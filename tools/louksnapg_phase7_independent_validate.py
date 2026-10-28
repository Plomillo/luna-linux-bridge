#!/usr/bin/env python3
"""Independent, read-only revalidation of Phase-5 and Phase-6 evidence artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase5", type=Path, required=True)
    parser.add_argument("--phase6", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    errors = []
    try:
        p5 = json.loads(args.phase5.read_text(encoding="utf-8"))
        p6 = json.loads(args.phase6.read_text(encoding="utf-8"))
    except Exception as exc:
        fail("PHASE5_OR_PHASE6_REPORT_UNREADABLE:" + type(exc).__name__)

    if p5.get("schema") != "LOUKSNAPG_PHASE5_TARGETED_RETEST/1.0":
        errors.append("PHASE5_SCHEMA_INVALID")
    if p6.get("schema") != "LOUKSNAPG_PHASE6_INTEGRATION/1.0":
        errors.append("PHASE6_SCHEMA_INVALID")
    if p5.get("candidate_commit") != args.expected_commit or p6.get("candidate_commit") != args.expected_commit:
        errors.append("CANDIDATE_COMMIT_BINDING_MISMATCH")
    if p5.get("status") not in {"PASS_REGISTERED_DOMAIN_RETESTS_WITH_ANCIENT_GAP", "PASS_REGISTERED_DOMAIN_RETESTS"}:
        errors.append("PHASE5_REGISTERED_DOMAIN_RETESTS_NOT_PASS")
    if p5.get("registered_domain_tests_passed") != 4 or p5.get("registered_domain_tests_expected") != 4:
        errors.append("PHASE5_DOMAIN_PASS_COUNT_MISMATCH")
    if p6.get("status") != "PASS_INTEGRATION_CHECKS":
        errors.append("PHASE6_INTEGRATION_CHECKS_NOT_PASS")
    if p5.get("candidate_id") != p6.get("candidate_id"):
        errors.append("CANDIDATE_ID_MISMATCH")
    tree_sha = p5.get("candidate_runtime_tree_sha256")
    if not isinstance(tree_sha, str) or not HEX64.fullmatch(tree_sha) or p6.get("candidate_runtime_tree_sha256") != tree_sha:
        errors.append("CANDIDATE_RUNTIME_TREE_HASH_MISMATCH")

    phase5_tasks = p5.get("registered_domain_results")
    if not isinstance(phase5_tasks, list) or len(phase5_tasks) != 4:
        errors.append("PHASE5_TASK_EVIDENCE_COUNT_MISMATCH")
    else:
        ids = set()
        for row in phase5_tasks:
            if not isinstance(row, dict):
                errors.append("PHASE5_TASK_EVIDENCE_INVALID_ROW")
                continue
            domain = row.get("domain_id")
            ids.add(domain)
            if row.get("passed") is not True:
                errors.append("PHASE5_TASK_FAILED:" + str(domain))
            for key in ("input_sha256", "output_sha256", "weight_sha256", "module_tree_sha256"):
                if not isinstance(row.get(key), str) or not HEX64.fullmatch(row[key]):
                    errors.append("PHASE5_TASK_HASH_INVALID:" + str(domain) + ":" + key)
        if ids != {"D01_CEREBRO", "D03_TRANSCRIPCION", "D04_TRADUCTOR_INTELIGENTE", "D06_SISTEMA_INTELIGENTE"}:
            errors.append("PHASE5_REQUIRED_DOMAIN_SET_MISMATCH")

    phase6 = p6.get("checks")
    if not isinstance(phase6, list) or not phase6:
        errors.append("PHASE6_CHECK_LIST_MISSING")
    else:
        for row in phase6:
            if not isinstance(row, dict) or row.get("status") != "PASS" or not HEX64.fullmatch(str(row.get("log_sha256", ""))):
                errors.append("PHASE6_CHECK_EVIDENCE_INVALID")

    ancient = p5.get("ancient_translation_status", "UNKNOWN")
    release_complete = not errors and ancient == "PASS_NATIVE_KNOWN_ANSWER"
    status = "PASS_SCOPED_EVIDENCE_RECHECK" if not errors else "FAIL_INDEPENDENT_EVIDENCE_RECHECK"
    result = {
        "schema": "LOUKSNAPG_PHASE7_INDEPENDENT_VALIDATION/1.0",
        "candidate_commit": args.expected_commit,
        "candidate_id": p5.get("candidate_id"),
        "candidate_runtime_tree_sha256": tree_sha,
        "phase5_report_sha256": sha256(args.phase5),
        "phase6_report_sha256": sha256(args.phase6),
        "phase5_status_rechecked": p5.get("status"),
        "phase6_status_rechecked": p6.get("status"),
        "ancient_translation_status": ancient,
        "status": status,
        "scope": "INDEPENDENT_RECHECK_OF_FOUR_REGISTERED_DOMAIN_RETESTS_AND_PHASE6_INTEGRATION_EVIDENCE",
        "global_release_ready": release_complete,
        "global_certification": "NOT_GRANTED",
        "blockers": sorted(set(errors + ([] if release_complete else ["ANCIENT_TRANSLATION_NATIVE_TEST_AND_G23_G24_CHAIN_NOT_ESTABLISHED"]))),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    if errors:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
