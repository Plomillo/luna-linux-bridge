"""Second implementation. Does not import metagente_luna."""
from __future__ import annotations
import hashlib, sqlite3, struct, unicodedata

def check(observed: dict) -> dict:
    tool = observed.get("tool")
    if tool == "utf8_roundtrip":
        expect = observed["text"].encode("utf-8").hex()
        # manual encoder for code points below U+0800, codecs path is the agent's
        manual = bytearray()
        for ch in observed["text"]:
            cp = ord(ch)
            if cp < 0x80:
                manual.append(cp)
            elif cp < 0x800:
                manual.extend((0xC0 | (cp >> 6), 0x80 | (cp & 0x3F)))
            else:
                manual.extend((0xE0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3F), 0x80 | (cp & 0x3F)))
        return {"ok": observed["utf8_hex"] == bytes(manual).hex() and observed["identical"] is True and observed["replacement_used"] is False}
    if tool == "utf8_strict_decode":
        raw = bytes.fromhex(observed["input_hex"])
        return {"ok": len(raw) == 1 and 0x80 <= raw[0] <= 0xBF and observed["accepted_as_valid_utf8"] is False}
    if tool == "utf16_roundtrip":
        codec = "utf-16-le" if observed["endian"] == "little" else "utf-16-be"
        return {"ok": observed["text"].encode(codec).hex() == observed["utf16_hex"] and observed["identical"] is True}
    if tool == "uint_from_bytes":
        raw = bytes.fromhex(observed["input_hex"])
        fmt = {16: "H", 32: "I", 64: "Q"}[observed["width"]]
        return {"ok": struct.unpack("<"+fmt, raw)[0] == observed["little"] and struct.unpack(">"+fmt, raw)[0] == observed["big"]}
    if tool == "uint16_limits":
        ok = all(row["recovered"] == row["value"] for row in observed["kept"]) and all(row["rejected"] for row in observed["rejected"])
        return {"ok": ok}
    if tool == "int16_roundtrip":
        ok = True
        for row in observed["recovered"]:
            ok = ok and struct.pack("<h", row["value"]).hex() == row["hex"]
        for value in observed["rejected"]:
            try:
                struct.pack("<h", value)
                ok = False
            except struct.error:
                pass
        return {"ok": ok and -32769 in observed["rejected"] and 32768 in observed["rejected"]}
    if tool == "signed_from_hex":
        raw = bytes.fromhex(observed["input_hex"])
        fmt = {16: "h", 32: "i"}[observed["width"]]
        return {"ok": struct.unpack(">"+fmt, raw)[0] == observed["value"]}
    if tool == "float_bits":
        fmt = "<f" if observed["kind"] == "float32" else "<d"
        return {"ok": struct.pack(fmt, observed["value"]).hex() == observed["hex"]}
    if tool == "non_finite" and observed["kind"] == "nan":
        return {"ok": observed["equal_to_self"] is False and observed["classified"] is True}
    if tool == "non_finite" and observed["kind"] == "inf":
        return {"ok": observed["signs_distinct"] is True and observed["positive_hex"] != observed["negative_hex"]}
    if tool == "min_subnormal_f32":
        return {"ok": observed["hex"] == "01000000" and observed["is_subnormal"] is True}
    if tool == "nfc_compare":
        return {"ok": observed["same"] is True and observed["left_hex"] == observed["right_hex"]}
    if tool == "nfd_decompose":
        return {"ok": observed["codepoints"] == ["U+0065", "U+0301"]}
    if tool == "nfkc_note":
        return {"ok": observed["output"] == "fi" and observed["preserved_original"] is False}
    if tool == "sha256_text":
        return {"ok": hashlib.sha256(observed["text"].encode()).hexdigest() == observed["sha256"]}
    if tool == "sum_ints":
        return {"ok": observed["sum"] == sum(observed["values"]) and observed["empty_sum"] == 0}
    if tool == "bounds":
        return {"ok": observed["min"] == min(observed["values"]) and observed["max"] == max(observed["values"])}
    if tool == "sqlite_check_insert":
        conn = sqlite3.connect(":memory:")
        conn.execute(f"CREATE TABLE t({observed['column']} INTEGER CHECK ({observed['predicate']}))")
        rejected = False
        try:
            conn.execute(f"INSERT INTO t({observed['column']}) VALUES (?)", (observed["value"],))
        except sqlite3.IntegrityError:
            rejected = True
        conn.close()
        return {"ok": rejected and observed["rejected"] is True}
    return {"ok": False, "reason": "no oracle"}
