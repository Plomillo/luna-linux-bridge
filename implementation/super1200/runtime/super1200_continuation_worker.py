#!/usr/bin/env python3
"""Retired synthetic materializer.

This entry point is intentionally fail-closed. The previous implementation
generated generic wrapper code/tests and marked entire domains EVIDENCED without
proving domain behavior. It must not be used as a material executor.

A reviewed domain-specific executor must be registered separately in
continuity/EXECUTORS.json, with behavior-level tests and immutable evidence.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    target = Path(os.environ.get("TARGET_ROOT", Path.cwd())).resolve()
    point = os.environ.get("NEXT_POINT", "").strip()
    event = {
        "schema": "SUPER1200_WORKER_REFUSAL/1",
        "event": "SYNTHETIC_MATERIALIZATION_DISABLED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "next_point": point or None,
        "branch": "custosz/super-1200-implementation-20261007",
        "material_changes": False,
        "capability_states_changed": False,
        "certification_changed": False,
        "reason": "A domain-specific reviewed executor with behavior-level tests is required.",
    }
    evidence = target / "continuity" / "runtime-evidence" / "WORKER_REFUSAL.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SUPER1200_TELEMETRY " + json.dumps(event, sort_keys=True), flush=True)
    print("DISPATCH_DENIED_SYNTHETIC_MATERIALIZATION_DISABLED", file=sys.stderr, flush=True)
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
