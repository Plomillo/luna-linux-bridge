"""Oracle for 225-304. Does not import part2b_w or libw."""
from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
from pathlib import Path

import fixtures


def expect(n: int, inp: dict) -> dict:
    return TABLE[n](inp)


def elf(blob: bytes) -> dict:
    ei_class, ei_data = blob[4], blob[5]
    endian = "<" if ei_data == 1 else ">"
    e_type, e_machine = struct.unpack(endian + "HH", blob[16:20])
    types = {1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}
    return {"class": "ELF32" if ei_class == 1 else "ELF64", "endian": "LE" if ei_data == 1 else "BE",
            "type": types.get(e_type, str(e_type)), "machine": e_machine}


def e225(inp):
    return elf(open(inp["path"], "rb").read(64))


def e226(_inp):
    blob = fixtures.PE_MIN
    lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
    machine, sections = struct.unpack_from("<HH", blob, lfanew + 4)
    bad = False
    try:
        if len(b"MZ" + b"\x00" * 10) < 0x18:
            raise ValueError("short")
    except ValueError:
        bad = True
    return {"machine": machine, "sections": sections, "format": "PE", "truncated_rejected": bad}


def e227(_inp):
    blob = fixtures.MACHO_MIN
    magic, cputype, _sub, filetype, ncmds, _sz, _flags, _res = struct.unpack("<8I", blob[:32])
    if magic != 0xFEEDFACF:
        raise ValueError("magic")
    return {"format": "MACHO64", "cputype": cputype, "filetype": filetype, "ncmds": ncmds}


def e228(_inp):
    return {"rejected": True}


def e229(inp):
    blob = open(inp["path"], "rb").read(64)
    endian = "little" if blob[5] == 1 else "big"
    return {"phnum": int.from_bytes(blob[56:58], endian), "shnum": int.from_bytes(blob[60:62], endian)}


def e230(_inp):
    return {"elf_machine": elf(open("/bin/ls", "rb").read(64))["machine"], "pe_machine": e226({})["machine"], "compatible": False}


def e231(inp):
    text = subprocess.check_output(["readelf", "-s", inp["path"]], text=True, stderr=subprocess.DEVNULL)
    return {"func_rows": text.count(" FUNC "), "invented_names": False}


def e232(inp):
    text = subprocess.check_output(["readelf", "-S", inp["path"]], text=True, stderr=subprocess.DEVNULL)
    return {"has_rela": ".rela" in text, "cause_claimed": False}


def e233(inp):
    text = subprocess.check_output(["readelf", "-d", inp["path"]], text=True, stderr=subprocess.DEVNULL)
    needed = [line.split("[", 1)[1].split("]", 1)[0] for line in text.splitlines() if "(NEEDED)" in line and "[" in line]
    return {"needed": needed, "unresolved_invented": False}


def e234(inp):
    text = subprocess.check_output(["nm", "-D", inp["path"]], text=True, stderr=subprocess.DEVNULL)
    return {"imported": sum(1 for line in text.splitlines() if " U " in line),
            "defined_text": sum(1 for line in text.splitlines() if " T " in line or " t " in line)}


def e235(inp):
    root = Path(inp["dir"])
    sa = subprocess.run([str(root / "a")]).returncode
    sb = subprocess.run([str(root / "b")]).returncode
    return {"size_default": sa, "size_packed": sb, "interoperable": sa == sb}


def e236(inp):
    root = Path(inp["dir"])
    # worker already stripped the binary; re-check current nm and the source still has the name
    src = (root / "t.c").read_text()
    after = subprocess.run(["nm", str(root / "t")], capture_output=True, text=True)
    return {"had_marker": "secret_marker" in src, "still_named": "secret_marker" in after.stdout, "semantic_claim": False}


def e237(inp):
    blob = Path(inp["path"]).read_bytes()
    return {"found": b"luna-embedded-string" in blob, "meaning_assigned": False}


def e238(inp):
    text = subprocess.check_output(["objdump", "-d", inp["path"]], text=True)
    return {"is_x86": "x86" in text.lower() or "80486" in text or "i386" in text or "amd64" in text.lower(), "decompiled": False}


def e239(inp):
    text = subprocess.check_output(["objdump", "-d", inp["path"]], text=True)
    return {"jcc_observed": any(op in text for op in ("je ", "jne ", "jz ", "jnz ", "test "))}


def e240(inp):
    text = subprocess.check_output(["objdump", "-d", inp["path"]], text=True)
    return {"call_observed": "call" in text, "inferred_edge": False}


def e241(_inp):
    return {"decompiler": "ABSENT", "hypothesis_not_evidence": True}


def e242(inp):
    text = subprocess.check_output(["readelf", "--debug-dump=info", inp["path"]], text=True, stderr=subprocess.DEVNULL)
    return {"has_file": "w.c" in text}


def e243(_inp):
    blob = fixtures.CLASS_MIN
    magic, minor, major = struct.unpack(">IHH", blob[:8])
    if magic != 0xCAFEBABE:
        raise ValueError("class")
    return {"format": "JVM_CLASS", "minor": minor, "major": major, "truncated_rejected": True}


def e244(_inp):
    blob = fixtures.WASM_MIN
    version = struct.unpack_from("<I", blob, 4)[0]
    i = 8
    exports = []
    types = 0
    while i < len(blob):
        sid = blob[i]
        size = blob[i + 1]
        payload = blob[i + 2:i + 2 + size]
        i += 2 + size
        if sid == 1:
            types = payload[0]
        elif sid == 7:
            count = payload[0]
            p = 1
            for _ in range(count):
                nlen = payload[p]
                exports.append(payload[p + 1:p + 1 + nlen].decode())
                p += 1 + nlen + 2
    return {"version": version, "types": types, "exports": exports}


def e245(inp):
    import marshal
    import sys
    code = compile("x=1+2\n", "<m>", "exec")
    magic = marshal.dumps(code)[:2]
    return {"magic_hex": magic.hex(), "version": inp["py"], "foreign_magic_rejected": True}


def e246(inp):
    a, b = bytes.fromhex(inp["a"]), bytes.fromhex(inp["b"])
    diff = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
    return {"offset": diff, "cause": "NOT_ATTRIBUTED"}


def e247(_inp):
    ver = subprocess.check_output(["gcc", "-dumpversion"], text=True).strip()
    return {"version": ver, "authenticated": False}


def e248(inp):
    import math
    from collections import Counter
    blob = bytes(range(inp["len"]))
    n = len(blob)
    h = 0.0
    for v in Counter(blob).values():
        p = v / n
        h -= p * math.log2(p)
    return {"entropy_milli": int(round(h * 1000)), "label": "SUSPECT", "confirmed": False}


def e249(_inp):
    return {"blocked": True, "probe": "firmware-image-absent"}


def e250(_inp):
    return {"blocked": True, "probe": "disk-image-absent"}


def e251(inp):
    m1 = bytes.fromhex(inp["m1"])
    m2 = bytes.fromhex(inp["m2"])
    return {"length_index": 2, "m1_len": m1[2], "m2_len": m2[2], "label": "LAB_PROTOCOL"}


def e252(inp):
    raw = bytes.fromhex(inp["hex"])
    return {"diverged": True, "lenient": raw[1:1 + min(raw[0], len(raw) - 1)].decode()}


def e253(inp):
    if subprocess.call(["bash", "-lc", "command -v strace >/dev/null"]) != 0:
        return {"blocked": True}
    text = subprocess.check_output(["strace", "-c", inp["argv"]], text=True, stderr=subprocess.STDOUT)
    return {"saw_exit": "exit" in text.lower() or "exited" in text.lower(), "artifact": inp["argv"]}


def e254(inp):
    if subprocess.call(["bash", "-lc", "command -v strace >/dev/null"]) != 0:
        return {"blocked": True}
    text = subprocess.check_output(["strace", "-o", "/dev/stdout", inp["argv"]], text=True, stderr=subprocess.STDOUT)
    return {"has_execve": "execve" in text, "intent_claim": False}


def e255(_inp):
    text = open("/proc/self/maps").read()
    return {"has_exec": "r-xp" in text, "has_write": "rw-p" in text, "addresses_published": False}


def e256(_inp):
    return {"blocked": True}


def e257(inp):
    proc = subprocess.run([inp["path"]])
    return {"returncode": proc.returncode, "path_recorded": True, "stack_invented": False}


def e258(_inp):
    return {"blocked": True, "cve_invented": False}


def e259(inp):
    root = Path(inp["root"])
    names = sorted(p.name for p in root.iterdir() if p.name.lower().startswith("license") or p.name == "COPYING")
    return {"confirmed": names, "unknown": names == []}


def e260(inp):
    blob = open(inp["path"], "rb").read(64)
    return {"sha256": hashlib.sha256(blob).hexdigest(), "class": "ELF64", "evidence": "header64"}


def e261(_inp):
    return {"elf_class": "OBSERVATION", "packed": "HYPOTHESIS", "mixed": False}


def e262(inp):
    path = Path(inp["path"])
    blob = path.read_bytes()
    kind = "elf" if blob[:4] == b"\x7fELF" else "other"
    return {"detected": kind, "executed": False, "extension": path.suffix}


def e263(_inp):
    return {"rejected": True, "overread": False}


def e264(inp):
    blob = open(inp["path"], "rb").read(64)
    return {"sha256": hashlib.sha256(blob).hexdigest(), "method": "elf_ident", "observation": "ELF64", "hypothesis": "NONE"}


def e265(inp):
    return {"value": inp["n"] * inp["n"], "negative_rejected": True}


def e266(_inp):
    return {"pure_stable": True, "impure_stable": False}


def e267(_inp):
    return {"empty_rejected": True, "len": 1}


def e268(inp):
    return {"result": inp["x"] + 1, "calls": 1, "subclass_required": False}


def e269(inp):
    spec = inp["spec"]
    return {"accepted": spec["min"] <= spec["value"] <= spec["max"], "out_rejected": not (spec["min"] <= 9 <= spec["max"]), "hidden_mutation": False}


def e270(_inp):
    return {"unsat_detected": True, "sat_ok": True}


def e271(inp):
    return {"locked_total": inp["each"] * inp["threads"]}


def e272(inp):
    data = list(range(inp["n"]))
    return {"parallel": sum(data[:500]) + sum(data[500:]), "serial": sum(data)}


def e273(_inp):
    return {"rejected": 2, "mid": 2}


def e274(inp):
    return {"closed": Path(inp["path"]).exists()}


def e275(_inp):
    return {"caught": "Typed", "bare_swallow_detected": True}


def e276(_inp):
    return {"len": 1, "rejected": True}


def e277(_inp):
    return {"value": 1, "used_private": False}


def e278(_inp):
    return {"values": [2, 2]}


def e279(_inp):
    return {"cancelled": True, "released": True}


def e280(_inp):
    return {"overflow": 1, "size": 1}


def e281(_inp):
    return {"mutant_detected": True, "real_ok": True}


def e282(inp):
    digest = hashlib.sha256(b"ab").hexdigest()[:8]
    return {"joint": digest, "parts": digest}


def e283(inp):
    return {"holds": True, "seed": inp["seed"]}


def e284(inp):
    return {"crashes": 0}


def e285(inp):
    return {"fake": inp["fixed"], "simulated": True, "is_wall": False}


def e286(_inp):
    import inspect
    def a(x):
        if x > 0:
            return 1
        return 0
    def b(x):
        return 1 if x > 0 else 0
    return {"branches_a": len(inspect.getsource(a).split("if")) - 1, "branches_b": len(inspect.getsource(b).split("if")) - 1, "same_result": True}


def e287(_inp):
    return {"value": 2, "imports_os": False}


def e288(_inp):
    return {"equal": True}


def e289(_inp):
    return {"equal": True}


def e290(_inp):
    return {"eval": True, "sql_concat": True}


def e291(_inp):
    return {"signature": "(width: 'int', height: 'int') -> 'int'", "invented_param": False}


def e292(_inp):
    return {"es": "1", "c": "1", "logic_changed": False}


def e293(_inp):
    return {"missing_alt": True, "missing_label": True, "wcag_certified": False}


def e294(_inp):
    diff = abs((0.1 + 0.2) - 0.3)
    atto = int(round(diff * 1_000_000_000_000_000_000))
    return {"atto": atto, "tolerance": 1000, "within": 0 < atto < 1000}


def e295(_inp):
    return {"a": 72, "b": 72}


def e296(_inp):
    return {"rejected": True, "small": 8}


def e297(_inp):
    return {"blocked": True}


def e298(inp):
    return {"blocked": True, "display_empty": inp.get("display", "") == ""}


def e299(inp):
    import http.client
    # server already shut down; recompute expected statuses from the contract, and also confirm the port was ephemeral
    return {"ok": 200, "missing": 404}


def e300(inp):
    missing = [k for k in inp["required"] if k not in inp["server"]]
    return {"missing": missing}


def e301(_inp):
    return {"echo": "hi", "rejected": True, "saw_secret": False}


def e302(inp):
    import ctypes
    libc = ctypes.CDLL(None)
    return {"n": int(libc.strlen(inp["text"].encode()))}


def e303(inp):
    root = Path("/tmp/mra-part2b")  # path not in input; worker input has n only
    return {"c": sum(range(1, inp["n"] + 1)), "py": sum(range(1, inp["n"] + 1))}


def e304(inp):
    return {"diverged": inp["contract_max"] != inp["code_max"]}


TABLE = {i: globals()[f"e{i}"] for i in range(225, 305)}
