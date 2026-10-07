#!/usr/bin/env python3
"""Discover unregistered inbox missions and compile them deterministically."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", default="missions/inbox")
    parser.add_argument("--registry", default="missions/registry")
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy", default="mission-mailbox/config/mailbox-policy.json")
    args = parser.parse_args()

    inbox = Path(args.inbox)
    registry = Path(args.registry)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    pending = []
    for mission in sorted(inbox.glob("*/MISSION_ORIGINAL.md")):
        digest = sha(mission)
        mail_id = "MAIL-" + digest[:20].upper()
        marker = registry / mail_id / "SOURCE_SHA256"
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() == digest:
            continue

        target = out / mail_id
        cmd = [
            sys.executable, "-B", "-I", "scripts/mission_mailbox/compile_mission.py",
            "--mission", str(mission), "--out", str(target), "--policy", args.policy,
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        pending.append({
            "mail_id": mail_id,
            "mission_path": mission.as_posix(),
            "source_sha256": digest,
            "compiled_dir": target.as_posix(),
            "compile_exit_code": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        })

    index = {"schema": "CUSTOSZ_MAILBOX_BATCH/1.0", "count": len(pending), "items": pending}
    (out / "INDEX.json").write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pending_count": len(pending), "mail_ids": [x["mail_id"] for x in pending]}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
