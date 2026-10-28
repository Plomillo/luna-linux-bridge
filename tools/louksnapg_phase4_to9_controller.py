#!/usr/bin/env python3
"""Fail-closed admission gate for the ordered LOUKSNAPG phase 4–9 continuation.

This script does not perform model inference, repair weights, publish local assets,
or grant certification. It authorizes Phase 5 only when a private, provenance-bound
experimental runtime bundle is available and the Phase-4 checkpoint remains valid.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

BASELINE = "66f0f0d22f5e7f7d207b191b39e997d1253a3866"
PHASE4_CONTINUATION_COMMIT = "3595e5e5ba692d27d8182804a91918d61de25e51"
LOCAL_INVENTORY_FINGERPRINT = "f33f25eabed2ccbe07e8917a6b69d446de2831ba6a93a7e4eb39fcfbdad1e9a1"
MANIFEST_PATH = Path("evidence/louksnapg/phase4-repair-candidate.json")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_BUNDLE_BYTES = 2_000_000_000

DOMAINS = {
    "D01_CEREBRO": {
        "path": "1. Cerebro/model.safetensors",
        "baseline_sha256": "e2516453d09285581bd6f3bf45a4c3a9fa6431bdc3dff56e7249d30e4e294ae0",
    },
    "D03_TRANSCRIPCION": {
        "path": "3. Transcripción/model.safetensors",
        "baseline_sha256": "67ee70beb2fb3529270a8169fbb6bd0f538912a064a6a303bec238647b4a5f5f",
    },
    "D04_TRADUCTOR_INTELIGENTE": {
        "path": "4. Traductor Inteligente/Traducción general/model.safetensors",
        "baseline_sha256": "630aad9958f9c78603852c29c382b0fe9d63e64772e21dc6367875a91dc6a28f",
    },
    "D06_SISTEMA_INTELIGENTE": {
        "path": "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
        "baseline_sha256": "01eba827b9dd001a2352f0fd28a0bea229d3a5b3a78a41f3ea3e7c6c21995f56",
    },
}


def valid_sha(value: object) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=20,
    ).stdout.strip()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_manifest(root: Path, manifest: dict, env: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "LOUKSNAPG_PHASE4_REPAIR_CANDIDATE/1.0":
        errors.append("REPAIR_MANIFEST_SCHEMA_INVALID")
    if manifest.get("baseline_commit") != BASELINE:
        errors.append("REPAIR_BASELINE_COMMIT_MISMATCH")
    if not isinstance(manifest.get("candidate_id"), str) or not manifest["candidate_id"].strip():
        errors.append("REPAIR_CANDIDATE_ID_MISSING")
    if manifest.get("payload_storage") != "PRIVATE_AUTHENTICATED_BUNDLE":
        errors.append("REPAIR_PAYLOAD_MUST_REMAIN_IN_PRIVATE_AUTHENTICATED_STORAGE")
    if manifest.get("payload_committed_to_repository") is not False:
        errors.append("LOCAL_MODEL_PAYLOAD_MUST_NOT_BE_COMMITTED_TO_PUBLIC_REPOSITORY")
    if manifest.get("canonical_runtime_mutated") is not False:
        errors.append("CANONICAL_RUNTIME_MUTATION_FORBIDDEN")
    if manifest.get("phases_1_to_3_rerun") is not False:
        errors.append("PHASES_1_TO_3_MUST_BE_REUSED_NOT_RERUN")
    if manifest.get("global_certification") != "NOT_GRANTED":
        errors.append("GLOBAL_CERTIFICATION_CANNOT_BE_GRANTED_BY_REPAIR_MANIFEST")

    bundle = manifest.get("private_bundle")
    if not isinstance(bundle, dict):
        errors.append("PRIVATE_BUNDLE_DESCRIPTOR_MISSING")
    else:
        if bundle.get("format") != "tar.gz":
            errors.append("PRIVATE_BUNDLE_FORMAT_UNSUPPORTED")
        size = bundle.get("bytes")
        if not isinstance(size, int) or size <= 0 or size > MAX_BUNDLE_BYTES:
            errors.append("PRIVATE_BUNDLE_SIZE_OUT_OF_BOUNDS")
        if not valid_sha(bundle.get("sha256")):
            errors.append("PRIVATE_BUNDLE_SHA256_INVALID")
        if not valid_sha(bundle.get("runtime_tree_sha256")):
            errors.append("PRIVATE_RUNTIME_TREE_SHA256_INVALID")

    entries = manifest.get("candidate_weight_artifacts")
    by_domain = {}
    if isinstance(entries, list):
        for row in entries:
            if not isinstance(row, dict):
                continue
            domain = row.get("domain_id")
            if domain in by_domain:
                errors.append("DUPLICATE_CANDIDATE_WEIGHT_DOMAIN:" + str(domain))
            by_domain[domain] = row
    else:
        errors.append("CANDIDATE_WEIGHT_ARTIFACTS_MISSING")

    if set(by_domain) != set(DOMAINS):
        errors.append("CANDIDATE_WEIGHT_DOMAIN_SET_MISMATCH")

    for domain, spec in DOMAINS.items():
        row = by_domain.get(domain)
        if not isinstance(row, dict):
            continue
        if row.get("path") != spec["path"]:
            errors.append("CANDIDATE_WEIGHT_PATH_MISMATCH:" + domain)
        if not isinstance(row.get("bytes"), int) or row.get("bytes", 0) <= 0:
            errors.append("CANDIDATE_WEIGHT_SIZE_INVALID:" + domain)
        if not valid_sha(row.get("sha256")):
            errors.append("CANDIDATE_WEIGHT_SHA256_INVALID:" + domain)
        elif row.get("sha256") == spec["baseline_sha256"]:
            errors.append("CANDIDATE_WEIGHT_UNCHANGED_FROM_FAILED_BASELINE:" + domain)
        if not valid_sha(row.get("source_sha256")):
            errors.append("SOURCE_WEIGHT_SHA256_INVALID:" + domain)
        if not isinstance(row.get("source_bytes"), int) or row.get("source_bytes", 0) <= 0:
            errors.append("SOURCE_WEIGHT_SIZE_INVALID:" + domain)
        if not valid_sha(row.get("transformation_record_sha256")):
            errors.append("TRANSFORMATION_PROVENANCE_HASH_MISSING:" + domain)

    provenance = manifest.get("source_provenance")
    source_by_domain = {}
    if isinstance(provenance, list):
        for row in provenance:
            if not isinstance(row, dict):
                continue
            domain = row.get("domain_id")
            if domain in source_by_domain:
                errors.append("DUPLICATE_SOURCE_PROVENANCE_DOMAIN:" + str(domain))
            source_by_domain[domain] = row
    else:
        errors.append("SOURCE_PROVENANCE_MISSING")

    if set(source_by_domain) != set(DOMAINS):
        errors.append("SOURCE_PROVENANCE_DOMAIN_SET_MISMATCH")

    for domain, row in source_by_domain.items():
        if not isinstance(row, dict):
            continue
        if row.get("source_type") == "existing_local_asset":
            if row.get("source_inventory_fingerprint") != LOCAL_INVENTORY_FINGERPRINT:
                errors.append("LOCAL_SOURCE_INVENTORY_FINGERPRINT_MISMATCH:" + str(domain))
            if row.get("source_id") not in {"W01", "W02", "W03", "W04", "W05", "W06"}:
                errors.append("LOCAL_SOURCE_ID_INVALID:" + str(domain))
        elif row.get("source_type") == "official_upstream":
            uri = row.get("source_uri")
            revision = row.get("source_revision")
            if not isinstance(uri, str) or not uri.startswith("https://"):
                errors.append("OFFICIAL_SOURCE_URI_INVALID:" + str(domain))
            if not isinstance(revision, str) or not revision.strip():
                errors.append("OFFICIAL_SOURCE_REVISION_MISSING:" + str(domain))
        else:
            errors.append("SOURCE_TYPE_UNSUPPORTED:" + str(domain))
        if not valid_sha(row.get("source_sha256")):
            errors.append("SOURCE_PROVENANCE_SHA256_INVALID:" + str(domain))
        if not isinstance(row.get("source_bytes"), int) or row.get("source_bytes", 0) <= 0:
            errors.append("SOURCE_PROVENANCE_SIZE_INVALID:" + str(domain))
        if not valid_sha(row.get("provenance_record_sha256")):
            errors.append("PROVENANCE_RECORD_HASH_MISSING:" + str(domain))

    if not env.get("LOUKSNAPG_PRIVATE_BUNDLE_URL", "").strip():
        errors.append("PRIVATE_BUNDLE_URL_SECRET_MISSING")
    if not env.get("LOUKSNAPG_PRIVATE_BUNDLE_TOKEN", "").strip():
        errors.append("PRIVATE_BUNDLE_TOKEN_SECRET_MISSING")

    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--phase4-report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve(strict=True)
    head = git(root, "rev-parse", "HEAD")
    errors: list[str] = []
    phase4 = {}
    try:
        phase4 = json.loads(args.phase4_report.read_text(encoding="utf-8"))
        if phase4.get("schema") != "LOUKSNAPG_PHASE4_FORENSIC_DIAGNOSIS/1.0":
            errors.append("PHASE4_EVIDENCE_SCHEMA_INVALID")
        if phase4.get("candidate_commit_under_test") != BASELINE:
            errors.append("PHASE4_BASELINE_CANDIDATE_MISMATCH")
        if phase4.get("continuation_commit") != PHASE4_CONTINUATION_COMMIT:
            errors.append("PHASE4_CONTINUATION_COMMIT_MISMATCH")
        continuation = phase4.get("continuation_identity", {})
        if continuation.get("baseline_commit_present") is not True:
            errors.append("PHASE4_BASELINE_COMMIT_PRESENCE_UNVERIFIED")
        if continuation.get("baseline_is_ancestor") is not True:
            errors.append("PHASE4_BASELINE_ANCESTRY_UNVERIFIED")
        if continuation.get("runtime_tree_unchanged_from_baseline") is not True:
            errors.append("PHASE4_RUNTIME_TREE_PRESERVATION_UNVERIFIED")
        if continuation.get("phases_1_to_3_rerun") is not False:
            errors.append("PHASE4_PHASES_1_TO_3_REUSE_NOT_PROVEN")
        if phase4.get("global_certification") != "NOT_GRANTED":
            errors.append("PHASE4_CERTIFICATION_STATE_INVALID")
        phase4_status = phase4.get("phase_progress", {}).get("phase_4", "UNKNOWN")
        if not str(phase4_status).startswith("DIAGNOSIS_COMPLETE"):
            errors.append("PHASE4_DIAGNOSIS_NOT_COMPLETE")
    except Exception as exc:
        phase4_status = "PHASE4_EVIDENCE_UNREADABLE"
        errors.append("PHASE4_EVIDENCE_UNREADABLE:" + type(exc).__name__)

    try:
        subprocess.run(["git", "-C", str(root), "cat-file", "-e", PHASE4_CONTINUATION_COMMIT + "^{commit}"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", PHASE4_CONTINUATION_COMMIT, "HEAD"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except Exception:
        errors.append("CURRENT_COMMIT_NOT_DESCENDANT_OF_PHASE4_CONTINUATION_ANCHOR")

    try:
        changed_runtime = git(root, "diff", "--name-only", PHASE4_CONTINUATION_COMMIT, "HEAD", "--", "cajita-luna-runtime")
        if changed_runtime:
            errors.append("PUBLIC_CANONICAL_RUNTIME_DIFF_FORBIDDEN")
    except Exception:
        errors.append("CANONICAL_RUNTIME_DIFF_CHECK_FAILED")

    manifest_path = root / MANIFEST_PATH
    manifest = {}
    manifest_errors = ["PHASE4_REPAIR_MANIFEST_MISSING"]
    manifest_sha256 = None
    if manifest_path.is_file():
        raw = manifest_path.read_bytes()
        manifest_sha256 = hashlib.sha256(raw).hexdigest()
        try:
            manifest = json.loads(raw.decode("utf-8"))
            manifest_errors = validate_manifest(root, manifest, dict(os.environ))
        except Exception as exc:
            manifest_errors = ["PHASE4_REPAIR_MANIFEST_INVALID_JSON:" + type(exc).__name__]
    errors.extend(manifest_errors)

    ready = not errors
    output = {
        "schema": "LOUKSNAPG_PHASE4_TO9_ADMISSION/1.0",
        "candidate_controller_commit": head,
        "baseline_candidate_commit": BASELINE,
        "phase4_run_id": os.environ.get("LOUKSNAPG_PHASE4_RUN_ID", "UNKNOWN"),
        "phase4_status": phase4_status,
        "phase4_evidence_schema": phase4.get("schema") if phase4 else None,
        "phase4_repair_gate": "PASS_PRIVATE_REPAIR_BUNDLE_ADMITTED" if ready else "BLOCKED_FAIL_CLOSED",
        "phase4_repair_manifest_path": MANIFEST_PATH.as_posix(),
        "phase4_repair_manifest_sha256": manifest_sha256,
        "repair_candidate_id": manifest.get("candidate_id") if manifest else None,
        "phase5_targeted_post_repair_tests": "READY_TO_RUN" if ready else "NOT_RUN_PHASE4_REPAIR_GATE_CLOSED",
        "phase6_integrated_entrypoint": "PENDING_PHASE5_PASS",
        "phase7_independent_validation": "PENDING_PHASE6_PASS",
        "phase8_release": "BLOCKED_G23_G24_AND_ALL_REQUIRED_DOMAIN_GATES",
        "phase9_governance": "ACTIVE_FAIL_CLOSED",
        "phases_1_to_3": "REUSED_NOT_RERUN",
        "canonical_runtime_mutation": "NOT_PERFORMED",
        "local_asset_upload_to_public_repository": "FORBIDDEN",
        "global_certification": "NOT_GRANTED",
        "blockers": errors,
        "decision": "CONTINUE_PHASE5" if ready else "WAIT_FOR_VERIFIED_PRIVATE_REPAIR_INPUT",
    }
    write_json(args.out, output)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as stream:
            stream.write("repair_ready=" + ("true" if ready else "false") + "\n")
            stream.write("phase4_status=" + str(phase4_status).replace("\n", " ") + "\n")
            stream.write("gate_status=" + output["phase4_repair_gate"] + "\n")
            stream.write("repair_candidate_id=" + str(output["repair_candidate_id"] or "") + "\n")
    print(json.dumps(output, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
