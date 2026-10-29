#!/usr/bin/env python3
"""Build the LOUKSNAPG2 candidate from unchanged source trees.

This script is invoked only by the CUSTOSZ V9 bounded worker mission. It prepares
a separate factory output, packages the exact architecture prefix and Cajita source
document with the additive runtime, and runs an independently implemented bundle
validator. It never edits the source architecture or original Cajita tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


MAX_BYTES = 490_000_000
MAX_RUNTIME_BYTES = 470_000_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], cwd: Path, timeout: int) -> dict:
    completed = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True,
        timeout=timeout, check=False, env=os.environ.copy(),
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-10000:],
        "stderr_tail": completed.stderr[-6000:],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args(argv)

    root = args.repo_root.resolve(strict=True)
    out = args.output_dir.resolve()
    if args.max_bytes != MAX_BYTES:
        raise SystemExit("UNAUTHORIZED_ALTERNATIVE_CAP_CHANGE")
    if out.exists() or out.is_symlink():
        raise SystemExit("OUTPUT_DIR_ALREADY_EXISTS_FAIL_CLOSED")
    out.mkdir(parents=True, exist_ok=False)
    factory_dir = out / "factory"
    report_path = out / "LOUKSNAPG2_BUILD_REPORT.json"
    candidate_path = out / "LOUKSNAPG2.md"
    source_architecture = root / "LOUKSNAMEJORADA.md"
    cajita_doc = root / "cajita-luna-runtime" / "CajitadeLuna.md"
    g2_runtime = root / "cajita-luna-runtime" / "LOUKSNAPG2_RUNTIME"

    report = {
        "schema": "LOUKSNAPG2_BUILD_REPORT/1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        "candidate_path": candidate_path.name,
        "candidate_status": "NOT_BUILT",
        "global_certification": "NOT_GRANTED",
        "certification_reason": "Build and source integrity do not demonstrate runtime semantic quality; G23/G24 must pass independently.",
        "budget": {"max_bytes": MAX_BYTES, "runtime_max_bytes": MAX_RUNTIME_BYTES},
        "source": {},
        "factory": {},
        "bundle": {},
        "independent_validation": {},
        "blockers": [],
    }
    try:
        for name, path in {
            "source_architecture": source_architecture,
            "cajita_doc": cajita_doc,
            "g2_engine": g2_runtime / "louksnapg2_engine.py",
            "g2_service": g2_runtime / "louksnapg2_service.py",
            "g2_route_overlay": g2_runtime / "route_overlay.json",
            "externalized_asset_registry": g2_runtime / "externalized_assets.json",
            "native_task_adapters": root / "cajita-luna-runtime" / "cajita_task_adapters.py",
            "original_weight_manifest": root / "cajita-luna-runtime" / "CAJITA_RUNTIME_V1" / "weights_manifest.json",
        }.items():
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("SOURCE_INPUT_NOT_REGULAR_FILE:" + name)
            report["source"][name] = {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        report["source"]["architecture_prefix_byte_exact_required"] = True
        report["source"]["cajita_document_byte_exact_suffix_required"] = True
        if sha256_file(source_architecture) != "8cdefe026de748bf924f14a9b6efc6308079c2c2":
            # The upstream content hash used by the source registry is the Git blob SHA,
            # not the raw-file SHA; compare the exact file against git HEAD to avoid
            # confusing the two hash namespaces.
            git_blob = subprocess.run(
                ["git", "hash-object", str(source_architecture)],
                cwd=root, capture_output=True, text=True, check=False,
            )
            report["source"]["architecture_git_blob_sha"] = git_blob.stdout.strip()
            if git_blob.returncode or git_blob.stdout.strip() != "8cdefe026de748bf924f14a9b6efc6308079c2c2":
                raise RuntimeError("PROTECTED_ARCHITECTURE_SOURCE_BLOB_MISMATCH")
        git_cajita = subprocess.run(
            ["git", "hash-object", str(cajita_doc)],
            cwd=root, capture_output=True, text=True, check=False,
        )
        report["source"]["cajita_document_git_blob_sha"] = git_cajita.stdout.strip()
        if git_cajita.returncode or git_cajita.stdout.strip() != "674c97a1d8b2e518ae8d5d9e8980399f292c6194":
            raise RuntimeError("CAJITA_DOCUMENT_SOURCE_BLOB_MISMATCH")

        python = sys.executable
        factory_result = run(
            [python, str(root / "tools" / "cajita_runtime_factory.py"),
             "--repo-root", str(root), "--output-dir", str(factory_dir),
             "--raw-cap-bytes", "1500000000", "--combined-cap-bytes", str(MAX_BYTES)],
            root, 2400,
        )
        report["factory"] = factory_result
        if factory_result["exit_code"] != 0:
            raise RuntimeError("CAJITA_FACTORY_FAILED:" + factory_result["stderr_tail"][-1500:])
        factory_report_path = factory_dir / "factory-report.json"
        runtime_archive = factory_dir / "CAJITA_LUNA_RUNTIME_V10.macrodown"
        factory_document = factory_dir / "Louksna1.md"
        for label, path in {
            "factory_report": factory_report_path,
            "runtime_archive": runtime_archive,
            "factory_document": factory_document,
        }.items():
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("FACTORY_OUTPUT_MISSING:" + label)
        factory_report = json.loads(factory_report_path.read_text(encoding="utf-8"))
        report["factory"]["reported_status"] = factory_report.get("status")
        report["factory"]["distribution"] = factory_report.get("distribution")
        if factory_report.get("status") != "PASS_MANUFACTURED_CANDIDATE_PENDING_G23_G24":
            raise RuntimeError("FACTORY_STATUS_NOT_PASS")
        if runtime_archive.stat().st_size > MAX_RUNTIME_BYTES:
            raise RuntimeError("RUNTIME_OVER_CAP")

        # The packaged document retains the exact architecture prefix and original
        # Cajita document as an exact suffix; only its container member name changes.
        combined_doc = out / "LOUKSNAMEJORADA.md"
        shutil.copyfile(factory_document, combined_doc)
        combined_bytes = combined_doc.read_bytes()
        architecture_bytes = source_architecture.read_bytes()
        cajita_bytes = cajita_doc.read_bytes()
        if not combined_bytes.startswith(architecture_bytes):
            raise RuntimeError("LOUKSNAMEJORADA_PREFIX_NOT_BYTE_EXACT")
        if not combined_bytes.endswith(cajita_bytes):
            raise RuntimeError("CAJITA_DOCUMENT_COPY_NOT_EXACT_SUFFIX")
        report["source"]["combined_document"] = {
            "path": combined_doc.name,
            "bytes": len(combined_bytes),
            "sha256": hashlib.sha256(combined_bytes).hexdigest(),
            "prefix_byte_exact": True,
            "cajita_suffix_byte_exact": True,
        }

        bundle_result = run(
            [python, str(root / "tools" / "louksnapg2_bundle.py"),
             "--document", str(combined_doc),
             "--runtime", str(runtime_archive),
             "--source-architecture", str(source_architecture),
             "--cajita-doc", str(cajita_doc),
             "--output", str(candidate_path),
             "--max-bytes", str(MAX_BYTES)],
            root, 1800,
        )
        report["bundle"] = bundle_result
        if bundle_result["exit_code"] != 0 or not candidate_path.is_file():
            raise RuntimeError("LOUKSNAPG2_BUNDLE_FAILED:" + bundle_result["stderr_tail"][-1500:])
        measured_bytes = candidate_path.stat().st_size
        measured_sha = sha256_file(candidate_path)
        if measured_bytes > MAX_BYTES:
            raise RuntimeError(f"LOUKSNAPG2_OVER_CAP:{measured_bytes}>{MAX_BYTES}")

        independent_path = out / "LOUKSNAPG2_INDEPENDENT_VALIDATION.json"
        validator_result = run(
            [python, str(root / "tools" / "louksnapg2_independent_validator.py"),
             "--bundle", str(candidate_path), "--max-bytes", str(MAX_BYTES),
             "--expected-source-commit", os.environ.get("GITHUB_SHA", ""),
             "--report", str(independent_path)],
            root, 900,
        )
        report["independent_validation"] = validator_result
        if validator_result["exit_code"] != 0 or not independent_path.is_file():
            raise RuntimeError("INDEPENDENT_BUNDLE_VALIDATION_FAILED:" + validator_result["stderr_tail"][-1500:])
        validation = json.loads(independent_path.read_text(encoding="utf-8"))
        report["independent_validation"]["status"] = validation.get("status")
        report["independent_validation"]["identity_preservation_status"] = validation.get("identity_preservation_status")
        report["independent_validation"]["runtime_routing_registry"] = validation.get("runtime_routing_registry")
        report["candidate"] = {
            "path": candidate_path.name,
            "bytes": measured_bytes,
            "sha256": measured_sha,
            "cap_bytes": MAX_BYTES,
            "within_cap": measured_bytes <= MAX_BYTES,
            "runtime_archive_bytes": runtime_archive.stat().st_size,
            "runtime_archive_sha256": sha256_file(runtime_archive),
            "candidate_document_bytes": combined_doc.stat().st_size,
            "source_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        }
        report["budget"]["status"] = "PASS_EXACT_BYTES_MEASURED_AFTER_ZIP_CLOSE"
        report["candidate_status"] = "PASS_BUILT_AND_INDEPENDENTLY_INTEGRITY_VALIDATED_PENDING_G24"
        report["gates"] = {
            "G23": "PRELIMINARY_STRUCTURAL_CHECK_PASS_NOT_SIGNED_PUAC2",
            "G24": "NOT_GRANTED",
            "functional_domain_quality": "PENDING_REAL_MODEL_EVALUATION",
        }
        report["status"] = "PASS_CANDIDATE_BUILD_ONLY"
        report["global_certification"] = "NOT_GRANTED"
        report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": report["status"],
            "candidate": report["candidate"],
            "gates": report["gates"],
            "global_certification": report["global_certification"],
            "report": str(report_path),
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as exc:
        report["status"] = "FAIL_CLOSED"
        report["candidate_status"] = "NOT_RELEASED"
        report["blockers"].append(type(exc).__name__ + ":" + str(exc)[:3000])
        report["global_certification"] = "NOT_GRANTED"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["status"], "blockers": report["blockers"], "report": str(report_path)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
