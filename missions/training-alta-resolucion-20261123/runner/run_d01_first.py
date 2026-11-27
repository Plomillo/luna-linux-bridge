#!/usr/bin/env python3
"""Execute a bounded, explicit subset of D01 cases. Unimplemented IDs stay NOT_RUN."""
import hashlib, json, math, platform, struct, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "missions" / "training-alta-resolucion-20261123" / "case-results"
PIN = "f67c32d8984be78e73ba1acac050349baef9c1fb6adeb59fef15e53821b88daf"

def oracle_utf8(text):
    # Independent of codecs.encode: manual UTF-8.
    out = bytearray()
    for ch in text:
        cp = ord(ch)
        if cp < 0x80:
            out.append(cp)
        elif cp < 0x800:
            out.append(0xC0 | (cp >> 6))
            out.append(0x80 | (cp & 0x3F))
        elif cp < 0x10000:
            out.append(0xE0 | (cp >> 12))
            out.append(0x80 | ((cp >> 6) & 0x3F))
            out.append(0x80 | (cp & 0x3F))
        else:
            out.append(0xF0 | (cp >> 18))
            out.append(0x80 | ((cp >> 12) & 0x3F))
            out.append(0x80 | ((cp >> 6) & 0x3F))
            out.append(0x80 | (cp & 0x3F))
    return bytes(out)

def run_case(case_id, fn):
    reps = []
    t0 = time.perf_counter()
    for i in range(3):
        reps.append(fn())
    same = all(r == reps[0] for r in reps)
    observed = reps[0]
    state = observed["state"] if same else "FAIL"
    if not same:
        observed = {"state": "FAIL", "reason": "repetitions diverged", "reps": reps}
    return {
        "id": case_id,
        "state": state,
        "repetitions": 3,
        "repetitions_identical": same,
        "duration_s": round(time.perf_counter() - t0, 6),
        "observed": observed,
        "program_original_state": "NOT_RUN",
        "python": platform.python_version(),
        "platform": platform.platform(),
    }

def c0001():
    text = "Luna-2026"
    produced = text.encode("utf-8")
    oracle = oracle_utf8(text)
    decoded = produced.decode("utf-8")
    negative = bytes([0x80])
    silent = True
    try:
        negative.decode("utf-8")
        silent = True
    except UnicodeDecodeError:
        silent = False
    ok = decoded == text and produced == oracle and produced == bytes([0x4C,0x75,0x6E,0x61,0x2D,0x32,0x30,0x32,0x36]) and not silent
    return {"state": "PASS" if ok else "FAIL", "decoded": decoded, "produced_hex": produced.hex(), "oracle_hex": oracle.hex(), "negative_silently_accepted": silent}

def c0002():
    text = "computación, información, ñandú"
    produced = text.encode("utf-8")
    oracle = oracle_utf8(text)
    decoded = produced.decode("utf-8")
    ok = decoded == text and produced == oracle and "\ufffd" not in decoded
    return {"state": "PASS" if ok else "FAIL", "decoded": decoded, "produced_hex": produced.hex()}

def c0003():
    policy = "REJECT_STRICT"
    data = bytes([0x80])
    anomaly = None
    accepted = False
    try:
        data.decode("utf-8")
        accepted = True
    except UnicodeDecodeError as exc:
        anomaly = str(exc)
    # Independent oracle: a lone continuation byte is not a valid UTF-8 scalar.
    oracle_invalid = data[0] & 0xC0 == 0x80 and len(data) == 1
    ok = policy == "REJECT_STRICT" and not accepted and anomaly is not None and oracle_invalid
    return {"state": "PASS" if ok else "FAIL", "policy": policy, "accepted_as_utf8": accepted, "anomaly": anomaly}

def c0004():
    text = "LUNA"
    produced = text.encode("utf-16-le")
    oracle = bytes([0x4C,0x00,0x55,0x00,0x4E,0x00,0x41,0x00])
    decoded = produced.decode("utf-16-le")
    ok = produced == oracle and decoded == text
    return {"state": "PASS" if ok else "FAIL", "produced_hex": produced.hex(), "oracle_hex": oracle.hex(), "decoded": decoded}

def c0005():
    text = "LUNA"
    produced = text.encode("utf-16-be")
    oracle = bytes([0x00,0x4C,0x00,0x55,0x00,0x4E,0x00,0x41])
    decoded = produced.decode("utf-16-be")
    endian_detected = produced[0] == 0x00 and produced[1] == 0x4C
    ok = produced == oracle and decoded == text and endian_detected
    return {"state": "PASS" if ok else "FAIL", "produced_hex": produced.hex(), "endian_detected": "BE" if endian_detected else "NOT_BE", "decoded": decoded}

def c0006():
    policy = "STRIP_UTF8_BOM_DO_NOT_KEEP_UFEFF_IN_VISIBLE_TEXT"
    visible = "Luna"
    body = visible.encode("utf-8")
    with_bom = b"\xef\xbb\xbf" + body
    without = body
    def apply(blob):
        if blob.startswith(b"\xef\xbb\xbf"):
            blob = blob[3:]
        text = blob.decode("utf-8")
        return text
    a, b = apply(with_bom), apply(without)
    ok = a == visible and b == visible and "\ufeff" not in a and "\ufeff" not in b
    return {"state": "PASS" if ok else "FAIL", "policy": policy, "with_bom": a, "without_bom": b}

def c0007():
    raw = bytes([0x01,0x02,0x03,0x04])
    le = int.from_bytes(raw, "little")
    be = int.from_bytes(raw, "big")
    oracle_le, oracle_be = 0x04030201, 0x01020304
    ok = le == oracle_le and be == oracle_be
    return {"state": "PASS" if ok else "FAIL", "le": hex(le), "be": hex(be)}

def c0008():
    def enc(n):
        return n.to_bytes(2, "little")
    a, b = enc(0), enc(65535)
    oracle_a, oracle_b = b"\x00\x00", b"\xff\xff"
    rejected = False
    try:
        enc(65536)
    except OverflowError:
        rejected = True
    dec_a = int.from_bytes(a, "little")
    dec_b = int.from_bytes(b, "little")
    ok = a == oracle_a and b == oracle_b and dec_a == 0 and dec_b == 65535 and rejected
    return {"state": "PASS" if ok else "FAIL", "a": a.hex(), "b": b.hex(), "overflow_rejected": rejected}

def c0009():
    return {"state": "BLOCKED", "reason": "FIXTURE_CONTRADICTION", "detail": "Operation names -32768 and -1. Literal list is 32768, 1, 0, 32767. Criterion was not modified."}

def c0010():
    raw = bytes([0xFF, 0xFF])
    value = int.from_bytes(raw, "little", signed=True)
    width = 16
    oracle = -1
    ok = value == oracle and width == 16
    return {"state": "PASS" if ok else "FAIL", "value": value, "width_bits": width}

def c0011():
    produced = struct.pack("<f", 1.5)
    oracle = (0x3FC00000).to_bytes(4, "little")
    ok = produced == oracle and int.from_bytes(produced, "little") == 0x3FC00000
    return {"state": "PASS" if ok else "FAIL", "produced_hex": produced.hex(), "oracle_hex": oracle.hex()}

def c0012():
    produced = struct.pack("<d", 1.5)
    oracle = (0x3FF8000000000000).to_bytes(8, "little")
    ok = produced == oracle
    return {"state": "PASS" if ok else "FAIL", "produced_hex": produced.hex(), "oracle_hex": oracle.hex()}

def c0013():
    nan = float("nan")
    payload = 0x7FF8000000000001
    nan2 = struct.unpack("<d", payload.to_bytes(8, "little"))[0]
    eq = (nan == nan) or (nan2 == nan2)
    ordinary = nan == 0 or nan == 1
    ok = (not eq) and (not ordinary) and math.isnan(nan) and math.isnan(nan2)
    return {"state": "PASS" if ok else "FAIL", "nan_equals_nan": eq, "confused_with_ordinary": ordinary}

def c0014():
    pos, neg = float("inf"), float("-inf")
    packed = struct.pack("<dd", pos, neg)
    signs = (math.copysign(1.0, pos) > 0, math.copysign(1.0, neg) < 0)
    strict_json = None
    try:
        json.dumps([pos, neg], allow_nan=False)
        strict_json = "accepted"
    except ValueError:
        strict_json = "rejected_by_strict_json"
    ok = signs == (True, True) and strict_json == "rejected_by_strict_json" and packed.hex() == "000000000000f07f000000000000f0ff"
    return {"state": "PASS" if ok else "FAIL", "signs_preserved": signs, "strict_json": strict_json, "packed_hex": packed.hex()}

def c0015():
    raw = (1).to_bytes(4, "little")  # smallest positive float32 subnormal
    value = struct.unpack("<f", raw)[0]
    bits = int.from_bytes(struct.pack("<f", value), "little")
    exponent = (bits >> 23) & 0xFF
    mantissa = bits & 0x7FFFFF
    is_subnormal = exponent == 0 and mantissa != 0
    as_f64 = struct.pack("<d", float(value))
    # float64 can represent this value exactly; document that no precision was lost.
    back = struct.unpack("<f", struct.pack("<f", struct.unpack("<d", as_f64)[0]))[0]
    lossless = struct.pack("<f", back) == raw
    ok = is_subnormal and value > 0 and lossless
    return {"state": "PASS" if ok else "FAIL", "is_subnormal": is_subnormal, "lossless_via_float64": lossless, "bits": hex(bits)}

def c0016():
    return {"state": "BLOCKED", "reason": "FIXTURE_LITERALS_TRUNCATED", "detail": "Operation names U+0301 and U+00E9. Literal list records 0301 and 00. Criterion was not modified."}

CASES = [
    ("MGL5-INF-0001", c0001), ("MGL5-INF-0002", c0002), ("MGL5-INF-0003", c0003),
    ("MGL5-INF-0004", c0004), ("MGL5-INF-0005", c0005), ("MGL5-INF-0006", c0006),
    ("MGL5-INF-0007", c0007), ("MGL5-INF-0008", c0008), ("MGL5-INF-0009", c0009),
    ("MGL5-INF-0010", c0010), ("MGL5-INF-0011", c0011), ("MGL5-INF-0012", c0012),
    ("MGL5-INF-0013", c0013), ("MGL5-INF-0014", c0014), ("MGL5-INF-0015", c0015),
    ("MGL5-INF-0016", c0016),
]

def main():
    prog = (ROOT / "PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt").read_bytes()
    if hashlib.sha256(prog).hexdigest() != PIN:
        raise SystemExit("program hash mismatch")
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    for cid, fn in CASES:
        if cid in {"MGL5-INF-0009", "MGL5-INF-0016"}:
            observed = fn()
            rec = {"id": cid, "state": observed["state"], "repetitions": 0, "observed": observed, "program_original_state": "NOT_RUN", "note": "Not executed. Fixture contradiction preserved."}
        else:
            rec = run_case(cid, fn)
        rec["program_sha256"] = PIN
        (OUT / f"{cid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary.append({"id": cid, "state": rec["state"]})
    counts = {}
    for row in summary:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    counts["NOT_RUN"] = 1000 - len(summary)
    report = {"executed_ids": len(summary), "counts_including_not_run": counts, "rows": summary, "c05_condition": "IN_PROGRESS", "c05_not_pass_because": "984 cases remain NOT_RUN and blocked cases are not PASS."}
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
