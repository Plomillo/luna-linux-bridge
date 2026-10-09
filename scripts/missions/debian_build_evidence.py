#!/usr/bin/env python3
"""Record and compare hash-bound evidence for two Debian package builds."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys


def digest(package: pathlib.Path, output: pathlib.Path) -> None:
    package = package.resolve()
    if not package.is_file():
        raise FileNotFoundError(f"Debian package not found: {package}")
    record = {
        "package_name": package.name,
        "size_bytes": package.stat().st_size,
        "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True))


def finalize(report_path: pathlib.Path, second_result: pathlib.Path | None, failed: bool) -> None:
    report_path = report_path.resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if failed:
        report["status"] = "HOLD_REPRODUCIBILITY_BUILD2_FAILED"
        report["reproducibility"] = {
            "sha256_equal": False,
            "reason": "Independent second build failed; inspect the CP-08 job log.",
        }
    else:
        if second_result is None or not second_result.is_file():
            raise FileNotFoundError("Second-build digest result is missing.")
        second = json.loads(second_result.read_text(encoding="utf-8"))
        first = report["builds"]["first"]
        same_hash = first["sha256"] == second["sha256"]
        same_size = first["size_bytes"] == second["size_bytes"]
        report["builds"]["independent_second"] = second
        report["reproducibility"] = {
            "sha256_equal": same_hash,
            "size_equal": same_size,
            "source_snapshot": "git archive of exact candidate commit",
            "independent_cargo_target": True,
        }
        report["status"] = "PASS_REPRODUCIBLE_BUILD" if same_hash and same_size else "HOLD_NON_REPRODUCIBLE_BUILD"
        report["scope"] = "Two clean source-snapshot builds completed with pinned npm lockfile and isolated Cargo target directories."
    report["revalidated_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "reproducibility": report["reproducibility"]}, indent=2, sort_keys=True))
    if failed or report["status"] != "PASS_REPRODUCIBLE_BUILD":
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p_digest = commands.add_parser("digest")
    p_digest.add_argument("--package", required=True, type=pathlib.Path)
    p_digest.add_argument("--output", required=True, type=pathlib.Path)
    p_finalize = commands.add_parser("finalize")
    p_finalize.add_argument("--report", required=True, type=pathlib.Path)
    p_finalize.add_argument("--second-result", type=pathlib.Path)
    p_finalize.add_argument("--second-build-failed", action="store_true")
    args = parser.parse_args()
    if args.command == "digest":
        digest(args.package, args.output)
    else:
        finalize(args.report, args.second_result, args.second_build_failed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
