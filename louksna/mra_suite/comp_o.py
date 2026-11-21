"""Oracle for compiler cases 305-344. Does not import worker modules."""
from __future__ import annotations

import hashlib
import marshal
import re
import shutil
import subprocess
from pathlib import Path


def expect(n: int, inp: dict) -> dict:
    return TABLE[n](inp)


def e305(inp):
    tokens = []
    bad = False
    for tok in re.findall(r"[A-Za-z]+|\d+|.", inp["src"]):
        if tok == "@":
            bad = True
            break
        tokens.append(tok)
    return {"tokens": tokens, "bad_at": bad}


def e306(inp):
    def ev(src: str) -> int:
        if not src or src[-1] in "+*":
            raise SyntaxError("trunc")
        total = 0
        for part in src.split("+"):
            value = 1
            for piece in part.split("*"):
                if not piece.isdigit():
                    raise SyntaxError("num")
                value *= int(piece)
            total += value
        return total
    rejected = False
    try:
        ev(inp["bad"])
    except SyntaxError:
        rejected = True
    return {"value": ev(inp["ok"]), "rejected": rejected}


def e307(inp):
    nums = [int(x) for x in inp["src"].split("-")]
    left = nums[0] - nums[1] - nums[2]
    right = nums[0] - (nums[1] - nums[2])
    return {"left": left, "right": right, "ambiguous": left != right, "chosen": left}


def e308(inp):
    left, right = inp["src"].split("+", 1)
    return {"root": "Add", "right": "Mult" if "*" in right else "Num"}


def e309(inp):
    return {"type_rejected": inp["bad"][0] != inp["bad"][1], "same_ok": inp["ok"][0] == inp["ok"][1]}


def e310(inp):
    local = 2
    return {"local": local, "global_unchanged": inp["global"]}


def e311(_inp):
    return {"inferred": "int"}


def e312(inp):
    return {"rejected": len(inp["data"]) != inp["claimed"], "actual": len(inp["data"])}


def e313(_inp):
    stack = []
    program = [1, 2, 3, "MUL", "ADD"]
    for op in program:
        if isinstance(op, int):
            stack.append(op)
        elif op == "MUL":
            stack.append(stack.pop() * stack.pop())
        else:
            stack.append(stack.pop() + stack.pop())
    return {"value": stack[0], "depth": len(stack)}


def e314(_inp):
    t0 = 6
    return {"t0": t0, "t1": 1 + t0}


def e315(inp):
    return {"same": all((x + 0) == x for x in inp["samples"])}


def e316(_inp):
    folded = 10
    wrapped = (200 + 100) % 256
    return {"folded": folded, "wrapped": wrapped, "overflow": wrapped != 300}


def e317(_inp):
    return {"effects": 0}


def e318(_inp):
    return {"calls": 1, "value": 2 + 3}


def e319(inp):
    scalar = sum(inp["data"])
    vector = sum(inp["data"][0:2]) + sum(inp["data"][2:4])
    return {"scalar": scalar, "vector": vector, "delta": scalar - vector}


def e320(_inp):
    return {"value": 1 + (2 * 3)}


def e321(inp):
    out = Path(inp["src"]).with_suffix(".oracle.s")
    proc = subprocess.run(["gcc", "-S", "-O0", inp["src"], "-o", str(out)], capture_output=True, text=True)
    text = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
    return {"compiled": proc.returncode == 0, "arith": ("add" in text or "lea" in text)}


def e322(inp):
    out = str(Path(inp["src"]).with_suffix(".bin"))
    proc = subprocess.run(["gcc", "-o", out, inp["src"]], capture_output=True, text=True)
    return {"exit_nonzero": proc.returncode != 0}


def e323(inp):
    out = str(Path(inp["src"]).with_suffix(".oracle.o"))
    proc = subprocess.run(["g++", "-c", "-o", out, inp["src"]], capture_output=True, text=True)
    nm = subprocess.run(["nm", out], capture_output=True, text=True)
    return {"compiled": proc.returncode == 0, "plain": "addc" in nm.stdout, "mangled": "_Z3addii" in nm.stdout}


def e324(inp):
    src = Path("/tmp/mra-oracle-abs.c")
    src.write_text('#include <stdlib.h>\n#include <stdio.h>\nint main(void){ printf("%%d\\n", abs(%d)); return 0; }\n' % int(inp["n"]))
    bin_path = Path("/tmp/mra-oracle-abs")
    subprocess.run(["gcc", "-o", str(bin_path), str(src)], check=True, capture_output=True)
    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, check=True)
    return {"libc": int(proc.stdout.strip()), "py": abs(int(inp["n"]))}


def e325(inp):
    native = inp["a"] - inp["b"]
    swapped = inp["b"] - inp["a"]
    return {"native": native, "swapped": swapped, "mismatch": native != swapped}


def e326(inp):
    class S:
        a = 1
        b_align = 4
    off = (S.a + S.b_align - 1) & ~(S.b_align - 1)
    size = off + 4
    src = Path(inp["src"]).read_text()
    if "struct S" not in src:
        off, size = -1, -1
    return {"offset": off, "size": size}


def e327(_inp):
    import ctypes
    class Raw(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("a", ctypes.c_byte), ("b", ctypes.c_int32)]
    return {"offset": Raw.b.offset, "size": ctypes.sizeof(Raw)}


def e328(_inp):
    import gc
    import weakref
    slot = []
    class Item:
        pass
    item = Item()
    slot.append(weakref.ref(item))
    del item
    gc.collect()
    return {"collected": slot[0]() is None}


def e329(inp):
    path = Path(inp["path"])
    released = {"closed": False}
    class Guard:
        def __enter__(self):
            self.handle = path.open("a")
            return self
        def __exit__(self, *_a):
            self.handle.close()
            released["closed"] = self.handle.closed
            return False
    try:
        with Guard():
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    return {"closed": released["closed"], "exists": path.exists()}


def e330(inp):
    out = str(Path(inp["src"]).with_suffix(".oracle.bin"))
    proc = subprocess.run(["rustc", "--edition", "2021", "-o", out, inp["src"]], capture_output=True, text=True)
    return {"exit_nonzero": proc.returncode != 0}


def e331(inp):
    if shutil.which("pypy3") or shutil.which("llvm-as"):
        return {"blocked": False, "probe": inp["probe"]}
    return {"blocked": True, "probe": inp["probe"]}


def e332(_inp):
    acc = 10 + 32
    rejected = True
    try:
        {"PUSH": 0, "ADD": 0, "HALT": 0}["NOPE"]
    except KeyError:
        rejected = True
    return {"value": acc, "rejected": rejected}


def e333(inp):
    if shutil.which("wasmtime") or shutil.which("wasmer"):
        return {"blocked": False, "probe": inp["probe"]}
    return {"blocked": True, "probe": inp["probe"]}


def e334(inp):
    if shutil.which("llvm-as") and shutil.which("opt"):
        return {"blocked": False, "probe": inp["probe"]}
    return {"blocked": True, "probe": inp["probe"]}


def e335(inp):
    out = str(Path(inp["src"]).with_suffix(".oracle.o"))
    proc = subprocess.run(["gcc", "-c", "-o", out, inp["src"]], capture_output=True, text=True)
    return {"diagnosed": proc.returncode != 0 and "error" in proc.stderr.lower()}


def e336(inp):
    header = inp["header"]
    pairs = [[index + header + 1, index + 1] for index, _line in enumerate(inp["lines"])]
    return {"pairs": pairs}


def e337(inp):
    changed = set(inp["changed"])
    graph = {"app": ["a", "b"]}
    rebuild = sorted(name for name, deps in graph.items() if changed.intersection(deps))
    rebuild.extend(sorted(changed))
    return {"rebuild": rebuild}


def e338(inp):
    return {
        "name_key_same": hashlib.sha256(inp["name"].encode()).hexdigest() == hashlib.sha256(inp["name"].encode()).hexdigest(),
        "content_key_changed": hashlib.sha256(inp["before"].encode()).hexdigest() != hashlib.sha256(inp["after"].encode()).hexdigest(),
    }


def e339(inp):
    first = hashlib.sha256(marshal.dumps(compile(inp["src"], "b.py", "exec"))).hexdigest()
    second = hashlib.sha256(marshal.dumps(compile(inp["src"], "b.py", "exec"))).hexdigest()
    return {"equal": first == second}


def e340(inp):
    if inp.get("probe") == "asan":
        return {"blocked": True, "probe": "asan"}
    out = str(Path(inp["src"]).with_suffix(".oracle.bin"))
    built = subprocess.run(["gcc", "-fsanitize=address", "-o", out, inp["src"]], capture_output=True, text=True)
    if built.returncode != 0:
        return {"blocked": True, "probe": "asan"}
    run = subprocess.run([out], capture_output=True, text=True)
    return {"sanitizer_nonzero": run.returncode != 0}


def e341(inp):
    import time
    def elapsed(body):
        start = time.perf_counter_ns()
        body()
        return time.perf_counter_ns() - start
    def hot():
        total = 0
        for i in range(inp["loops"]):
            total += i * 1
        return total
    def cold():
        return 0 + 1
    return {"hot_slower": elapsed(hot) > elapsed(cold)}


def e342(_inp):
    kind = ""
    try:
        _ = pow(1, 1) // 0
    except ZeroDivisionError as exc:
        kind = exc.__class__.__name__
    return {"kind": kind}


def e343(_inp):
    released = False
    try:
        try:
            raise RuntimeError("y")
        finally:
            released = True
    except RuntimeError:
        released = released and True
    return {"released": released}


def e344(_inp):
    snapshot = [0, 0]
    snapshot[0] = snapshot[1] + 1
    observed = snapshot[1] + 1
    return {"observed": observed, "atomic_would_be": 2, "lost_update": observed != 2}


TABLE = {i: globals()[f"e{i}"] for i in list(range(305, 345))}
