#!/usr/bin/env python3
"""Reviewed, task-scoped D04 evidence executor.

Executes only six concrete behaviors already implemented in D04_runtime.py.
It never closes a domain, mutates the capability registry, or certifies work.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "implementation/super1200/domains/D04_runtime.py"
TEST = ROOT / "implementation/super1200/tests/test_d04_runtime.py"
OUT = Path(os.environ.get("SUPER1200_EVIDENCE_DIR", ROOT / "continuity/runtime-evidence/D04"))
TASKS = [
    (81, "UNIVERSAL_OBJECT_IDENTITY", "test_universal_object_id_is_stable_scoped_and_does_not_embed_value"),
    (82, "CONTENT_ADDRESSABILITY", "test_content_address_is_deterministic_and_key_order_independent"),
    (83, "PROVENANCE_GRAPH", "test_graph_accepts_known_parent_and_exports_stable_hash"),
    (84, "W3C_PROV_ADAPTER", "test_w3c_prov_adapter_preserves_generation_and_usage_edges"),
    (85, "IN_TOTO_ADAPTER", "test_intoto_statement_has_required_identity_and_rejects_bad_digest"),
    (86, "SLSA_PROVENANCE_ADAPTER", "test_slsa_provenance_binds_source_builder_and_invocation"),
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    if not MODULE.is_file() or not TEST.is_file():
        print("D04_EXECUTOR_DENIED_REQUIRED_SOURCE_OR_TEST_MISSING", file=sys.stderr)
        return 78
    OUT.mkdir(parents=True, exist_ok=True)
    source_hash, test_hash = sha(MODULE), sha(TEST)
    failures = 0
    for capability_id, name, test_name in TASKS:
        started = datetime.now(timezone.utc).isoformat()
        cmd = [sys.executable, "-B", str(TEST), f"D04RuntimeTests.{test_name}"]
        run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=60)
        finished = datetime.now(timezone.utc).isoformat()
        status = "PASS" if run.returncode == 0 else "FAIL"
        if status != "PASS":
            failures += 1
        record = {
            "schema": "SUPER1200_D04_TASK_EVIDENCE/1",
            "capability_id": capability_id,
            "canonical_name": name,
            "executor": "implementation/super1200/runtime/d04_material_executor.py",
            "task_test": test_name,
            "status": status,
            "started_at_utc": started,
            "finished_at_utc": finished,
            "source_sha256": source_hash,
            "test_file_sha256": test_hash,
            "command": cmd,
            "exit_code": run.returncode,
            "stdout_sha256": hashlib.sha256(run.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(run.stderr.encode()).hexdigest(),
            "stdout": run.stdout[-12000:],
            "stderr": run.stderr[-12000:],
            "registry_mutated": False,
            "domain_closed": False,
            "g23": "NOT_RUN",
            "g24": "NOT_RUN",
        }
        record["evidence_sha256"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        path = OUT / f"capability-{capability_id:04d}.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("SUPER1200_TELEMETRY " + json.dumps({
            "event": "D04_TASK_EVIDENCE", "capability_id": capability_id,
            "name": name, "status": status, "source_sha256": source_hash,
            "test_sha256": test_hash, "evidence_sha256": record["evidence_sha256"],
        }, sort_keys=True), flush=True)
    print(f"SUPER1200_TELEMETRY D04_TASKS_PASS={len(TASKS)-failures}/{len(TASKS)} DOMAIN_CLOSED=NO G23=NOT_RUN G24=NOT_RUN")
    return 0 if failures == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
