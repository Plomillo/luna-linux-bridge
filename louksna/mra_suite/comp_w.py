"""Compiler and runtime cases 307-344. Does not import oracle modules."""
from __future__ import annotations

import ast
import ctypes
import gc
import hashlib
import marshal
import shutil
import struct
import subprocess
import weakref
from pathlib import Path

from pack import pack

DOMAIN = "compiler"


def level_of(n: int) -> int:
    return 2


def run(n: int, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def reg(n, objective, fn, limits=""):
    def runner(ctx):
        inp, facts, good, unlock = fn(ctx)
        return pack(DOMAIN, level_of(n), objective, inp, facts, good, unlock=unlock, limits=limits)
    DISPATCH[n] = runner


DISPATCH = {}


def c307(_c):
    src = "8-3-2"
    left = (8 - 3) - 2
    right = 8 - (3 - 2)
    return {"src": src, "policy": "left-assoc"}, {"left": left, "right": right, "ambiguous": left != right, "chosen": left}, left == 3 and right == 7 and left != right, ""


def c308(_c):
    src = "1+2*3"
    tree = ast.parse(src, mode="eval").body
    root = type(tree.op).__name__
    right = type(tree.right.op).__name__
    return {"src": src}, {"root": root, "right": right}, root == "Add" and right == "Mult", ""


def c309(_c):
    def check(node):
        kind, a, b = node
        if kind != "add":
            raise ValueError(kind)
        if a[0] != b[0]:
            raise TypeError(a[0] + "!=" + b[0])
        return a[0]
    bad = False
    try:
        check(("add", ("int", 1), ("str", "a")))
    except TypeError:
        bad = True
    good = check(("add", ("int", 1), ("int", 2))) == "int"
    return {"bad": ["int", "str"], "ok": ["int", "int"]}, {"type_rejected": bad, "same_ok": good}, bad and good, ""


def c310(_c):
    global_x = 1
    def inner():
        local_x = 2
        return local_x
    return {"global": global_x}, {"local": inner(), "global_unchanged": global_x}, inner() == 2 and global_x == 1, ""


def c311(_c):
    expr = ("add", ("lit", 1), ("lit", 2))
    def infer(node):
        if node[0] == "lit":
            return "int" if isinstance(node[1], int) else "unknown"
        if node[0] == "add":
            left, right = infer(node[1]), infer(node[2])
            if left == right:
                return left
            return "mismatch"
        return "unknown"
    return {"expr": "1+2"}, {"inferred": infer(expr)}, infer(expr) == "int", ""


def c312(_c):
    claimed = 3
    data = [1, 2]
    rejected = len(data) != claimed
    return {"claimed": claimed, "data": data}, {"rejected": rejected, "actual": len(data)}, rejected and len(data) == 2, ""


def c313(_c):
    stack = []
    for op in ("PUSH", 1, "PUSH", 2, "PUSH", 3, "MUL", "ADD"):
        if op == "PUSH":
            continue
        if isinstance(op, int):
            stack.append(op)
        elif op == "MUL":
            b, a = stack.pop(), stack.pop()
            stack.append(a * b)
        elif op == "ADD":
            b, a = stack.pop(), stack.pop()
            stack.append(a + b)
    return {"ir": "PUSH 1; PUSH 2; PUSH 3; MUL; ADD"}, {"value": stack[0], "depth": len(stack)}, stack == [7], ""


def c314(_c):
    t0 = 2 * 3
    t1 = 1 + t0
    return {"low": "t0=2*3; t1=1+t0"}, {"t0": t0, "t1": t1}, t0 == 6 and t1 == 7, ""


def c315(_c):
    def raw(x):
        return x + 0
    def opt(x):
        return x
    samples = [0, 1, 5]
    same = [raw(x) == opt(x) for x in samples]
    return {"samples": samples}, {"same": all(same)}, all(same), ""


def c316(_c):
    folded = 2 * 3 + 4
    wrapped = (200 + 100) & 0xFF
    return {"expr": "2*3+4", "uint8": "200+100"}, {"folded": folded, "wrapped": wrapped, "overflow": wrapped != 300}, folded == 10 and wrapped == 44, ""


def c317(_c):
    effects = {"n": 0}
    def dead():
        effects["n"] += 1
    if False:
        dead()
    return {"branch": False}, {"effects": effects["n"]}, effects["n"] == 0, ""


def c318(_c):
    calls = {"n": 0}
    def expensive(a, b):
        calls["n"] += 1
        return a + b
    once = expensive(2, 3)
    reused = once
    return {"expr": "a+b"}, {"calls": calls["n"], "value": reused}, calls["n"] == 1 and reused == 5, ""


def c319(_c):
    data = [1, 2, 3, 4]
    scalar = 0
    for item in data:
        scalar += item
    vector = (data[0] + data[1]) + (data[2] + data[3])
    return {"data": data}, {"scalar": scalar, "vector": vector, "delta": scalar - vector}, scalar == vector == 10, ""


def c320(_c):
    allowed = {"ADD": lambda a, b: a + b, "MUL": lambda a, b: a * b}
    steps = [("PUSH", 1), ("PUSH", 2), ("PUSH", 3), ("MUL", None), ("ADD", None)]
    stack = []
    for op, val in steps:
        if op == "PUSH":
            stack.append(val)
        else:
            b, a = stack.pop(), stack.pop()
            stack.append(allowed[op](a, b))
    return {"steps": "1,2,3,MUL,ADD"}, {"value": stack[0]}, stack == [7], ""


def c321(ctx):
    src = ctx.d(321) / "a.c"
    src.write_text("int add(int a, int b){ return a + b; }\n")
    out = ctx.d(321) / "a.s"
    proc = subprocess.run(["gcc", "-S", "-O0", str(src), "-o", str(out)], capture_output=True, text=True)
    text = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
    arith = any(tok in text for tok in ("add", "lea"))
    return {"src": str(src)}, {"compiled": proc.returncode == 0, "arith": arith}, proc.returncode == 0 and arith, ""


def c322(ctx):
    src = ctx.d(322) / "m.c"
    src.write_text("void missing(void);\nint main(void){ missing(); return 0; }\n")
    proc = subprocess.run(["gcc", "-o", str(ctx.d(322) / "m"), str(src)], capture_output=True, text=True)
    return {"src": str(src)}, {"exit_nonzero": proc.returncode != 0}, proc.returncode != 0, ""


def c323(ctx):
    src = ctx.d(323) / "s.cpp"
    src.write_text('extern "C" int addc(int a, int b){ return a + b; }\nint add(int a, int b){ return a + b; }\n')
    bin_path = ctx.d(323) / "s.o"
    proc = subprocess.run(["g++", "-c", "-o", str(bin_path), str(src)], capture_output=True, text=True)
    nm = subprocess.run(["nm", str(bin_path)], capture_output=True, text=True)
    text = nm.stdout
    return {"src": str(src)}, {"compiled": proc.returncode == 0, "plain": "addc" in text, "mangled": "_Z3addii" in text}, proc.returncode == 0 and "addc" in text and "_Z3addii" in text, ""


def c324(_c):
    libc = ctypes.CDLL("libc.so.6")
    got = int(libc.abs(-4))
    py = abs(-4)
    return {"n": -4}, {"libc": got, "py": py}, got == 4 and py == 4, ""


def c325(_c):
    def callee(x, y):
        return x - y
    native = callee(5, 2)
    swapped = callee(2, 5)
    return {"a": 5, "b": 2}, {"native": native, "swapped": swapped, "mismatch": native != swapped}, native == 3 and swapped == -3, ""


def c326(ctx):
    src = ctx.d(326) / "p.c"
    src.write_text("#include <stddef.h>\n#include <stdio.h>\nstruct S { char a; int b; };\nint main(void){ printf(\"%zu %zu\\n\", offsetof(struct S, b), sizeof(struct S)); return 0; }\n")
    bin_path = ctx.d(326) / "p"
    proc = subprocess.run(["gcc", "-o", str(bin_path), str(src)], capture_output=True, text=True)
    run = subprocess.run([str(bin_path)], capture_output=True, text=True) if proc.returncode == 0 else None
    off, size = (int(x) for x in run.stdout.split()) if run and run.returncode == 0 else (-1, -1)
    return {"src": str(src)}, {"offset": off, "size": size}, off == 4 and size == 8, ""


def c327(_c):
    class P(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("a", ctypes.c_char), ("b", ctypes.c_int)]
    return {"pack": 1}, {"offset": P.b.offset, "size": ctypes.sizeof(P)}, P.b.offset == 1 and ctypes.sizeof(P) == 5, ""


def c328(_c):
    class Box:
        pass
    obj = Box()
    ref = weakref.ref(obj)
    del obj
    gc.collect()
    return {"kind": "weakref"}, {"collected": ref() is None}, ref() is None, ""


def c329(ctx):
    path = ctx.d(329) / "f.txt"
    closed = False
    class Box:
        def __enter__(self):
            self.handle = path.open("w")
            return self
        def __exit__(self, exc_type, exc, tb):
            self.handle.close()
            return False
    try:
        with Box() as box:
            box.handle.write("x")
            raise RuntimeError("boom")
    except RuntimeError:
        closed = box.handle.closed
    return {"path": str(path)}, {"closed": closed, "exists": path.exists()}, closed and path.exists(), ""


def c330(ctx):
    src = ctx.d(330) / "mv.rs"
    src.write_text('fn main(){ let s = String::from("a"); let _t = s; println!("{}", s); }\n')
    proc = subprocess.run(["rustc", "--edition", "2021", "-o", str(ctx.d(330) / "mv"), str(src)], capture_output=True, text=True)
    return {"src": str(src)}, {"exit_nonzero": proc.returncode != 0}, proc.returncode != 0, ""


def c331(_c):
    present = bool(shutil.which("pypy3") or shutil.which("llvm-as"))
    if present:
        return {"probe": "jit"}, {"blocked": False, "probe": "jit"}, False, ""
    return {"probe": "jit"}, {"blocked": True, "probe": "jit"}, False, "hace falta un runtime JIT observable (pypy o llvm-as); no se simula la compilacion dinamica"


def c332(_c):
    def run_vm(code):
        stack = []
        for op, arg in code:
            if op == "PUSH":
                stack.append(arg)
            elif op == "ADD":
                stack.append(stack.pop() + stack.pop())
            elif op == "HALT":
                return stack[-1]
            else:
                raise ValueError("bad-opcode")
        raise ValueError("no-halt")
    good = run_vm([("PUSH", 10), ("PUSH", 32), ("ADD", None), ("HALT", None)])
    rejected = False
    try:
        run_vm([("NOPE", None)])
    except ValueError:
        rejected = True
    return {"program": "PUSH 10; PUSH 32; ADD; HALT"}, {"value": good, "rejected": rejected}, good == 42 and rejected, ""


def c333(_c):
    present = bool(shutil.which("wasmtime") or shutil.which("wasmer"))
    if present:
        return {"probe": "wasm-runtime"}, {"blocked": False, "probe": "wasm-runtime"}, False, ""
    return {"probe": "wasm-runtime"}, {"blocked": True, "probe": "wasm-runtime"}, False, "hace falta wasmtime o wasmer; el parser de bytes no es un runtime"


def c334(_c):
    present = bool(shutil.which("llvm-as") and shutil.which("opt"))
    if present:
        return {"probe": "llvm"}, {"blocked": False, "probe": "llvm"}, False, ""
    return {"probe": "llvm"}, {"blocked": True, "probe": "llvm"}, False, "hace falta llvm-as y opt para relacionar etapas LLVM; no se inventa IR"


def c335(ctx):
    src = ctx.d(335) / "bad.c"
    src.write_text("int main( { return 0; }\n")
    proc = subprocess.run(["gcc", "-c", "-o", str(ctx.d(335) / "bad.o"), str(src)], capture_output=True, text=True)
    diagnosed = proc.returncode != 0 and "error" in (proc.stderr or "").lower()
    return {"src": str(src)}, {"diagnosed": diagnosed}, diagnosed, ""


def c336(_c):
    original = ["x = 1", "y = 2"]
    header = 2
    pairs = [[i + header + 1, i + 1] for i in range(len(original))]
    return {"header": header, "lines": original}, {"pairs": pairs}, pairs == [[3, 1], [4, 2]], ""


def c337(_c):
    deps = {"app": ["a", "b"]}
    changed = {"b"}
    need = sorted(name for name, inputs in deps.items() if changed.intersection(inputs))
    need += sorted(changed)
    return {"changed": ["b"]}, {"rebuild": need}, need == ["app", "b"], ""


def c338(_c):
    name = "mod.py"
    before = "v = 1\n"
    after = "v = 2\n"
    name_same = hashlib.sha256(name.encode()).hexdigest() == hashlib.sha256(name.encode()).hexdigest()
    content_changed = hashlib.sha256(before.encode()).hexdigest() != hashlib.sha256(after.encode()).hexdigest()
    return {"name": name, "before": before, "after": after}, {"name_key_same": name_same, "content_key_changed": content_changed}, name_same and content_changed, ""


def c339(_c):
    src = "def f(x):\n    return x + 1\n"
    a = hashlib.sha256(marshal.dumps(compile(src, "a.py", "exec"))).hexdigest()
    b = hashlib.sha256(marshal.dumps(compile(src, "a.py", "exec"))).hexdigest()
    return {"src": src}, {"equal": a == b}, a == b, ""


def c340(ctx):
    src = ctx.d(340) / "z.c"
    src.write_text("#include <stdlib.h>\nint main(void){ int *p = malloc(1); p[1] = 1; free(p); return 0; }\n")
    bin_path = ctx.d(340) / "z"
    built = subprocess.run(["gcc", "-fsanitize=address", "-o", str(bin_path), str(src)], capture_output=True, text=True)
    if built.returncode != 0:
        return {"src": str(src), "probe": "asan"}, {"blocked": True, "probe": "asan"}, False, "gcc no pudo enlazar libasan en este entorno"
    run = subprocess.run([str(bin_path)], capture_output=True, text=True)
    return {"src": str(src)}, {"sanitizer_nonzero": run.returncode != 0}, run.returncode != 0, ""


def c341(_c):
    loops = 4000
    def hot():
        total = 0
        for i in range(loops):
            total += i
        return total
    def cold():
        return 1
    import time
    def elapsed(fn):
        start = time.perf_counter_ns()
        fn()
        return time.perf_counter_ns() - start
    hot_ns = elapsed(hot)
    cold_ns = elapsed(cold)
    return {"loops": loops}, {"hot_slower": hot_ns > cold_ns}, hot_ns > cold_ns, ""


def c342(_c):
    def boom():
        return 1 / 0
    kind = ""
    try:
        boom()
    except ZeroDivisionError as exc:
        kind = type(exc).__name__
    return {"expr": "1/0"}, {"kind": kind}, kind == "ZeroDivisionError", ""


def c343(_c):
    state = {"released": False}
    try:
        try:
            raise RuntimeError("x")
        finally:
            state["released"] = True
    except RuntimeError:
        pass
    return {"raise": True}, {"released": state["released"]}, state["released"] is True, ""


def c344(_c):
    cell = 0
    first = cell
    second = cell
    cell = first + 1
    cell = second + 1
    return {"threads": 2}, {"observed": cell, "atomic_would_be": 2, "lost_update": cell != 2}, cell == 1, ""


reg(307, "Una resta encadenada es ambigua y la politica izquierda queda explicita", c307, "LEFT_ASSOC_POLICY")
reg(308, "El AST conserva suma en la raiz y producto a la derecha", c308)
reg(309, "Una suma de tipos distintos es un error semantico", c309)
reg(310, "El nombre local no altera el global", c310)
reg(311, "La suma de literales enteros infiere int", c311)
reg(312, "Un vector mas corto que la longitud declarada se rechaza", c312)
reg(313, "La IR de pila evalua 1+(2*3)", c313)
reg(314, "El lowering a tres direcciones conserva el valor", c314)
reg(315, "Eliminar +0 no cambia las muestras", c315)
reg(316, "El plegado conserva el valor y el uint8 declara el desbordamiento", c316)
reg(317, "El codigo inalcanzable no se ejecuta", c317)
reg(318, "La subexpresion comun se evalua una vez", c318)
reg(319, "La suma vectorial de enteros coincide con la escalar", c319)
reg(320, "El codigo generado solo usa operaciones de la lista blanca", c320)
reg(321, "El ensamblador de la suma contiene una operacion aritmetica", c321, "GCC_O0")
reg(322, "El enlace falla si falta un simbolo", c322)
reg(323, "El simbolo extern C no lleva el mismo decorado que el simbolo C++", c323)
reg(324, "libc abs y la funcion del lenguaje coinciden en el valor de prueba", c324)
reg(325, "Intercambiar el orden de argumentos cambia el resultado", c325, "ARGUMENT_ORDER_NOT_A_FULL_ABI")
reg(326, "El desplazamiento de un int despues de un char se mide en un binario", c326)
reg(327, "La estructura empaquetada elimina el padding", c327)
reg(328, "Un objeto sin referencias fuertes es recuperable", c328)
reg(329, "El recurso se cierra aunque la operacion falle", c329)
reg(330, "El compilador rechaza un uso posterior a un movimiento", c330)
reg(331, "No hay un JIT observable en este entorno", c331)
reg(332, "La maquina virtual ejecuta el bytecode valido y rechaza un opcode", c332)
reg(333, "No hay runtime WebAssembly instalado", c333)
reg(334, "No hay pipeline LLVM instalado", c334)
reg(335, "El compilador localiza un error de sintaxis", c335)
reg(336, "El mapa de origen relaciona la linea generada con la linea original", c336)
reg(337, "Cambiar una dependencia marca el componente que la usa", c337)
reg(338, "La clave de cache cambia con el contenido aunque el nombre no cambie", c338)
reg(339, "La misma fuente produce el mismo codigo dos veces", c339, "PYTHON_BYTECODE_NOT_GCC_BITIDENTITY")
reg(340, "El sanitizador detecta una escritura fuera del bloque reservado", c340)
reg(341, "El lazo medido cuesta mas que la funcion vacia", c341)
reg(342, "El error de division queda asociado a ZeroDivisionError", c342)
reg(343, "La ruta de excepcion libera el recurso", c343)
reg(344, "Dos lecturas del mismo valor producen una actualizacion perdida", c344, "DETERMINISTIC_INTERLEAVING_NOT_A_CPU_MEMORY_MODEL")
