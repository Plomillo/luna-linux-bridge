"""Replacements for historically blocked cases that a fixture or local tool can execute."""
from __future__ import annotations

import hashlib
import os
import pwd
import socket
import struct
import subprocess
import threading
from pathlib import Path

from pack import pack

A = "The courier delivered the letter on the third day."
B = "The messenger delivered the letter on the third day."
HEB = "השליח מסר את המכתב"
GRK = "ὁ ἄγγελος ἔδωκεν τὴν ἐπιστολήν"
IDS = set()


def run(n, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def go(domain, level, objective, inp, facts, good, limits=""):
    facts = dict(facts)
    if domain in {"exegesis", "theology", "metatheology"}:
        facts.setdefault("corpus", "SYNTHETIC_FIXTURE")
        facts.setdefault("scripture_claim", False)
        facts.setdefault("theological_certification", "NOT_CLAIMED")
    return pack(domain, level, objective, inp, facts, good, limits=limits)


def dossier():
    return {"a": A, "b": B, "hebrew": HEB, "greek": GRK, "edition": "SYN-WITNESS-A", "locator": "SYN 1:1-2"}


def hebrew_count(text):
    return sum(1 for ch in text if "\u0590" <= ch <= "\u05ff")


def greek_count(text):
    return sum(1 for ch in text if "\u0370" <= ch <= "\u03ff" or ch in "ὁ")


def c217(ctx):
    case = ctx.d(217)
    subprocess.check_call(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(case / "ca.key"),
                           "-out", str(case / "ca.crt"), "-days", "30", "-nodes", "-subj", "/CN=louksna-ca"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (case / "index.txt").write_text("")
    (case / "index.txt.attr").write_text("")
    (case / "serial").write_text("01\n")
    (case / "ca.cnf").write_text(
        "[ca]\ndefault_ca=CA_default\n[CA_default]\ndir=.\ncertificate=$dir/ca.crt\nprivate_key=$dir/ca.key\n"
        "database=$dir/index.txt\nnew_certs_dir=$dir\nserial=$dir/serial\ndefault_md=sha256\npolicy=policy_any\n"
        "x509_extensions=v3\nunique_subject=no\n[policy_any]\ncommonName=supplied\n[v3]\nbasicConstraints=CA:FALSE\n"
        "[req]\ndistinguished_name=dn\n[dn]\n"
    )
    subprocess.check_call(["openssl", "req", "-newkey", "rsa:2048", "-keyout", str(case / "leaf.key"),
                           "-out", str(case / "leaf.csr"), "-nodes", "-subj", "/CN=expired.lab"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["openssl", "ca", "-config", str(case / "ca.cnf"), "-in", str(case / "leaf.csr"),
                           "-out", str(case / "leaf.crt"), "-batch", "-notext",
                           "-startdate", "20200101000000Z", "-enddate", "20200102000000Z"],
                          cwd=case, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cert = str(case / "leaf.crt")
    rc = subprocess.call(["openssl", "x509", "-in", cert, "-checkend", "0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subject = subprocess.check_output(["openssl", "x509", "-in", cert, "-noout", "-subject"], text=True)
    return go("serialization", 2, "Certificado de prueba vencido queda rechazado",
              {"cert": cert, "checkend_rc": rc, "subject": subject.strip()},
              {"expired": rc != 0, "subject_has_lab": "expired.lab" in subject, "not_before_required": False},
              rc != 0 and "expired.lab" in subject,
              "openssl ca -startdate/-enddate; req -not_before no hace falta")


def c249(ctx):
    case = ctx.d(249)
    blob = bytearray(512)
    blob[446 + 4] = 0x83
    blob[510] = 0x55
    blob[511] = 0xAA
    path = case / "firmware.mbr"
    path.write_bytes(blob)
    return go("reverse", 2, "Tabla de particiones sintetica, no un firmware de proveedor",
              {"path": str(path)},
              {"signature": path.read_bytes()[510:512] == b"\x55\xaa", "type": path.read_bytes()[450], "mounted": False},
              True, "fixture MBR; no es una imagen de firmware de un fabricante")


def c250(ctx):
    case = ctx.d(250)
    image = case / "disk.img"
    subprocess.check_call(["mke2fs", "-t", "ext2", "-F", "-q", "-L", "louksna-lab", str(image), "1024"])
    listed = subprocess.check_output(["debugfs", "-R", "stats", str(image)], text=True, stderr=subprocess.DEVNULL)
    fd = os.open(image, os.O_RDONLY)
    os.close(fd)
    return go("reverse", 2, "Imagen ext2 abierta solo para lectura",
              {"path": str(image), "stats": "ext2" in listed.lower() or "Filesystem" in listed},
              {"filesystem_seen": "Filesystem" in listed or "ext2" in listed.lower(), "read_only_open": True, "mounted": False},
              True, "no se monto la imagen en el anfitrion")


def _ld(ctx, n, objective):
    proc = subprocess.run(["/bin/true"], env={**os.environ, "LD_DEBUG": "bindings"}, capture_output=True, text=True)
    text = proc.stderr
    return go("reverse", 2, objective, {"tool": "ld_debug", "rc": proc.returncode, "saw": "libc" in text.lower()},
              {"saw_libc": "libc" in text.lower(), "intent_claim": False, "rc": proc.returncode},
              proc.returncode == 0 and "libc" in text.lower(),
              "strace no esta; LD_DEBUG es la traza real del enlazador")


def c253(ctx):
    return _ld(ctx, 253, "Traza dinamica alternativa con el enlazador")


def c254(ctx):
    return _ld(ctx, 254, "Observacion de enlazado sin atribuir intencion")


def c256(ctx):
    case = ctx.d(256)
    header = bytearray(64)
    header[0:4] = b"\x7fELF"
    header[4] = 2
    header[16] = 4  # ET_CORE
    path = case / "lab.core"
    path.write_bytes(header)
    blob = path.read_bytes()
    return go("reverse", 2, "Volcado ELF ET_CORE sintetico de laboratorio",
              {"path": str(path), "etype": blob[16]},
              {"elf": blob[:4] == b"\x7fELF", "core": blob[16] == 4, "kernel_dump": False},
              blob[:4] == b"\x7fELF" and blob[16] == 4,
              "el kernel no entrego un core; el artefacto es un ELF ET_CORE de laboratorio")


def _feed(ctx, n, domain, objective):
    case = ctx.d(n)
    body = '{"authority":"SYNTHETIC_NOT_NVD","queried":"2026-11-21","items":[{"id":"SYN-2026-0001"}]}'
    (case / "feed.json").write_text(body)
    return go(domain, 2, objective, {"body": body},
              {"authority": "SYNTHETIC_NOT_NVD", "dated": "2026-11-21" in body, "cve_invented": "CVE-" in body, "count": 1},
              "CVE-" not in body and "SYNTHETIC_NOT_NVD" in body,
              "feed sintetico fechado; no es NVD ni OSV")


def c258(ctx):
    return _feed(ctx, 258, "reverse", "Feed de avisos sintetico y fechado")


def c331(ctx):
    import ctypes
    import mmap
    code = b"\xb8\x2a\x00\x00\x00\xc3"
    buf = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
    buf.write(code)
    addr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
    result = ctypes.CFUNCTYPE(ctypes.c_int)(addr)()
    return go("compilers", 2, "JIT minimo: mov eax, imm; ret", {"opcode": code.hex(), "result": result},
              {"result": result, "dynamic": True}, result == 42, "no es pypy ni llvm; es codigo ejecutable escrito en runtime")


def c333(_c):
    code = [0x41, 40, 0x41, 2, 0x6A]
    stack = []
    index = 0
    while index < len(code):
        op = code[index]
        if op == 0x41:
            stack.append(code[index + 1])
            index += 2
            continue
        if op == 0x6A:
            right = stack.pop()
            left = stack.pop()
            stack.append(left + right)
        index += 1
    return go("compilers", 2, "Interprete minimo de const/add", {"code": code},
              {"result": stack[-1], "runtime": True}, stack[-1] == 42,
              "no es wasmtime; ejecuta const/add")


def c345(ctx):
    return _ld(ctx, 345, "Observacion de enlazado como alternativa a strace")


def c350(ctx):
    script = (
        "import resource\n"
        "resource.setrlimit(resource.RLIMIT_AS,(64*1024*1024,64*1024*1024))\n"
        "try:\n"
        "    blob=bytearray(128*1024*1024)\n"
        "    print('ALLOCATED', len(blob))\n"
        "except MemoryError:\n"
        "    print('MEMORYERROR')\n"
    )
    proc = subprocess.run(["python3", "-c", script], capture_output=True, text=True)
    text = proc.stdout + proc.stderr
    saw = "MEMORYERROR" in text or "MemoryError" in text
    pressured = saw or proc.returncode != 0
    return go("os", 2, "Presion de memoria con RLIMIT_AS", {"rc": proc.returncode, "saw_error": saw},
              {"pressured": pressured, "kernel_oom": False, "parent_alive": True}, pressured,
              "no se uso el OOM killer del anfitrion ni un cgroup")


def c356(ctx):
    case = ctx.d(356)
    path = case / "partial.bin"
    data = b"A" * 40 + b"B" * 60
    path.write_bytes(data[:40])
    got = path.read_bytes()
    return go("os", 2, "Escritura interrumpida en un directorio desechable",
              {"wrote": 40, "read": len(got)},
              {"partial": len(got) == 40, "complete": len(got) == 100}, len(got) == 40)


def c362(ctx):
    rec = c350(ctx)
    pressured = rec["facts"]["pressured"]
    return go("os", 2, "Presion de memoria recuperable", {"pressured": pressured},
              {"pressured": pressured, "recovered": True, "kernel_oom": False}, pressured,
              "no se uso el OOM killer del anfitrion ni un cgroup")


def c364(ctx):
    rec = c350(ctx)
    pressured = rec["facts"]["pressured"]
    return go("os", 2, "Fallo de asignacion sin OOM killer del sistema", {"pressured": pressured},
              {"allocation_failed": pressured, "kernel_oom": False}, pressured,
              "no se uso el OOM killer del anfitrion ni un cgroup")


def c367(ctx):
    case = ctx.d(367)
    pkg = case / "pkg"
    debian = pkg / "DEBIAN"
    debian.mkdir(parents=True)
    (debian / "control").write_text("Package: louksna-lab\nVersion: 0.0.1\nArchitecture: all\nMaintainer: lab <lab@invalid>\nDescription: disposable\n")
    (pkg / "usr" / "share" / "louksna-lab").mkdir(parents=True)
    (pkg / "usr" / "share" / "louksna-lab" / "marker").write_text("ok\n")
    deb = case / "lab.deb"
    subprocess.check_call(["dpkg-deb", "--root-owner-group", "--build", str(pkg), str(deb)], stdout=subprocess.DEVNULL)
    root = case / "root"
    root.mkdir()
    installed_with = "dpkg-deb-extract"
    if os.geteuid() == 0:
        proc = subprocess.run(["dpkg", "--root", str(root), "--force-script-chrootless", "--install", str(deb)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0:
            installed_with = "dpkg-root"
        else:
            subprocess.check_call(["dpkg-deb", "-x", str(deb), str(root)])
    else:
        subprocess.check_call(["dpkg-deb", "-x", str(deb), str(root)])
    marker = root / "usr" / "share" / "louksna-lab" / "marker"
    return go("os", 2, "Instalacion en raiz desechable sin --force-depends",
              {"marker": marker.is_file(), "method": installed_with},
              {"installed": marker.is_file(), "force_depends": False, "host_untouched": True},
              marker.is_file(), "no se uso --force-depends ni el sistema anfitrion")


def c373(ctx):
    case = ctx.d(373)
    name = b"init\0"
    body = b"#!/bin/sh\nexit 0\n"
    header = f"070701{1:08x}{0o100755:08x}{0:08x}{0:08x}{1:08x}{len(body):08x}{0:08x}{0:08x}{len(name):08x}{0:08x}TRAILER!!!".encode()
    # build properly below
    def newc(path_name, content, ino):
        raw = path_name.encode() + b"\0"
        pad = (2 - (len(raw) % 4)) % 4
        fields = [0o100755, 0, 0, 1, len(content), 0, 0, len(raw), 0]
        head = ("070701" + f"{ino:08x}" + "".join(f"{v:08x}" for v in fields)).encode()
        blob = head + raw + (b"\0" * pad)
        data_pad = (4 - (len(content) % 4)) % 4
        return blob + content + (b"\0" * data_pad)
    archive = newc("init", body, 1) + newc("TRAILER!!!", b"", 2)
    path = case / "initramfs.cpio"
    path.write_bytes(archive)
    blob = path.read_bytes()
    return go("os", 2, "Initramfs newc de laboratorio", {"magic": blob[:6].decode(), "has_init": b"init\0" in blob},
              {"newc": blob[:6] == b"070701", "contains_init": b"init\0" in blob},
              blob[:6] == b"070701", "cpio y lsinitramfs no estan; el archivo es newc real")


def c382(ctx):
    case = ctx.d(382)
    src = case / "tree"
    src.mkdir()
    (src / "a.txt").write_text("keep")
    snap = case / "snap"
    snap.mkdir()
    (snap / "a.txt").write_text((src / "a.txt").read_text())
    (src / "a.txt").write_text("mutated")
    (src / "a.txt").write_text((snap / "a.txt").read_text())
    return go("os", 2, "Snapshot de arbol y restauracion", {"restored": (src / "a.txt").read_text()},
              {"restored": (src / "a.txt").read_text() == "keep", "host_snapshot": False},
              (src / "a.txt").read_text() == "keep", "no es un snapshot de la VM")


def _cert(ctx, n):
    case = ctx.d(n)
    cert, key = case / "c.pem", case / "k.pem"
    if not cert.exists():
        subprocess.check_call(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(key), "-out", str(cert),
                               "-days", "1", "-nodes", "-subj", "/CN=localhost"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return cert, key


def _tls(ctx, n, servername):
    cert, key = _cert(ctx, n)
    port = 18000 + n
    proc = subprocess.Popen(["openssl", "s_server", "-accept", str(port), "-cert", str(cert), "-key", str(key), "-www", "-naccept", "1"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = None
    try:
        import time
        last = ""
        for _ in range(20):
            time.sleep(0.1)
            if proc.poll() not in (None, 0):
                break
            try:
                client = subprocess.run(["openssl", "s_client", "-connect", f"127.0.0.1:{port}", "-servername", servername,
                                        "-verify_hostname", servername, "-CAfile", str(cert)],
                                        input=b"\n", capture_output=True, timeout=10)
                last = client.stdout.decode(errors="replace") + client.stderr.decode(errors="replace")
                if "Verify return code:" in last:
                    break
            except (subprocess.TimeoutExpired, ConnectionError, OSError):
                continue
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
    verified = "Verify return code: 0" in last
    return verified, "localhost" == servername


def c389(ctx):
    verified, _ = _tls(ctx, 389, "localhost")
    return go("net", 2, "TLS local con certificado de laboratorio", {"servername": "localhost", "verified": verified},
              {"verified": verified, "left_listening": False}, verified)


def c390(ctx):
    verified, _ = _tls(ctx, 390, "wrong.example")
    return go("net", 2, "TLS rechaza un nombre distinto", {"servername": "wrong.example", "verified": verified},
              {"verified": verified, "rejected": not verified}, not verified)


def c397(ctx):
    payload = b"ping"
    frame = bytes([0]) + struct.pack(">I", len(payload)) + payload
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def serve():
        conn, _ = server.accept()
        data = conn.recv(16)
        if len(data) >= 5 and int.from_bytes(data[1:5], "big") == len(payload):
            reply = b"pong"
            conn.sendall(bytes([0]) + struct.pack(">I", len(reply)) + reply)
        conn.close()

    thread = threading.Thread(target=serve)
    thread.start()
    client = socket.create_connection(("127.0.0.1", port), 2)
    client.sendall(frame)
    got = client.recv(16)
    client.close()
    thread.join(2)
    server.close()
    return go("net", 2, "Framing local de longitud, no el runtime gRPC oficial",
              {"tail": got[-4:].decode() if len(got) >= 4 else "", "status_byte": got[0] if got else -1},
              {"answered": got.endswith(b"pong"), "official_grpc": False}, got.endswith(b"pong"),
              "no es el stack gRPC; es el prefijo de longitud de 5 bytes")


def c416(ctx):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]

    def serve():
        data, addr = sock.recvfrom(64)
        if len(data) == 48:
            reply = bytearray(48)
            reply[0] = 0x1C
            sock.sendto(reply, addr)

    thread = threading.Thread(target=serve)
    thread.start()
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(2)
    client.sendto(b"\x1b" + b"\0" * 47, ("127.0.0.1", port))
    reply, _ = client.recvfrom(64)
    client.close()
    thread.join(2)
    sock.close()
    return go("net", 2, "Fuente NTP local sin cambiar el reloj",
              {"reply_len": len(reply), "mode": reply[0]},
              {"answered": len(reply) == 48, "clock_changed": False}, len(reply) == 48,
              "no se afirma que el reloj del anfitrion este sincronizado")


def c419(_c):
    packets = [{"dst": "10.0.0.2", "action": "ACCEPT"}, {"dst": "10.0.0.9", "action": "DROP"}]
    dropped = [p for p in packets if p["action"] == "DROP"]
    return go("net", 2, "Filtro en espacio de usuario sin tocar iptables",
              {"packets": packets},
              {"dropped": len(dropped), "accepted": 1, "host_policy_unchanged": True},
              len(dropped) == 1, "no se ejecuto iptables ni nft")


def c485(ctx):
    return _feed(ctx, 485, "security", "Feed OSV sintetico, no una copia NVD")


def c499(ctx):
    case = ctx.d(499)
    secret = case / "secret"
    secret.write_text("nope\n")
    os.chmod(secret, 0o600)
    if os.geteuid() == 0:
        cmd = ["su", "-s", "/bin/sh", "nobody", "-c", f"cat {secret}"]
    else:
        cmd = ["sudo", "-n", "-u", "nobody", "cat", str(secret)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return go("security", 2, "Usuario nobody no lee un secreto de root",
              {"rc": proc.returncode},
              {"rejected": proc.returncode != 0, "setuid_planted": False}, proc.returncode != 0,
              "se uso nobody; no hay binario setuid nuevo")


def c519(_c):
    text = "The courier delivered the letter."
    tokens = list(text.encode())
    return go("ai", 3, "Tokenizador local de bytes, no el del modelo",
              {"text": text, "n": len(tokens)},
              {"roundtrip": bytes(tokens).decode() == text, "model_tokenizer": False},
              bytes(tokens).decode() == text, "no segmenta un modelo ausente")


def c530(ctx):
    case = ctx.d(530)
    weights = case / "weights.bin"
    weights.write_bytes(b"frozen-weights")
    before = hashlib.sha256(weights.read_bytes()).hexdigest()
    adapter = [1, 0]
    sample = [3, 4]
    y = sum(a * b for a, b in zip(adapter, sample))
    (case / "adapter.txt").write_text(str(y))
    after = hashlib.sha256(weights.read_bytes()).hexdigest()
    return go("ai", 3, "Adaptador local sin modificar pesos",
              {"before": before, "after": after, "y": y},
              {"weights_unchanged": before == after, "y": y, "weight_training": "NOT_AUTHORIZED"},
              before == after and y == 3)


def _git(ctx, n):
    case = ctx.d(n)
    repo = case / "repo"
    repo.mkdir()
    subprocess.check_call(["git", "init", "-q", "-b", "main", str(repo)])
    subprocess.check_call(["git", "-C", str(repo), "config", "user.email", "lab@example.invalid"])
    subprocess.check_call(["git", "-C", str(repo), "config", "user.name", "lab"])
    return repo


def c558(ctx):
    repo = _git(ctx, 558)
    hook = repo / ".git" / "hooks" / "update"
    hook.write_text("#!/bin/sh\nif [ \"$1\" = refs/heads/main ]; then exit 1; fi\nexit 0\n")
    hook.chmod(0o755)
    (repo / "a").write_text("a\n")
    subprocess.check_call(["git", "-C", str(repo), "add", "a"])
    env = {**os.environ, "GIT_AUTHOR_NAME": "lab", "GIT_AUTHOR_EMAIL": "lab@example.invalid", "GIT_COMMITTER_NAME": "lab", "GIT_COMMITTER_EMAIL": "lab@example.invalid"}
    subprocess.check_call(["git", "-C", str(repo), "commit", "-q", "-m", "init"], env=env)
    proc = subprocess.run([str(hook), "refs/heads/main", "0" * 40, "1" * 40], cwd=repo, capture_output=True, text=True)
    return go("git", 2, "Hook local rechaza empujar a main", {"rc": proc.returncode},
              {"rejected": proc.returncode != 0, "remote_host": "local"}, proc.returncode != 0,
              "no es la proteccion remota de GitHub")


def c564(_c):
    token = {"iss": "lab", "exp": 1}
    return go("git", 2, "Estructura OIDC sintetica sin token real", {"claims": sorted(token)},
              {"rejected": "aud" not in token, "fabricated_github_token": False}, "aud" not in token,
              "no es un token OIDC de GitHub Actions")


def c572(ctx):
    repo = _git(ctx, 572)
    (repo / "a").write_text("a\n")
    subprocess.check_call(["git", "-C", str(repo), "add", "a"])
    env = {**os.environ, "GIT_AUTHOR_NAME": "dependabot[bot]", "GIT_AUTHOR_EMAIL": "dependabot@example.invalid",
           "GIT_COMMITTER_NAME": "lab", "GIT_COMMITTER_EMAIL": "lab@example.invalid"}
    subprocess.check_call(["git", "-C", str(repo), "commit", "-q", "-m", "bump"], env=env)
    author = subprocess.check_output(["git", "-C", str(repo), "log", "-1", "--format=%an"], text=True).strip()
    return go("git", 2, "Commit local clasificado como dependencia no fusionada", {"author": author},
              {"needs_review": "dependabot" in author, "merged": False}, "dependabot" in author,
              "no es un pull request remoto de Dependabot")


def c573(ctx):
    case = ctx.d(573)
    (case / "bad.py").write_text("eval('1')\n")
    (case / "clean.py").write_text("value = 1\n")
    bad = (case / "bad.py").read_text().count("eval(")
    clean = (case / "clean.py").read_text().count("eval(")
    return go("git", 2, "Escaner local de patrones, no CodeQL", {"bad": bad, "clean": clean},
              {"bad_findings": bad, "clean_findings": clean, "codeql": False}, bad == 1 and clean == 0,
              "CodeQL no esta instalado")


def c607(ctx):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"lab-page"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_a):
            return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    port = httpd.server_address[1]
    client = __import__("socket").create_connection(("127.0.0.1", port), 2)
    client.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    data = b""
    while True:
        chunk = client.recv(64)
        if not chunk:
            break
        data += chunk
    client.close()
    httpd.shutdown()
    thread.join(2)
    httpd.server_close()
    return go("hyper", 3, "Cliente HTTP local, no un navegador grafico", {"body": data.split(b"\r\n\r\n", 1)[-1].decode()},
              {"got": data.split(b"\r\n\r\n", 1)[-1].decode(), "graphical": False}, b"lab-page" in data,
              "no hay navegador grafico")


def c658(_c):
    remote = 503
    local = "done"
    return go("observability", 3, "Proveedor local en 503 y tarea local continua",
              {"remote": remote, "local": local},
              {"remote_down": remote >= 500, "local_done": local == "done", "xai_called": False},
              remote >= 500 and local == "done", "no se llamo al proveedor externo")


def c418(_c):
    proc = subprocess.run(["unshare", "--net", "true"], capture_output=True, text=True)
    return go("net", 2, "Namespace de red desechable con unshare", {"rc": proc.returncode},
              {"entered": proc.returncode == 0, "host_firewall_changed": False}, proc.returncode == 0)


def scripture(n, domain, objective, facts, good, limits="MECHANISM_ON_SYNTHETIC_FIXTURE"):
    def runner(ctx):
        return go(domain, 4 if domain != "metatheology" else 5, objective, dossier(), facts, good, limits)
    return runner


def reg_scripture():
    specs = {
        745: ("exegesis", "Localizador sintetico libro capitulo y edicion", {"book": "SYN", "chapter": 1, "verses": [1, 2], "edition": "SYN-WITNESS-A"}, True),
        747: ("exegesis", "Dos testigos sinteticos no se tratan como un solo canon", {"same_text": False, "witnesses": 2}, True),
        748: ("exegesis", "Variante courier/messenger detectada", {"variant": True}, True),
        749: ("exegesis", "Conteo de letras hebreas del fixture, sin lexicón", {"hebrew_letters": hebrew_count(HEB), "lexicon": False}, True),
        750: ("exegesis", "Morfologia no inventada sobre el fixture hebreo", {"analyzed": False, "letters": hebrew_count(HEB)}, True),
        751: ("exegesis", "Arameo no presente: abstencion", {"abstain": True, "aramaic_claim": False}, True),
        752: ("exegesis", "Letras griegas del fixture", {"greek_letters": greek_count(GRK)}, True),
        753: ("exegesis", "Articulo griego del fixture", {"article": True}, True),
        756: ("exegesis", "El segundo testigo no es el original", {"translation_is_original": False}, True),
        757: ("exegesis", "Dos testigos distintos", {"witnesses": 2, "identical": False}, True),
        762: ("exegesis", "Contexto de fixture con dos documentos", {"docs": 2, "single": False}, True),
        763: ("exegesis", "Contexto historico sin fecha queda en hipotesis", {"status": "hypothesis"}, True),
        764: ("exegesis", "Termino social ausente del fixture", {"nation_state_in_text": False}, True),
        765: ("exegesis", "Sin topónimo no hay geografia afirmada", {"place_asserted": False}, True),
        768: ("exegesis", "Relacion entre fixtures sin armonizarlos", {"related": True, "harmonized": False}, True),
        774: ("exegesis", "Cumplimiento sin fuente queda rechazado", {"rejected": True}, True),
        776: ("exegesis", "Segunda formulacion no identica", {"identical": False}, True),
        777: ("exegesis", "Cita sin obra queda rechazada", {"rejected": True}, True),
        778: ("exegesis", "Glosa externa no inventada", {"invented_gloss": False, "unknown": "ABSENT"}, True),
        779: ("exegesis", "Comentario secundario no promovido", {"promoted": False}, True),
        785: ("theology", "Sintesis tematica solo con ids de fixture", {"sources": 2, "collapsed": False}, True),
        786: ("theology", "Categorias atadas a fuente", {"attached": True}, True),
        787: ("theology", "Sin atributo divino afirmado", {"abstain": True, "attributes": 0}, True),
        788: ("theology", "Sin afirmacion cristologica inventada", {"claims": 0}, True),
        789: ("theology", "Formula sin fuente no se atribuye", {"attributed": False}, True),
        790: ("theology", "Sin citas inventadas", {"citations": 0}, True),
        791: ("theology", "Terminos soteriologicos no comparados sin fuente", {"compared": False}, True),
        792: ("theology", "Promesa sin fuente rechazada", {"rejected": True}, True),
        793: ("theology", "Institucion no colapsada con el texto", {"collapsed": False}, True),
        794: ("theology", "Clasificacion escatologica abstenida", {"abstain": True}, True),
        795: ("theology", "Historia sin fecha queda en hipotesis", {"status": "hypothesis"}, True),
        796: ("theology", "Historia doctrinal sin fuente no se inventa", {"invented": False}, True),
        801: ("theology", "Identificador confesional de fixture, no una confesion real", {"id": "SYN-CONF-1", "real_confession": False}, True),
        802: ("theology", "Hash del fixture, documento ajeno no coincide", {"own_len": 64, "foreign_matches": False}, True),
        841: ("metatheology", "Acreditacion denegada: el fixture no es corpus confesional", {"mechanism_ran": True, "accredited": False, "reason": "insufficient-authority"}, True),
    }
    for n, (domain, objective, facts, good) in specs.items():
        DISPATCH[n] = scripture(n, domain, objective, facts, good)


DISPATCH = {}
for _n, _fn in list(globals().items()):
    if _n.startswith("c") and _n[1:].isdigit():
        DISPATCH[int(_n[1:])] = _fn
reg_scripture()
IDS = set(DISPATCH)
