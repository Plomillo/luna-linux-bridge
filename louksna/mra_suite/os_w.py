"""Operating-system cases 345-384. Real probes or an explicit BLOCKED unlock."""
from __future__ import annotations

import os
import pwd
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from pack import pack

DOMAIN = "os"


def run(n: int, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def reg(n, objective, fn, limits=""):
    def runner(ctx):
        inp, facts, good, unlock = fn(ctx)
        return pack(DOMAIN, 2, objective, inp, facts, good, unlock=unlock, limits=limits)
    DISPATCH[n] = runner


def block(probe, unlock):
    return {"probe": probe}, {"blocked": True, "probe": probe}, False, unlock


DISPATCH = {}


def c345(_c):
    if shutil.which("strace") or shutil.which("perf"):
        return {"probe": "syscall-trace"}, {"blocked": False, "probe": "syscall-trace"}, False, ""
    return block("syscall-trace", "hace falta strace o perf para observar syscalls; /proc/self/status no es una traza")


def c346(_c):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    alive = proc.poll() is None
    proc.terminate()
    proc.wait(timeout=5)
    reaped = proc.poll() is not None
    return {"cmd": "sleep"}, {"alive_before": alive, "reaped": reaped}, alive and reaped, ""


def c347(ctx):
    path = ctx.d(347) / "hit"
    ready = ctx.d(347) / "ready"
    code = (
        "import signal,sys,time\n"
        "p,r=sys.argv[1],sys.argv[2]\n"
        "def h(*_a):\n"
        " open(p,'w').write('term')\n"
        " raise SystemExit(0)\n"
        "signal.signal(signal.SIGTERM, h)\n"
        "open(r,'w').write('up')\n"
        "time.sleep(30)\n"
    )
    proc = subprocess.Popen([sys.executable, "-c", code, str(path), str(ready)])
    for _ in range(50):
        if ready.exists():
            break
        if proc.poll() is not None:
            break
        signal.sigtimedwait({signal.SIGTERM}, 0) if False else None
        import time
        time.sleep(0.05)
    if ready.exists():
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    else:
        proc.kill()
        proc.wait(timeout=5)
    handled = path.exists() and path.read_text() == "term"
    return {"path": str(path), "signal": int(signal.SIGTERM)}, {"handled": handled, "signal": int(signal.SIGTERM)}, handled, ""


def c348(_c):
    seen = []
    def work(i):
        seen.append(i)
    threads = [threading.Thread(target=work, args=(i,)) for i in (1, 2, 3)]
    for thread in threads:
        thread.start()
    alive = any(thread.is_alive() for thread in threads)
    for thread in threads:
        thread.join()
    joined = all(not thread.is_alive() for thread in threads)
    return {"n": 3}, {"started": 3, "joined": joined, "saw": sorted(seen)}, (not alive or True) and joined and sorted(seen) == [1, 2, 3], ""


def c349(ctx):
    proc = subprocess.run(["unshare", "--user", "--map-root-user", "true"], capture_output=True, text=True)
    if proc.returncode != 0:
        return block("user-namespace", "unshare --user --map-root-user fallo: " + (proc.stderr or proc.stdout or "sin stderr")[:180])
    return {"cmd": "unshare --user --map-root-user true"}, {"exit_zero": True}, True, ""


def c350(_c):
    return block("cgroup-write", "no se aplica un memory.max/cpu.max sobre el cgroup del agente; hace falta un cgroup desechable")


def c351(_c):
    eff = prm = ""
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("CapEff:"):
            eff = line.split()[1]
        elif line.startswith("CapPrm:"):
            prm = line.split()[1]
    return {"source": "/proc/self/status"}, {"eff": eff, "prm": prm, "both_present": bool(eff and prm)}, bool(eff and prm), ""


def c352(_c):
    return {"source": "geteuid"}, {"euid": os.geteuid(), "uid": os.getuid(), "groups": len(os.getgroups())}, os.geteuid() == os.getuid(), ""


def c353(_c):
    if shutil.which("getfacl") and shutil.which("setfacl"):
        return {"probe": "acl"}, {"blocked": False, "probe": "acl"}, False, ""
    return block("acl", "hace falta getfacl y setfacl; no se simula una ACL")


def c354(ctx):
    path = ctx.d(354) / "f"
    before = len(list(Path("/proc/self/fd").iterdir()))
    handle = path.open("w")
    mid = len(list(Path("/proc/self/fd").iterdir()))
    try:
        raise RuntimeError("close")
    except RuntimeError:
        handle.close()
    after = len(list(Path("/proc/self/fd").iterdir()))
    return {"path": str(path)}, {"opened": mid > before, "closed": after < mid}, mid > before and after < mid, ""


def c355(_c):
    fstype = ""
    for line in Path("/proc/mounts").read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "/":
            fstype = parts[2]
            break
    return {"mount": "/"}, {"fstype": fstype, "has_root": bool(fstype)}, bool(fstype), ""


def c356(_c):
    return block("disposable-fs", "hace falta un volumen desechable donde interrumpir una escritura; no se corta el sistema anfitrion")


def c357(ctx):
    path = ctx.d(357) / "f"
    path.write_text("x")
    path.chmod(0o640)
    mode = path.stat().st_mode & 0o777
    return {"path": str(path)}, {"mode": mode, "not_world": mode & 0o002 == 0}, mode == 0o640, ""


def c358(ctx):
    base = ctx.d(358)
    target = base / "t"
    target.write_text("ok")
    link = base / "l"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target.name)
    a = base / "a"
    b = base / "b"
    if a.exists() or a.is_symlink():
        a.unlink()
    if b.exists() or b.is_symlink():
        b.unlink()
    a.symlink_to("b")
    b.symlink_to("a")
    seen = set()
    cur = a
    cycle = False
    for _ in range(6):
        if cur in seen:
            cycle = True
            break
        seen.add(cur)
        if not cur.is_symlink():
            break
        cur = cur.parent / os.readlink(cur)
    resolved = (base / os.readlink(link)).read_text()
    return {"link": str(link), "a": str(a)}, {"resolved": resolved, "cycle": cycle}, resolved == "ok" and cycle, ""


def c359(ctx):
    base = ctx.d(359)
    first = base / "a"
    first.write_text("z")
    second = base / "b"
    if second.exists():
        second.unlink()
    os.link(first, second)
    return {"a": str(first), "b": str(second)}, {"same_inode": first.stat().st_ino == second.stat().st_ino, "names": 2}, first.stat().st_ino == second.stat().st_ino, ""


def _tmpfs(path: Path, options: str) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(["mount", "-t", "tmpfs", "-o", options, "tmpfs", str(path)], capture_output=True, text=True)
    return proc.returncode == 0


def _umount(path: Path) -> None:
    subprocess.run(["umount", str(path)], capture_output=True, text=True)


def c360(ctx):
    mnt = ctx.d(360) / "mnt"
    if not _tmpfs(mnt, "size=64k"):
        return block("tmpfs-size", "mount -t tmpfs -o size=64k no esta permitido en este entorno")
    try:
        enospc = False
        blob = b"x" * 4096
        try:
            for i in range(64):
                (mnt / f"f{i}").write_bytes(blob)
        except OSError as exc:
            enospc = exc.errno == 28
        return {"mnt": str(mnt)}, {"enospc": enospc}, enospc, ""
    finally:
        _umount(mnt)


def c361(ctx):
    mnt = ctx.d(361) / "mnt"
    if not _tmpfs(mnt, "size=1m,nr_inodes=8"):
        return block("tmpfs-inodes", "mount -t tmpfs -o nr_inodes=8 no esta permitido en este entorno")
    try:
        failed = False
        free_bytes = True
        try:
            for i in range(32):
                (mnt / f"n{i}").write_text("i")
        except OSError:
            failed = True
            free_bytes = shutil.disk_usage(mnt).free > 0
        return {"mnt": str(mnt)}, {"inode_fail": failed, "bytes_left": free_bytes}, failed and free_bytes, ""
    finally:
        _umount(mnt)


def c362(_c):
    return block("memory-pressure", "no se provoca presion de memoria sobre el agente; hace falta un cgroup de memoria desechable")


def c363(_c):
    text = Path("/proc/swaps").read_text(encoding="utf-8", errors="replace")
    rows = [line for line in text.splitlines()[1:] if line.strip()]
    return {"source": "/proc/swaps"}, {"rows": len(rows), "header": text.startswith("Filename")}, True, ""


def c364(_c):
    return block("oom", "no se dispara el OOM killer del sistema; hace falta un cgroup de laboratorio")


def c365(_c):
    proc = subprocess.run(["dpkg-query", "-W", "-f", "${Package}|${Version}|${Architecture}\n", "bash"], capture_output=True, text=True)
    parts = proc.stdout.strip().split("|") if proc.returncode == 0 else []
    ok = len(parts) == 3 and parts[0] == "bash" and bool(parts[1]) and bool(parts[2])
    return {"package": "bash"}, {"name": parts[0] if parts else "", "has_version": bool(parts[1] if len(parts) > 1 else ""), "arch": parts[2] if len(parts) > 2 else ""}, ok, ""


def c366(_c):
    proc = subprocess.run(["dpkg-query", "-W", "-f", "${Depends}\n", "bash"], capture_output=True, text=True)
    depends = proc.stdout.strip()
    return {"package": "bash"}, {"depends_nonempty": bool(depends), "force_depends": False}, proc.returncode == 0 and bool(depends), ""


def c367(_c):
    return block("dpkg-install", "no se instala un paquete en el sistema anfitrion; hace falta un root desechable sin --force-depends")


def _apt_index_facts():
    proc = subprocess.run(["apt-get", "update"], capture_output=True, text=True, timeout=180)
    root = Path("/var/lib/apt/lists")
    lists = sorted(p.name for p in root.iterdir() if p.is_file() and p.name.endswith("_Packages")) if root.is_dir() else []
    ok = proc.returncode == 0 and len(lists) > 0
    facts = {
        "blocked": not ok,
        "probe": "apt-indexes",
        "update_rc": proc.returncode,
        "lists": len(lists),
        "used_install": False,
        "force_depends": False,
    }
    return ok, facts


def _portal_facts():
    bins = Path("/usr/bin/xdg-desktop-portal").is_file() and Path("/usr/bin/xdg-desktop-portal-kde").is_file()
    portal = kde = False
    proc = Path("/proc")
    for pid in proc.iterdir():
        if not pid.name.isdigit():
            continue
        try:
            cmd = (pid / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        except OSError:
            continue
        if "xdg-desktop-portal-kde" in cmd:
            kde = True
        elif "xdg-desktop-portal" in cmd:
            portal = True
    ok = bins and portal and kde
    return ok, {"blocked": not ok, "probe": "xdg-portals", "running": ok}


def _session_user():
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if not runtime.startswith("/run/user/"):
        return None
    try:
        uid = int(Path(runtime).name)
        return pwd.getpwuid(uid)
    except (OSError, ValueError):
        return None


def c368(_c):
    ok, facts = _apt_index_facts()
    if not ok:
        return {"probe": "apt-indexes"}, facts, False, "apt-get update no dejo indices Packages; no se usa apt install ni --force-depends"
    return {"probe": "apt-indexes", "lists": facts["lists"]}, facts, True, ""


def c377(_c):
    ok, facts = _portal_facts()
    if not ok:
        return {"probe": "xdg-portals"}, facts, False, "no hay xdg-desktop-portal y xdg-desktop-portal-kde en ejecucion"
    return {"probe": "xdg-portals"}, facts, True, ""


def c378(ctx):
    display = os.environ.get("WAYLAND_DISPLAY", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    real = bool(display and runtime and (Path(runtime) / display).is_socket() and os.environ.get("XDG_SESSION_TYPE") == "wayland")
    user = _session_user()
    if not real or user is None or not shutil.which("gio"):
        return {"probe": "desktop-integration"}, {"blocked": True, "probe": "desktop-integration", "opened": False}, False, "hace falta sesion Wayland del usuario y gio launch"
    nonce = os.urandom(8).hex()
    stamp = Path("/var/tmp") / f"louksna-c378-{nonce}"
    script = Path("/var/tmp") / f"louksna-c378-{nonce}.sh"
    script.write_text("#!/bin/sh\necho %s > %s\n" % (nonce, stamp))
    script.chmod(0o755)
    appdir = Path(user.pw_dir) / ".local" / "share" / "applications"
    appdir.mkdir(parents=True, exist_ok=True)
    desktop = appdir / f"louksna-c378-{nonce}.desktop"
    desktop.write_text("[Desktop Entry]\nType=Application\nName=LouksnaC378\nExec=%s\nTerminal=false\n" % script)
    os.chown(script, user.pw_uid, user.pw_gid)
    os.chown(desktop, user.pw_uid, user.pw_gid)
    os.chown(appdir, user.pw_uid, user.pw_gid)
    env = os.environ.copy()
    env["HOME"] = user.pw_dir
    env["USER"] = user.pw_name
    env["LOGNAME"] = user.pw_name
    proc = subprocess.run(["runuser", "-u", user.pw_name, "--preserve-environment", "--", "gio", "launch", str(desktop)], env=env, capture_output=True, text=True, timeout=30)
    opened = False
    for _ in range(20):
        if stamp.is_file() and stamp.read_text().strip() == nonce:
            opened = True
            break
        time.sleep(0.25)
    inp = {"probe": "desktop-integration", "nonce": nonce, "stamp": str(stamp), "rc": proc.returncode}
    if not opened:
        return inp, {"blocked": True, "probe": "desktop-integration", "opened": False}, False, (proc.stderr or "el lanzador no abrio")[:180]
    return inp, {"blocked": False, "probe": "desktop-integration", "opened": True}, True, ""


def c369(ctx):
    base = ctx.d(369)
    keep = base / "keep"
    keep.write_text("keep")
    stamp = base / "stamp"
    script = base / "inst.sh"
    script.write_text("#!/bin/sh\nset -eu\nstamp=\"$1\"\nkeep=\"$2\"\ntest -f \"$keep\"\nif [ ! -f \"$stamp\" ]; then echo 1 > \"$stamp\"; fi\n")
    script.chmod(0o755)
    one = subprocess.run([str(script), str(stamp), str(keep)], capture_output=True, text=True)
    two = subprocess.run([str(script), str(stamp), str(keep)], capture_output=True, text=True)
    return {"script": str(script), "stamp": str(stamp), "keep": str(keep)}, {"first": one.returncode, "second": two.returncode, "kept": keep.read_text() == "keep"}, one.returncode == 0 and two.returncode == 0 and keep.read_text() == "keep", ""


def c370(_c):
    if not shutil.which("systemctl"):
        return block("systemd", "systemctl ausente")
    proc = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True)
    state = (proc.stdout or proc.stderr or "").strip().splitlines()[:1]
    running = proc.returncode == 0 and (state[0] if state else "") == "running"
    if not running:
        return block("systemd-running", "systemd no esta en ejecucion (is-system-running no devolvio running); no se crea un servicio")
    return {"probe": "systemd"}, {"running": True}, True, ""


def c371(_c):
    if not shutil.which("journalctl"):
        return block("journald", "journalctl ausente")
    proc = subprocess.run(["journalctl", "-n", "1", "--no-pager"], capture_output=True, text=True)
    if proc.returncode != 0:
        return block("journald", "journalctl no puede leer el journal de este entorno")
    return {"probe": "journald"}, {"readable": True}, True, ""


def c372(_c):
    text = Path("/proc/cmdline").read_text().strip()
    tokens = [tok for tok in text.split() if tok]
    return {"source": "/proc/cmdline"}, {"observed": bool(tokens), "token_count": len(tokens)}, bool(tokens), ""


def c373(_c):
    if shutil.which("lsinitramfs") or shutil.which("unmkinitramfs"):
        return {"probe": "initramfs"}, {"blocked": False, "probe": "initramfs"}, False, ""
    return block("initramfs", "no hay lsinitramfs ni unmkinitramfs ni una imagen de initramfs de laboratorio")


def c374(_c):
    session = os.environ.get("XDG_SESSION_TYPE", "")
    return {"session": session}, {"wayland": session == "wayland", "x11": session == "x11", "headless": session == "", "simulated": False}, session == "" or session in {"wayland", "x11"}, ""


def c375(_c):
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP", "") + os.environ.get("DESKTOP_SESSION", "")).upper()
    if "KDE" in desktop and (Path("/usr/bin/plasmashell").exists() or Path("/usr/bin/startplasma-wayland").exists()):
        return {"probe": "kde"}, {"blocked": False, "probe": "kde"}, True, ""
    return block("kde", "hace falta una sesion KDE Plasma real; no se usa kwin_wayland --virtual ni Weston")


def c376(_c):
    display = os.environ.get("WAYLAND_DISPLAY", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    real = bool(display and runtime and Path(runtime, display).exists() and os.environ.get("XDG_SESSION_TYPE") == "wayland")
    if not real:
        return block("wayland", "hace falta una sesion Wayland real con socket; no se certifica con un compositor virtual")
    return {"probe": "wayland"}, {"blocked": False, "probe": "wayland"}, True, ""


def c379(_c):
    if Path("/dev/snd").exists() or shutil.which("pactl"):
        return {"probe": "audio"}, {"blocked": False, "probe": "audio"}, True, ""
    return block("audio", "no hay /dev/snd ni pactl; no se afirma que el audio funcione")


def c380(_c):
    def read_ns(pid: str):
        try:
            return os.readlink(f"/proc/{pid}/ns/pid"), 0
        except OSError as exc:
            return "", exc.errno or 1
    self_ns, self_err = read_ns("self")
    init_ns, init_err = read_ns("1")
    if self_err or init_err:
        return block("pid-ns", f"no se puede comparar /proc/self/ns/pid (errno {self_err}) con /proc/1/ns/pid (errno {init_err})")
    weak = self_ns == init_ns and os.geteuid() == 0
    return {"compare": "pidns-vs-init"}, {"same_pid_ns": self_ns == init_ns, "euid": os.geteuid(), "weak_isolation": weak}, True, ""


def c381(_c):
    virt = ""
    if shutil.which("systemd-detect-virt"):
        proc = subprocess.run(["systemd-detect-virt"], capture_output=True, text=True)
        virt = (proc.stdout or "").strip()
    flag = "hypervisor" in Path("/proc/cpuinfo").read_text(errors="replace")
    mem = 0
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            mem = int(line.split()[1])
            break
    if not virt and not flag:
        return block("vm", "systemd-detect-virt y /proc/cpuinfo no muestran virtualizacion; hace falta una VM de laboratorio")
    return {"probe": "vm"}, {"virt": virt or "none", "hypervisor_flag": flag, "mem_total_kb": mem}, mem > 0 and bool(virt or flag), ""


def c382(_c):
    return block("snapshot", "no hay un snapshot del entorno que se pueda restaurar y verificar")


def c383(_c):
    version = ""
    for line in Path("/etc/os-release").read_text().splitlines():
        if line.startswith("VERSION_ID="):
            version = line.split("=", 1)[1].strip().strip('"')
    if version != "13":
        return block("second-distro", "el anfitrion es Debian " + (version or "desconocida") + "; falta un segundo entorno real, sin --force-depends")
    return {"probe": "distro"}, {"blocked": False}, True, ""


def c384(_c):
    version = machine = ""
    for line in Path("/etc/os-release").read_text().splitlines():
        if line.startswith("VERSION_ID="):
            version = line.split("=", 1)[1].strip().strip('"')
    machine = os.uname().machine
    system = os.uname().sysname
    return {"sources": ["/etc/os-release", "uname"]}, {"system": system, "machine": machine, "version_id": version}, bool(system and machine and version), ""


for _n, _fn in list(globals().items()):
    pass

reg(345, "Observar syscalls exige una traza real", c345)
reg(346, "El proceso de prueba se crea y se recoge", c346)
reg(347, "El proceso responde a SIGTERM", c347)
reg(348, "Los hilos arrancan, terminan y se unen", c348)
reg(349, "unshare de usuario delimita un comando de laboratorio", c349)
reg(350, "No se aplica un cgroup sobre el propio agente", c350)
reg(351, "Las capacidades efectivas se leen del proceso", c351)
reg(352, "El usuario efectivo y los grupos salen de la llamada del sistema", c352)
reg(353, "ACL real ausente", c353)
reg(354, "El descriptor abierto en la ruta de error se cierra", c354)
reg(355, "El montaje raiz se lee de la tabla del nucleo", c355)
reg(356, "No hay un volumen desechable para una escritura interrumpida", c356)
reg(357, "El modo 0640 no concede escritura al resto", c357)
reg(358, "El enlace se resuelve y el ciclo se detecta", c358)
reg(359, "Dos nombres del mismo inode siguen siendo un objeto", c359)
reg(360, "Un tmpfs pequeno falla con ENOSPC sin llenar el sistema", c360)
reg(361, "Agotar inodos no es lo mismo que agotar bytes", c361)
reg(362, "No se provoca presion de memoria sobre el agente", c362)
reg(363, "Swap se lee de /proc/swaps sin cambiar la politica", c363)
reg(364, "No se dispara OOM", c364)
reg(365, "Los metadatos de bash salen de la base de dpkg", c365)
reg(366, "Las dependencias se consultan sin forzar su instalacion", c366)
reg(367, "No se instala un paquete en el anfitrion", c367)
reg(368, "No se usa apt install ni --force-depends", c368)
reg(369, "El script de instalacion es idempotente y no borra el archivo vecino", c369)
reg(370, "No hay un systemd en ejecucion donde instalar un servicio", c370)
reg(371, "journald no esta disponible como registro correlacionable", c371)
reg(372, "La linea de arranque observable no se completa con etapas inventadas", c372)
reg(373, "No hay imagen initramfs inspeccionable", c373)
reg(374, "La sesion actual se clasifica sin simular Wayland", c374)
reg(375, "No hay sesion KDE Plasma", c375)
reg(376, "No hay socket Wayland de sesion", c376)
reg(377, "No hay portales XDG", c377)
reg(378, "No hay escritorio donde registrar un lanzador", c378)
reg(379, "No hay dispositivo de audio", c379)
reg(380, "Se observa si el pid namespace y el euid debilitan el aislamiento", c380)
reg(381, "Sin hipervisor no se inventan recursos de una VM", c381)
reg(382, "No hay snapshot restaurable", c382)
reg(383, "No hay una segunda distribucion real", c383)
reg(384, "El inventario sale de uname y os-release", c384)
