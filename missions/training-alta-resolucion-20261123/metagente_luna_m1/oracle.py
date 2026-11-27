"""Independent recomputation. Does not import the agent."""
from __future__ import annotations

import hashlib
import json
import struct


def utf8_bytes(text: str) -> str:
    out = bytearray()
    for ch in text:
        cp = ord(ch)
        if cp < 0x80:
            out.append(cp)
        elif cp < 0x800:
            out.extend((0xC0 | (cp >> 6), 0x80 | (cp & 0x3F)))
        else:
            out.extend((0xE0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F)))
    return bytes(out).hex()


def check(agent_result: dict) -> dict:
    observed = agent_result.get("observed") or {}
    tool = observed.get("tool")
    if tool == "utf8_roundtrip":
        expect = utf8_bytes(observed["text"])
        ok = observed["utf8_hex"] == expect and observed["identical"] is True
        return {"oracle": "manual-utf8", "ok": ok, "expect_hex": expect}
    if tool == "utf8_strict_decode":
        raw = bytes.fromhex(observed["input_hex"])
        structural_reject = len(raw) == 1 and 0x80 <= raw[0] <= 0xBF
        return {
            "oracle": "utf8-lead-byte-range",
            "ok": structural_reject and observed["accepted_as_valid_utf8"] is False,
        }
    if tool == "sum_ints":
        return {"oracle": "builtin-sum", "ok": observed["sum"] == sum(observed["values"]) and observed["empty_sum"] == 0}
    if tool == "bounds":
        return {"oracle": "builtin-minmax", "ok": observed["min"] == min(observed["values"]) and observed["max"] == max(observed["values"])}
    if tool == "sha256_text":
        expect = hashlib.sha256(observed["text"].encode("utf-8")).hexdigest()
        return {"oracle": "hashlib-sha256", "ok": observed["sha256"] == expect}
    if tool == "int16_roundtrip":
        ok = True
        for row in observed["recovered"]:
            packed = struct.pack("<h", row["value"])
            ok = ok and packed.hex() == row["hex"] and struct.unpack("<h", packed)[0] == row["recovered"]
        for value in observed["rejected"]:
            try:
                struct.pack("<h", value)
                ok = False
            except struct.error:
                ok = True and ok
        return {"oracle": "struct-int16", "ok": ok}
    if tool == "utf16_roundtrip":
        codec = "utf-16-le" if observed["endian"] == "little" else "utf-16-be"
        raw = observed["text"].encode(codec)
        return {"oracle": "codecs-utf16", "ok": raw.hex() == observed["utf16_hex"] and observed["identical"] is True}
    return {"oracle": "none", "ok": False, "reason": "no independent check for this observation"}


if __name__ == "__main__":
    import sys
    print(json.dumps(check(json.loads(sys.stdin.read())), sort_keys=True))
