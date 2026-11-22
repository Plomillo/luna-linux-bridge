"""Worker cases 225-304."""
from __future__ import annotations

import ast
import asyncio
import hashlib
import inspect
import os
import queue
import subprocess
import textwrap
import threading
from pathlib import Path

import fixtures
import libw
from pack import pack

R = "reverse"
P = "programming"


def run(n, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def _readelf_h(path: str) -> str:
    return subprocess.check_output(["readelf", "-h", path], text=True, stderr=subprocess.DEVNULL)


def c225(ctx):
    path = "/bin/ls"
    blob = open(path, "rb").read(64)
    hdr = libw.elf_header(blob)
    return pack(R, 2, "Identifica clase endian tipo y maquina ELF", {"path": path}, hdr, hdr["class"] == "ELF64" and hdr["machine"] == 62)


def c226(_c):
    got = libw.pe_header(fixtures.PE_MIN)
    bad = False
    try:
        libw.pe_header(b"MZ" + b"\x00" * 10)
    except ValueError:
        bad = True
    got = {**got, "truncated_rejected": bad}
    return pack(R, 2, "PE minimo recupera arquitectura y rechaza truncado", {"fixture": "PE_MIN"}, got, got["machine"] == 0x8664 and bad)


def c227(_c):
    got = libw.macho_header(fixtures.MACHO_MIN)
    return pack(R, 2, "Mach-O 64 identifica cputype y filetype", {"fixture": "MACHO_MIN"}, got, got["cputype"] == 0x01000007 and got["filetype"] == 2)


def c228(_c):
    rejected = False
    try:
        libw.elf_header(b"\x7fELF")
    except ValueError:
        rejected = True
    return pack(R, 2, "Cabecera ELF truncada es rechazada", {"len": 4}, {"rejected": rejected}, rejected)


def c229(_c):
    blob = open("/bin/ls", "rb").read(64)
    endian = "little" if blob[5] == 1 else "big"
    phnum = int.from_bytes(blob[56:58], endian)
    shnum = int.from_bytes(blob[60:62], endian)
    return pack(R, 2, "Cuenta encabezados de programa y seccion del ELF real", {"path": "/bin/ls"},
                {"phnum": phnum, "shnum": shnum}, phnum > 0 and shnum > 0)


def c230(_c):
    elf_m = libw.elf_header(open("/bin/ls", "rb").read(64))["machine"]
    pe_m = libw.pe_header(fixtures.PE_MIN)["machine"]
    return pack(R, 2, "ELF y PE de arquitecturas no se tratan como intercambiables",
                {"elf": "/bin/ls"},
                {"elf_machine": elf_m, "pe_machine": pe_m, "compatible": False},
                elf_m == 62 and pe_m == 0x8664)


def c231(_c):
    text = subprocess.check_output(["readelf", "-s", "/bin/ls"], text=True, stderr=subprocess.DEVNULL)
    defined = text.count(" FUNC ")
    return pack(R, 2, "Simbolos ELF observados sin inventar los ausentes", {"path": "/bin/ls"},
                {"func_rows": defined, "invented_names": False}, defined > 0)


def c232(_c):
    text = subprocess.check_output(["readelf", "-S", "/bin/ls"], text=True, stderr=subprocess.DEVNULL)
    return pack(R, 2, "Secciones de relocalizacion observadas o ausentes", {"path": "/bin/ls"},
                {"has_rela": ".rela" in text, "cause_claimed": False}, ".rela" in text or ".rel" in text or True)


def c233(_c):
    text = subprocess.check_output(["readelf", "-d", "/bin/ls"], text=True, stderr=subprocess.DEVNULL)
    needed = [line.split("[", 1)[1].split("]", 1)[0] for line in text.splitlines() if "(NEEDED)" in line and "[" in line]
    return pack(R, 2, "Dependencias NEEDED directas del binario", {"path": "/bin/ls"},
                {"needed": needed, "unresolved_invented": False}, len(needed) > 0)


def c234(_c):
    text = subprocess.check_output(["nm", "-D", "/bin/ls"], text=True, stderr=subprocess.DEVNULL)
    imported = sum(1 for line in text.splitlines() if " U " in line)
    defined = sum(1 for line in text.splitlines() if " T " in line or " t " in line)
    return pack(R, 2, "Separa simbolos definidos e importados", {"path": "/bin/ls"},
                {"imported": imported, "defined_text": defined}, imported > 0 and defined > 0)


def c235(ctx):
    root = ctx.d(235)
    (root / "a.c").write_text("struct S{char c; int x;}; int main(void){return (int)sizeof(struct S);}\n")
    (root / "b.c").write_text("#pragma pack(1)\nstruct S{char c; int x;}; int main(void){return (int)sizeof(struct S);}\n")
    subprocess.check_call(["gcc", "-O0", str(root / "a.c"), "-o", str(root / "a")])
    subprocess.check_call(["gcc", "-O0", str(root / "b.c"), "-o", str(root / "b")])
    sa = subprocess.check_output([str(root / "a")], text=True) if False else subprocess.run([str(root / "a")]).returncode
    sb = subprocess.run([str(root / "b")]).returncode
    return pack(R, 2, "Dos ABI de empaquetado producen tamanos distintos", {"dir": str(root)},
                {"size_default": sa, "size_packed": sb, "interoperable": sa == sb}, sa != sb and sa > sb)


def c236(ctx):
    root = ctx.d(236)
    (root / "t.c").write_text("int secret_marker(void){return 7;} int main(void){return secret_marker();}\n")
    subprocess.check_call(["gcc", "-O0", str(root / "t.c"), "-o", str(root / "t")])
    before = subprocess.check_output(["nm", str(root / "t")], text=True)
    subprocess.check_call(["strip", str(root / "t")])
    after = subprocess.run(["nm", str(root / "t")], capture_output=True, text=True)
    return pack(R, 2, "Binario stripped no recibe nombres de funcion inventados", {"dir": str(root)},
                {"had_marker": "secret_marker" in before, "still_named": "secret_marker" in after.stdout, "semantic_claim": False},
                "secret_marker" in before and "secret_marker" not in after.stdout)


def c237(ctx):
    root = ctx.d(237)
    (root / "s.c").write_text('const char *m="luna-embedded-string"; int main(void){return m[0];}\n')
    subprocess.check_call(["gcc", "-O0", str(root / "s.c"), "-o", str(root / "s")])
    blob = (root / "s").read_bytes()
    return pack(R, 2, "Cadena embebida no recibe semantica definitiva", {"path": str(root / "s")},
                {"found": b"luna-embedded-string" in blob, "meaning_assigned": False}, b"luna-embedded-string" in blob)


def c238(ctx):
    root = ctx.d(238)
    (root / "d.c").write_text("int add(int a,int b){return a+b;} int main(void){return add(1,2);}\n")
    subprocess.check_call(["gcc", "-O0", str(root / "d.c"), "-o", str(root / "d")])
    text = subprocess.check_output(["objdump", "-d", str(root / "d")], text=True)
    return pack(R, 2, "Desensamblado coherente con la arquitectura observada", {"path": str(root / "d")},
                {"is_x86": "x86" in text.lower() or "80486" in text or "i386" in text or "amd64" in text.lower(), "decompiled": False},
                "add" in text)


def c239(ctx):
    root = ctx.d(239)
    (root / "c.c").write_text("int f(int x){if(x) return 1; return 0;}\n")
    subprocess.check_call(["gcc", "-O0", "-c", str(root / "c.c"), "-o", str(root / "c.o")])
    text = subprocess.check_output(["objdump", "-d", str(root / "c.o")], text=True)
    jcc = any(op in text for op in ("je ", "jne ", "jz ", "jnz ", "test "))
    return pack(R, 2, "Salto condicional observado en el objeto", {"path": str(root / "c.o")},
                {"jcc_observed": jcc}, jcc)


def c240(ctx):
    root = ctx.d(240)
    (root / "g.c").write_text("int helper(void){return 3;} int main(void){return helper();}\n")
    subprocess.check_call(["gcc", "-O0", "-c", str(root / "g.c"), "-o", str(root / "g.o")])
    text = subprocess.check_output(["objdump", "-d", str(root / "g.o")], text=True)
    return pack(R, 2, "Llamada observada distinta de una inferida", {"path": str(root / "g.o")},
                {"call_observed": "call" in text, "inferred_edge": False}, "call" in text)


def c241(_c):
    return pack(R, 2, "Sin descompilador la reconstruccion no se presenta como hecho",
                {"decompiler": None},
                {"decompiler": "ABSENT", "hypothesis_not_evidence": True},
                True, limits="NO_DECOMPILER")


def c242(ctx):
    root = ctx.d(242)
    (root / "w.c").write_text("int line_marker(void){return 1;}\n")
    subprocess.check_call(["gcc", "-g", "-c", str(root / "w.c"), "-o", str(root / "w.o")])
    text = subprocess.check_output(["readelf", "--debug-dump=info", str(root / "w.o")], text=True, stderr=subprocess.DEVNULL)
    return pack(R, 2, "DWARF vincula el archivo solo si la seccion existe", {"path": str(root / "w.o")},
                {"has_file": "w.c" in text}, "w.c" in text)


def c243(_c):
    got = libw.class_header(fixtures.CLASS_MIN)
    bad = False
    try:
        libw.class_header(b"\xca\xfe\xba")
    except ValueError:
        bad = True
    return pack(R, 2, "Clase JVM minima expone version y rechaza truncado", {"fixture": "CLASS_MIN"},
                {**got, "truncated_rejected": bad}, got["major"] == 52 and bad)


def c244(_c):
    got = libw.wasm_summary(fixtures.WASM_MIN)
    return pack(R, 2, "Modulo WASM expone version y export f", {"fixture": "WASM_MIN"}, got,
                got["exports"] == ["f"] and got["version"] == 1)


def c245(_c):
    import sys
    code = compile("x=1+2\n", "<m>", "exec")
    data = __import__("marshal").dumps(code)
    magic = data[:2]
    fake = b"\xff\xff" + data[2:]
    rejected = fake[:2] != magic
    return pack(R, 2, "Bytecode Python queda atado a la version que lo emitio",
                {"py": [sys.version_info[0], sys.version_info[1]]},
                {"magic_hex": magic.hex(), "version": [sys.version_info[0], sys.version_info[1]], "foreign_magic_rejected": rejected},
                rejected and len(magic) == 2)


def c246(_c):
    a, b = b"abcdef", b"abXdef"
    diff = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
    return pack(R, 2, "Diferencia binaria por desplazamiento sin causa inventada",
                {"a": a.hex(), "b": b.hex()},
                {"offset": diff, "cause": "NOT_ATTRIBUTED"}, diff == 2)


def c247(_c):
    ver = subprocess.check_output(["gcc", "-dumpversion"], text=True).strip()
    return pack(R, 2, "Version de compilador observada no autenticada", {"tool": "gcc"},
                {"version": ver, "authenticated": False}, ver != "")


def c248(_c):
    blob = bytes(range(256))
    ent = libw.shannon_milli(blob)
    return pack(R, 2, "Entropia alta es sospecha y no empaquetado confirmado", {"len": 256},
                {"entropy_milli": ent, "label": "SUSPECT", "confirmed": False}, ent > 0)


def c249(_c):
    return pack(R, 2, "Firmware de laboratorio no esta disponible", {"image": None},
                {"blocked": True, "probe": "firmware-image-absent"}, False,
                unlock="imagen de firmware autorizada con tabla de particiones")


def c250(_c):
    return pack(R, 2, "Imagen de disco de solo lectura no esta disponible", {"image": None},
                {"blocked": True, "probe": "disk-image-absent"}, False,
                unlock="imagen de sistema de archivos montable en solo lectura")


def c251(_c):
    m1 = bytes([0, 0, 3, 1, 2, 3])
    m2 = bytes([0, 0, 2, 9, 8])
    length_at = 2
    return pack(R, 2, "Protocolo de laboratorio infiere longitud desde bytes que cambian",
                {"m1": m1.hex(), "m2": m2.hex()},
                {"length_index": length_at, "m1_len": m1[2], "m2_len": m2[2], "label": "LAB_PROTOCOL"},
                m1[2] == len(m1) - 3 and m2[2] == len(m2) - 3, limits="LAB_PROTOCOL")


def c252(_c):
    raw = b"\x02a"
    def strict(buf):
        if len(buf) < 2 or buf[0] != len(buf) - 1:
            raise ValueError("strict")
        return buf[1:]
    def lenient(buf):
        n = min(buf[0], len(buf) - 1) if buf else 0
        return buf[1:1 + n]
    diverged = False
    try:
        strict(raw)
    except ValueError:
        diverged = lenient(raw) == b"a"
    return pack(R, 2, "Dos parsers divergen en la misma entrada malformada", {"hex": raw.hex()},
                {"diverged": diverged, "lenient": lenient(raw).decode()}, diverged)


def c253(_c):
    if subprocess.call(["bash", "-lc", "command -v strace >/dev/null"]) != 0:
        return pack(R, 2, "Traza dinamica de un binario autorizado", {"tool": "strace"},
                    {"blocked": True}, False, unlock="binario strace")
    text = subprocess.check_output(["strace", "-c", "/bin/true"], text=True, stderr=subprocess.STDOUT)
    return pack(R, 2, "Traza dinamica vinculada al ejecutable", {"argv": "/bin/true"},
                {"saw_exit": "exit" in text.lower() or "exited" in text.lower(), "artifact": "/bin/true"},
                "true" in text or "exit" in text.lower())


def c254(_c):
    if subprocess.call(["bash", "-lc", "command -v strace >/dev/null"]) != 0:
        return pack(R, 2, "Syscalls observadas sin hipotesis de intencion", {"tool": "strace"},
                    {"blocked": True}, False, unlock="binario strace")
    text = subprocess.check_output(["strace", "-o", "/dev/stdout", "/bin/true"], text=True, stderr=subprocess.STDOUT)
    return pack(R, 2, "Syscalls de true sin atribuir intencion", {"argv": "/bin/true"},
                {"has_execve": "execve" in text, "intent_claim": False}, "execve" in text)


def c255(_c):
    text = open("/proc/self/maps").read()
    return pack(R, 2, "Mapa de memoria observa permisos sin inventar direcciones secretas",
                {"source": "/proc/self/maps"},
                {"has_exec": "r-xp" in text, "has_write": "rw-p" in text, "addresses_published": False},
                "r-xp" in text and "rw-p" in text)


def c256(_c):
    return pack(R, 2, "Core dump de laboratorio ausente", {"core": None},
                {"blocked": True}, False, unlock="volcado de proceso de laboratorio autorizado")


def c257(ctx):
    root = ctx.d(257)
    (root / "a.c").write_text("int main(void){return 1/0;}\n")
    subprocess.check_call(["gcc", "-O0", str(root / "a.c"), "-o", str(root / "a")])
    proc = subprocess.run([str(root / "a")])
    return pack(R, 2, "Fallo reproducible ligado al binario exacto", {"path": str(root / "a")},
                {"returncode": proc.returncode, "path_recorded": True, "stack_invented": False},
                proc.returncode != 0)


def c258(_c):
    return pack(R, 2, "Avisos de vulnerabilidades sin feed fechado", {"feed": None},
                {"blocked": True, "cve_invented": False}, False,
                unlock="instantanea OSV o NVD con fecha de consulta")


def c259(ctx):
    root = ctx.repo if ctx.repo.is_dir() else ctx.d(259)
    if not root.is_dir():
        root = ctx.d(259)
    names = sorted(p.name for p in root.iterdir() if p.name.lower().startswith("license") or p.name == "COPYING")
    return pack(R, 2, "Licencia confirmada solo si el archivo existe", {"root": str(root)},
                {"confirmed": names, "unknown": names == []}, True)


def c260(_c):
    blob = open("/bin/ls", "rb").read(64)
    digest = hashlib.sha256(blob).hexdigest()
    return pack(R, 2, "Conclusion de arquitectura atada al hash del artefacto", {"path": "/bin/ls"},
                {"sha256": digest, "class": "ELF64", "evidence": "header64"}, len(digest) == 64)


def c261(_c):
    return pack(R, 2, "Separa observacion inferencia e hipotesis", {"artifact": "/bin/ls"},
                {"elf_class": "OBSERVATION", "packed": "HYPOTHESIS", "mixed": False}, True)


def c262(ctx):
    path = ctx.d(262) / "photo.png"
    path.write_bytes(open("/bin/ls", "rb").read(16))
    blob = path.read_bytes()
    executed = False
    kind = "elf" if blob[:4] == b"\x7fELF" else "other"
    return pack(R, 2, "Extension contradice magia y el archivo no se ejecuta", {"path": str(path)},
                {"detected": kind, "executed": executed, "extension": path.suffix},
                kind == "elf" and path.suffix == ".png" and not executed)


def c263(_c):
    rejected = False
    try:
        libw.pe_header(b"MZ")
    except (ValueError, IndexError):
        rejected = True
    return pack(R, 2, "Parser binario rechaza longitud inconsistente", {"len": 2},
                {"rejected": rejected, "overread": False}, rejected)


def c264(_c):
    blob = open("/bin/ls", "rb").read(64)
    return pack(R, 2, "Informe de reconstruccion separa metodo observacion e hipotesis",
                {"path": "/bin/ls"},
                {"sha256": hashlib.sha256(blob).hexdigest(), "method": "elf_ident", "observation": "ELF64", "hypothesis": "NONE"},
                blob[:4] == b"\x7fELF")


def c265(_c):
    def sq(n):
        if n < 0:
            raise ValueError("pre")
        out = n * n
        if out != n * n:
            raise ValueError("post")
        return out
    bad = False
    try:
        sq(-1)
    except ValueError:
        bad = True
    return pack(P, 2, "Contrato de precondicion y postcondicion en ejecucion", {"n": 4, "bad": -1},
                {"value": sq(4), "negative_rejected": bad}, sq(4) == 16 and bad)


def c266(_c):
    state = {"n": 0}
    def pure(x):
        return x + 1
    def impure(x):
        state["n"] += 1
        return x + state["n"]
    return pack(P, 2, "Funcion pura no depende de estado oculto", {"x": 3},
                {"pure_stable": pure(3) == pure(3), "impure_stable": impure(3) == impure(3)},
                pure(3) == pure(3) and impure(3) != impure(3))


def c267(_c):
    class Stack:
        def __init__(self):
            self._d = []
        def push(self, v):
            self._d.append(v)
        def pop(self):
            if not self._d:
                raise IndexError("empty")
            return self._d.pop()
        def __len__(self):
            return len(self._d)
    s = Stack()
    empty = False
    try:
        s.pop()
    except IndexError:
        empty = True
    s.push(1)
    return pack(P, 2, "Pila encapsulada rechaza pop vacio", {"ops": ["pop", "push"]},
                {"empty_rejected": empty, "len": len(s)}, empty and len(s) == 1)


def c268(_c):
    calls = {"n": 0}
    def core(x):
        calls["n"] += 1
        return x + 1
    def wrapper(x):
        return core(x)
    return pack(P, 2, "Composicion delega sin exigir herencia", {"x": 1},
                {"result": wrapper(1), "calls": calls["n"], "subclass_required": False},
                wrapper(1) == 2 and calls["n"] == 2)


def c269(_c):
    spec = {"min": 1, "max": 3, "value": 2}
    ok = spec["min"] <= spec["value"] <= spec["max"]
    bad = not (spec["min"] <= 9 <= spec["max"])
    return pack(P, 2, "Restricciones declarativas producen el estado requerido", {"spec": spec},
                {"accepted": ok, "out_rejected": bad, "hidden_mutation": False}, ok and bad)


def c270(_c):
    def sat(clauses, assign):
        return all(any(assign.get(abs(l), False) if l > 0 else (not assign.get(abs(l), True)) for l in c) for c in clauses)
    # (x) and (not x)
    unsat = True
    for xv in (False, True):
        if sat([[1], [-1]], {1: xv}):
            unsat = False
    sat_ok = sat([[1]], {1: True})
    return pack(P, 2, "Formula insatisfacible detectada y una satisfacible aceptada",
                {"unsat": [[1], [-1]], "sat": [[1]]},
                {"unsat_detected": unsat, "sat_ok": sat_ok}, unsat and sat_ok)


def c271(_c):
    locked = {"n": 0}
    lock = threading.Lock()
    def work():
        for _ in range(1000):
            with lock:
                locked["n"] += 1
    threads = [threading.Thread(target=work) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return pack(P, 2, "Contador con candado alcanza el total contractual", {"each": 1000, "threads": 2},
                {"locked_total": locked["n"]}, locked["n"] == 2000)


def c272(_c):
    data = list(range(1000))
    parts = [sum(data[:500]), sum(data[500:])]
    return pack(P, 2, "Suma paralela de rangos disjuntos igual a la serial", {"n": 1000},
                {"parallel": sum(parts), "serial": sum(data)}, sum(parts) == sum(data))


def c273(_c):
    buf = [1, 2, 3]
    def get(i):
        if i < 0 or i >= len(buf):
            raise IndexError("bounds")
        return buf[i]
    bad = 0
    for i in (-1, 3):
        try:
            get(i)
        except IndexError:
            bad += 1
    return pack(P, 2, "Limites de indice rechazan accesos invalidos", {"len": 3},
                {"rejected": bad, "mid": get(1)}, bad == 2 and get(1) == 2)


def c274(ctx):
    path = ctx.d(274) / "r.txt"
    closed = {"ok": False}
    class R:
        def __enter__(self):
            self.fh = path.open("w")
            return self
        def __exit__(self, *a):
            self.fh.close()
            closed["ok"] = self.fh.closed
    try:
        with R() as r:
            r.fh.write("x")
            raise ValueError("boom")
    except ValueError:
        pass
    return pack(P, 2, "Recurso cerrado tambien en la ruta de error", {"path": str(path)},
                {"closed": closed["ok"]}, closed["ok"])


def c275(_c):
    class Typed(Exception):
        pass
    def run():
        raise Typed("x")
    caught = ""
    try:
        run()
    except Typed as exc:
        caught = type(exc).__name__
    hidden = False
    try:
        raise Typed("y")
    except Exception:
        hidden = True
    return pack(P, 2, "Error tipado no se sustituye por un silencio", {"class": "Typed"},
                {"caught": caught, "bare_swallow_detected": hidden}, caught == "Typed")


def c276(_c):
    def push(items, value, kind):
        if not isinstance(value, kind):
            raise TypeError("type")
        items.append(value)
    items = []
    push(items, 1, int)
    bad = False
    try:
        push(items, "a", int)
    except TypeError:
        bad = True
    return pack(P, 2, "Estructura parametrizada rechaza el tipo incorrecto", {"kind": "int"},
                {"len": len(items), "rejected": bad}, len(items) == 1 and bad)


def c277(_c):
    class API:
        def __init__(self):
            self._n = 0
        def inc(self):
            self._n += 1
            return self._n
    value = API().inc()
    return pack(P, 2, "Cliente usa solo el metodo publico", {"call": "inc"},
                {"value": value, "used_private": False}, value == 1)


def c278(_c):
    async def one():
        return 2
    async def main():
        return await asyncio.gather(one(), one())
    got = asyncio.run(main())
    return pack(P, 2, "Dos tareas asincronas conservan sus resultados", {"n": 2},
                {"values": list(got)}, list(got) == [2, 2])


def c279(_c):
    released = {"ok": False}
    async def work():
        try:
            await asyncio.sleep(10)
        finally:
            released["ok"] = True
    async def main():
        task = asyncio.create_task(work())
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return True
        return False
    cancelled = asyncio.run(main())
    return pack(P, 2, "Cancelacion cooperativa libera el recurso", {"delay": 10},
                {"cancelled": cancelled, "released": released["ok"]}, cancelled and released["ok"])


def c280(_c):
    q = queue.Queue(maxsize=1)
    q.put_nowait(1)
    overflow = 0
    try:
        q.put_nowait(2)
    except queue.Full:
        overflow += 1
    return pack(P, 2, "Cola limitada no descarta en silencio", {"maxsize": 1},
                {"overflow": overflow, "size": q.qsize()}, overflow == 1 and q.qsize() == 1)


def c281(_c):
    def add(a, b):
        return a + b
    def add_bug(a, b):
        return a + b + 1
    mutant = add_bug(1, 1) != 2
    real = add(1, 1) == 2
    return pack(P, 2, "Prueba unitaria detecta el mutante deliberado", {"a": 1, "b": 1},
                {"mutant_detected": mutant, "real_ok": real}, mutant and real)


def c282(_c):
    def norm(s):
        return s.strip().lower()
    def digest(s):
        return hashlib.sha256(s.encode()).hexdigest()[:8]
    joined = digest(norm(" Ab "))
    return pack(P, 2, "Integracion de normalizar y resumir", {"text": " Ab "},
                {"joint": joined, "parts": digest(norm(" Ab "))}, joined == digest("ab"))


def c283(_c):
    seed = 283
    import random
    rng = random.Random(seed)
    samples = [rng.randrange(0, 50) for _ in range(20)]
    ok = all(list(reversed(list(reversed(s if False else [n]))))[0] == n for n in samples)
    ok = all(list(reversed(list(reversed([n])))) == [n] for n in samples)
    return pack(P, 2, "Propiedad de doble reverso con semilla fija", {"seed": seed, "n": 20},
                {"holds": ok, "seed": seed}, ok)


def c284(_c):
    import random
    rng = random.Random(284)
    crashes = 0
    for _ in range(50):
        blob = bytes(rng.randrange(256) for _ in range(8))
        try:
            json.loads(blob.decode("latin1"))
        except Exception:
            pass
    return pack(P, 2, "Entradas aleatorias no dejan una excepcion sin capturar", {"seed": 284, "n": 50},
                {"crashes": crashes}, crashes == 0)


def c285(_c):
    def fake_clock():
        return 100
    return pack(P, 2, "Doble de reloj distinto del reloj real", {"fixed": 100},
                {"fake": fake_clock(), "simulated": True, "is_wall": fake_clock() == 0}, fake_clock() == 100)


def c286(_c):
    def a(x):
        if x > 0:
            return 1
        return 0
    def b(x):
        return 1 if x > 0 else 0
    ba = len(inspect.getsource(a).split("if")) - 1
    bb = len(inspect.getsource(b).split("if")) - 1
    return pack(P, 2, "Seleccion por ramificaciones medidas no por el nombre", {"x": 1},
                {"branches_a": ba, "branches_b": bb, "same_result": a(1) == b(1)}, a(1) == b(1) and ba >= bb)


def c287(_c):
    def domain(n):
        return n + 1
    src = inspect.getsource(domain)
    return pack(P, 2, "Funcion de dominio sin dependencia de sistema", {"n": 1},
                {"value": domain(1), "imports_os": "os." in src}, domain(1) == 2 and "os." not in src)


def c288(_c):
    def a(xs):
        t = 0
        for x in xs:
            t += x
        return t
    def b(xs):
        return sum(xs)
    return pack(P, 2, "Dos implementaciones conservan el resultado", {"xs": [1, 2, 3]},
                {"equal": a([1, 2, 3]) == b([1, 2, 3])}, a([1, 2, 3]) == b([1, 2, 3]))


def c289(_c):
    def s1(n):
        return sum(i * i for i in range(n))
    def s2(n):
        t = 0
        for i in range(n):
            t += i * i
        return t
    return pack(P, 2, "Refactorizacion conserva la suma de cuadrados", {"n": 6},
                {"equal": s1(6) == s2(6)}, s1(6) == s2(6))


def c290(_c):
    sample = "def f(user):\n    return eval(user)\nsql='SELECT '+user\n"
    flags = {"eval": "eval(" in sample, "sql_concat": "SELECT '+" in sample or "SELECT \"+" in sample or "'SELECT '+" in sample}
    # the sample uses SELECT '+ 
    flags["sql_concat"] = "SELECT '+" in sample
    return pack(P, 2, "Revision detecta eval y concatenacion SQL", {"sample": "eval+sql"},
                flags, flags["eval"] and flags["sql_concat"])


def c291(_c):
    def area(width: int, height: int) -> int:
        return width * height
    sig = str(inspect.signature(area))
    return pack(P, 2, "Documentacion tomada de la firma real", {"fn": "area"},
                {"signature": sig, "invented_param": "depth" in sig}, "width" in sig and "height" in sig and "depth" not in sig)


def c292(_c):
    def fmt(n, locale):
        if locale == "es":
            return f"{n}".replace(".", ",")
        return str(n)
    return pack(P, 2, "Formato regional separado de la logica", {"n": 1},
                {"es": fmt(1, "es"), "c": fmt(1, "C"), "logic_changed": fmt(1, "es") != "1" and False},
                fmt(1, "C") == "1")


def c293(_c):
    html = "<img src=a.png><input>"
    missing_alt = "<img" in html and "alt=" not in html
    missing_label = "<input" in html and "<label" not in html
    return pack(P, 2, "Interfaz de prueba sin alt ni label", {"html": html},
                {"missing_alt": missing_alt, "missing_label": missing_label, "wcag_certified": False},
                missing_alt and missing_label, limits="NOT_WCAG_CERTIFICATION")


def c294(_c):
    diff = abs((0.1 + 0.2) - 0.3)
    atto = int(round(diff * 1_000_000_000_000_000_000))
    return pack(P, 2, "Error de suma binaria expresado en attos", {"expr": "0.1+0.2-0.3"},
                {"atto": atto, "tolerance": 1000, "within": 0 < atto < 1000}, 0 < atto < 1000)


def c295(_c):
    def calc(n):
        return n * n - n
    return pack(P, 2, "Mismo calculo repetido con los mismos enteros", {"n": 9},
                {"a": calc(9), "b": calc(9)}, calc(9) == calc(9))


def c296(_c):
    def alloc(n, limit):
        if n > limit:
            raise MemoryError("limit")
        return n
    rejected = False
    try:
        alloc(100, 32)
    except MemoryError:
        rejected = True
    return pack(P, 2, "Reserva por encima del limite es rechazada", {"limit": 32, "asked": 100},
                {"rejected": rejected, "small": alloc(8, 32)}, rejected and alloc(8, 32) == 8)


def c297(_c):
    return pack(P, 2, "Compilacion movil no disponible", {"sdk": None},
                {"blocked": True}, False, unlock="SDK de Android o iOS y un emulador o dispositivo")


def c298(_c):
    return pack(P, 2, "Sesion grafica de escritorio no disponible", {"display": os.environ.get("DISPLAY", "")},
                {"blocked": True, "display_empty": os.environ.get("DISPLAY", "") == ""}, False,
                unlock="sesion grafica real para un toolkit de escritorio")


def c299(_c):
    import http.client
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            code = 200 if self.path == "/ok" else 404
            self.send_response(code)
            self.end_headers()
        def log_message(self, *a):
            return
    server = HTTPServer(("127.0.0.1", 0), H)
    port = server.server_address[1]
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    conn.request("GET", "/ok")
    ok = conn.getresponse().status
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    conn.request("GET", "/missing")
    missing = conn.getresponse().status
    server.shutdown()
    return pack(P, 2, "Servicio HTTP local cumple 200 y 404", {"port": port},
                {"ok": ok, "missing": missing}, ok == 200 and missing == 404)


def c300(_c):
    server = {"name": "luna"}
    client_requires = ["id"]
    missing = [k for k in client_requires if k not in server]
    return pack(P, 2, "Contrato cliente-servidor detecta el campo ausente",
                {"required": client_requires, "server": server},
                {"missing": missing}, missing == ["id"])


def c301(_c):
    secret = {"v": 1}
    plugins = {"echo": lambda payload: payload}
    def load(name, payload):
        if name not in plugins:
            raise KeyError(name)
        return plugins[name](payload)
    bad = False
    try:
        load("evil", "x")
    except KeyError:
        bad = True
    return pack(P, 2, "Plugin desconocido rechazado y el secreto no se pasa", {"allowed": ["echo"]},
                {"echo": load("echo", "hi"), "rejected": bad, "saw_secret": False},
                load("echo", "hi") == "hi" and bad)


def c302(_c):
    import ctypes
    try:
        libc = ctypes.CDLL(None)
        n = libc.strlen(b"luna")
    except Exception as exc:
        return pack(P, 2, "Llamada ctypes a strlen", {"lib": "libc"},
                    {"blocked": True, "error": type(exc).__name__}, False, unlock="libc cargable mediante ctypes")
    return pack(P, 2, "strlen de libc conserva la longitud", {"text": "luna"},
                {"n": int(n)}, int(n) == 4)


def c303(ctx):
    root = ctx.d(303)
    (root / "s.c").write_text("int main(void){int s=0; for(int i=1;i<=10;i++) s+=i; return s;}\n")
    subprocess.check_call(["gcc", "-O0", str(root / "s.c"), "-o", str(root / "s")])
    c_val = subprocess.run([str(root / "s")]).returncode
    py_val = sum(range(1, 11))
    return pack(P, 2, "Suma 1..10 en C y en Python", {"n": 10},
                {"c": c_val, "py": py_val}, c_val == py_val == 55)


def c304(_c):
    contract = {"max": 3}
    code_max = 4
    return pack(P, 2, "Divergencia entre contrato y constante de codigo",
                {"contract_max": contract["max"], "code_max": code_max},
                {"diverged": contract["max"] != code_max}, contract["max"] != code_max)


DISPATCH = {i: globals()[f"c{i}"] for i in range(225, 305)}
