from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
MISSION = ROOT / "missions/training-alta-resolucion-20261123"
sys.path.insert(0, str(MISSION))

from metagente_luna.m0 import execute as m0_execute
from metagente_luna.parse import Unmatched
from metagente_luna_m1.m0 import execute as m1_execute
from metagente_luna_m1.oracle import check as m1_oracle_check
from oracle.independent_oracle import check as independent_oracle_check

RESULTS = MISSION / "results/M0-20261124.2/CORPUS_RESULTS.jsonl"
M1_DELTA = MISSION / "results/M1-20261125.1/M1_DELTA.json"
M1_RESULTS_DIR = MISSION / "results/M1-20261125.1"
FIXTURES_DIR = MISSION / "fixtures"
M0_ENTRY = MISSION / "metagente_luna/m0.py"


def load_rows() -> list[dict]:
    return [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    rows = load_rows()
    assert len(rows) == 1000, f"expected 1000 baseline rows, got {len(rows)}"
    pass_rows = [r for r in rows if r["VERDICT"] == "PASS"]
    fail_rows = [r for r in rows if r["VERDICT"] == "FAIL"]
    assert len(pass_rows) == 20 and len(fail_rows) == 980

    reproduced_pass = 0
    reproduced_unmatched = 0
    pass_oracle_failures: list[str] = []
    mismatch: list[str] = []

    for row in rows:
        instruction = row["INSTRUCTION"]
        try:
            actual = m0_execute(instruction)
        except Unmatched as exc:
            if row["VERDICT"] != "FAIL" or str(exc) != instruction:
                mismatch.append(row["CASE_ID"])
            else:
                reproduced_unmatched += 1
            continue
        except Exception as exc:
            mismatch.append(f'{row["CASE_ID"]}: {type(exc).__name__}: {exc}')
            continue

        if row["VERDICT"] != "PASS":
            mismatch.append(row["CASE_ID"])
            continue
        expected_wrapper = json.loads(row["OBSERVED"])
        if actual.get("observed") != expected_wrapper.get("observed"):
            mismatch.append(f'{row["CASE_ID"]}: observed output mismatch')
        oracle_result = independent_oracle_check(actual["observed"])
        if oracle_result.get("ok") is not True:
            pass_oracle_failures.append(row["CASE_ID"])
        else:
            reproduced_pass += 1

    assert reproduced_unmatched == 980, f"reproduced UNMATCHED={reproduced_unmatched}"
    assert reproduced_pass == 20, f"reproduced oracle-backed PASS={reproduced_pass}"
    assert not mismatch, f"baseline mismatches: {mismatch[:10]}"
    assert not pass_oracle_failures, f"M0 PASS oracle failures: {pass_oracle_failures}"

    delta = json.loads(M1_DELTA.read_text(encoding="utf-8"))
    m1_ids = delta["m1_additional_pass"]
    assert len(m1_ids) == 19 and delta["m1_additional_count"] == 19
    row_by_id = {r["CASE_ID"]: r for r in rows}

    m1_checks = []
    for case_id in m1_ids:
        instruction = row_by_id[case_id]["INSTRUCTION"]
        output = m1_execute(instruction)
        oracle_agent = m1_oracle_check(output)
        oracle_independent = independent_oracle_check(output["observed"])
        m1_checks.append({
            "case_id": case_id,
            "tool": output["observed"].get("tool"),
            "identity_version": output.get("version"),
            "identity_machinery": "M1",
            "reported_machinery": output.get("machinery"),
            "m1_oracle": oracle_agent,
            "independent_oracle": oracle_independent,
        })

    unsupported_by_both = [
        x["case_id"] for x in m1_checks
        if x["m1_oracle"].get("ok") is not True
        and x["independent_oracle"].get("ok") is not True
    ]
    mislabeled = [x["case_id"] for x in m1_checks if x["reported_machinery"] != "M1"]
    assert len(unsupported_by_both) == 19, f"expected 19 unsupported oracle cases, got {len(unsupported_by_both)}"
    assert len(mislabeled) == 19, f"expected 19 M1 outputs mislabeled as M0, got {len(mislabeled)}"

    fixture_dirs = sorted(p.name for p in FIXTURES_DIR.iterdir() if p.is_dir())
    m1_result_files = sorted(p.name for p in M1_RESULTS_DIR.iterdir() if p.is_file())
    assert len(fixture_dirs) == 6, f"expected six existing fixture directories, got {len(fixture_dirs)}"
    assert m1_result_files == ["M1_DELTA.json"], f"unexpected M1 result evidence files: {m1_result_files}"

    # Reproduce representative M0 CLI behavior in fresh processes.
    sample_ids = ["MGL5-INF-0001", "MGL5-INF-0009", "MGL5-INF-0005", "MGL5-INF-0030", "MGL5-INF-0413", "MGL5-INF-1000"]
    samples = []
    with tempfile.TemporaryDirectory(prefix="m0-forensic-") as temp:
        base = Path(temp)
        for case_id in sample_ids:
            row = row_by_id[case_id]
            for attempt in range(1, 4):
                out = base / case_id / f"{attempt}.json"
                state = base / case_id / f"state-{attempt}"
                proc = subprocess.run(
                    [sys.executable, str(M0_ENTRY), "--instruction", row["INSTRUCTION"],
                     "--state-dir", str(state), "--out", str(out)],
                    cwd=ROOT, capture_output=True, text=True, check=False,
                    env={**os.environ, "PYTHONPATH": str(MISSION) + os.pathsep + os.environ.get("PYTHONPATH", "")},
                )
                payload = json.loads(out.read_text(encoding="utf-8"))
                expected_code = 0 if row["VERDICT"] == "PASS" else 2
                assert proc.returncode == expected_code, (case_id, attempt, proc.returncode, expected_code)
                assert payload["status"] == ("OBSERVED" if expected_code == 0 else "UNMATCHED")
                samples.append({"case_id": case_id, "attempt": attempt, "exit_code": proc.returncode, "status": payload["status"]})

    summary = {
        "baseline_records": len(rows),
        "baseline_recorded": {"PASS": len(pass_rows), "FAIL": len(fail_rows)},
        "full_corpus_reproduction": {"PASS_with_independent_oracle": reproduced_pass, "UNMATCHED": reproduced_unmatched, "mismatches": len(mismatch)},
        "unmatched_invariants": {
            "all_980_failures_reproduced_as_unmatched": True,
            "each_reason_equals_original_instruction": True,
            "baseline_exit_codes_each": [2, 2, 2],
        },
        "m1_claims": {
            "additional_pass_claims": len(m1_ids),
            "oracle_supported_claims": len(m1_ids) - len(unsupported_by_both),
            "unsupported_by_committed_m1_and_shared_oracles": len(unsupported_by_both),
            "outputs_mislabeled_machinery": len(mislabeled),
            "per_case_m1_result_files": m1_result_files,
            "cases": m1_checks,
        },
        "fixture_directories_present": fixture_dirs,
        "fresh_process_samples": samples,
        "verdict": "REPRODUCED_M0_PARSER_COVERAGE_GAP; M1_ADDITIONAL_PASS_CLAIMS_NOT_SUPPORTED_BY_COMMITTED_ORACLES",
    }
    (ROOT / "forensic-reproduction.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
