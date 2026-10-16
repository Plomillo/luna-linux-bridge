#!/usr/bin/env python3
"""Copy mailbox result directories into the persistent repository registry."""
import argparse
import json
import shutil
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--registry", default="missions/registry")
    args = parser.parse_args()

    results = Path(args.results)
    registry = Path(args.registry)
    registry.mkdir(parents=True, exist_ok=True)
    count = 0

    for source in sorted(results.iterdir() if results.is_dir() else []):
        if not source.is_dir() or not source.name.startswith("MAIL-"):
            continue
        receipt = source / "RECEIPT.json"
        native = source / "MISSION_NATIVE.json"
        if receipt.is_file():
            digest = json.loads(receipt.read_text(encoding="utf-8")).get("source_sha256")
        elif native.is_file():
            digest = json.loads(native.read_text(encoding="utf-8"))["source"]["sha256"]
        else:
            continue

        state_path = source / "MISSION_STATE.json"
        if not state_path.is_file():
            continue
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("workflow_technical_status") != "PASS":
            continue
        if state.get("current_state") in {
            "RECEIVED",
            "VALIDATED",
            "COMPILED",
            "SEMANTICALLY_EQUIVALENT_BY_BYTE_PRESERVATION",
        }:
            continue

        target = registry / source.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        (target / "SOURCE_SHA256").write_text(str(digest) + "\n", encoding="utf-8")
        count += 1

    print(json.dumps({"published_registry_entries": count}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
