#!/usr/bin/env python3
"""Training-lab preflight. Does not execute or pass any MGL5 case."""
import hashlib, json, platform, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROG = ROOT / "PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt"
PINNED = "f67c32d8984be78e73ba1acac050349baef9c1fb6adeb59fef15e53821b88daf"

def main():
    started = time.perf_counter()
    raw = PROG.read_bytes()
    hashes = [hashlib.sha256(raw).hexdigest() for _ in range(3)]
    text = raw.decode("utf-8")
    inf = re.findall(r"\[MGL5-INF-(\d{4})\]", text)
    teo = re.findall(r"\[MGL5-TEO-(\d{4})\]", text)
    inf_n = [int(x) for x in inf]
    teo_n = [int(x) for x in teo]
    checks = {
        "program_present": PROG.is_file(),
        "sha256_matches_pin": hashes[0] == PINNED,
        "hash_repeated_3": len(set(hashes)) == 1,
        "inf_1000_contiguous": inf_n == list(range(1, 1001)),
        "teo_50_contiguous": teo_n == list(range(1, 51)),
        "declared_not_run_1000": text.count("ESTADO=NOT_RUN") == 1000,
    }
    ok = all(checks.values())
    report = {
        "id": "C04-PREFLIGHT",
        "state": "PASS" if ok else "FAIL",
        "does_not_execute_cases": True,
        "does_not_accredit_agent": True,
        "pinned_sha256": PINNED,
        "observed_sha256": hashes[0],
        "checks": checks,
        "python": sys.version,
        "platform": platform.platform(),
        "duration_s": round(time.perf_counter() - started, 6),
        "limitations": [
            "This host is not Debian 13 KDE Wayland.",
            "The Piper es_ES-sharvard-medium model blob is not in the git tree.",
            "No physical microphone or speaker is claimed.",
            "Case execution has not started.",
        ],
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
