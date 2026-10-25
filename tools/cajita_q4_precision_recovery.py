#!/usr/bin/env python3
"""Restore signed-INT4 factors of the same Cajita models from a pinned LFS snapshot."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

Q4_SOURCE_REF = "fb8e6fcf9a8ec31d151191f0c6e90b51e77505fb"
WEIGHT_MANIFEST_REL = "cajita-luna-runtime/CAJITA_RUNTIME_V1/weights_manifest.json"
RESTORE_IDS = ("W01", "W02", "W03", "W05")
UNCHANGED_IDS = ("W04", "W06")
Q4_SCHEMA = "CAJITA_Q4_BLOCK_PACKED/1.0"
Q2_ENCODING = "UNSIGNED_INT2_ASYMMETRIC"

TASK_ADAPTER_ROWS = {
    "W01": ("1. Cerebro/model.safetensors", "D01_CEREBRO"),
    "W02": ("3. Transcripción/model.safetensors", "D03_TRANSCRIPCION"),
    "W03": ("4. Traductor Inteligente/Traducción general/model.safetensors", "D04_TRADUCTOR_INTELIGENTE"),
    "W05": ("6. Sistema Inteligente/Análisis Avanzado/model.safetensors", "D06_SISTEMA_INTELIGENTE"),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_lfs_pointer(data: bytes) -> dict[str, Any]:
    """Parse a Git LFS pointer; do not trust a pointer until object bytes are verified."""
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("LFS_POINTER_NOT_ASCII") from exc
    if not text.startswith("version https://git-lfs.github.com/spec/v1\n"):
        raise ValueError("HISTORICAL_WEIGHT_IS_NOT_A_GIT_LFS_POINTER")
    oid_match = re.search(r"^oid sha256:([0-9a-f]{64})$", text, re.MULTILINE)
    size_match = re.search(r"^size ([0-9]+)$", text, re.MULTILINE)
    if oid_match is None or size_match is None:
        raise ValueError("LFS_POINTER_FIELDS_INVALID")
    return {"sha256": oid_match.group(1), "bytes": int(size_match.group(1))}


def _git_show(repo: Path, ref_path: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", ref_path],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, shell=False, timeout=180,
    )
    if proc.returncode:
        raise RuntimeError(
            "PINNED_Q4_GIT_BLOB_MISSING:" + ref_path + ":"
            + proc.stderr.decode("utf-8", errors="replace")[-600:]
        )
    return proc.stdout


def _artifact_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 6:
        raise RuntimeError("WEIGHT_MANIFEST_ARTIFACT_COUNT_MISMATCH")
    rows: dict[str, dict[str, Any]] = {}
    for row in artifacts:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or row["id"] in rows:
            raise RuntimeError("WEIGHT_MANIFEST_ID_INVALID_OR_DUPLICATE")
        rows[row["id"]] = row
    if set(rows) != set(RESTORE_IDS) | set(UNCHANGED_IDS):
        raise RuntimeError("CANONICAL_WEIGHT_ARTIFACT_ID_SET_MISMATCH")
    return rows


def validate_manifest_transition(current: dict[str, Any], historical_q4: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Verify same candidate, artifact paths/domains, larger Q4 files and unchanged W04/W06."""
    expected_schema = "CAJITA_SIX_DOMAIN_WEIGHT_MANIFEST/1.0"
    if current.get("schema") != expected_schema or historical_q4.get("schema") != expected_schema:
        raise RuntimeError("WEIGHT_MANIFEST_SCHEMA_MISMATCH")
    if current.get("candidate_id") != historical_q4.get("candidate_id"):
        raise RuntimeError("CANONICAL_MODEL_CANDIDATE_ID_MISMATCH")
    current_rows = _artifact_map(current)
    q4_rows = _artifact_map(historical_q4)
    for artifact_id, before in current_rows.items():
        after = q4_rows[artifact_id]
        for field in ("path", "domain_id", "label"):
            if before.get(field) != after.get(field):
                raise RuntimeError("CANONICAL_WEIGHT_BINDING_DRIFT:" + artifact_id + ":" + field)
        if artifact_id in UNCHANGED_IDS:
            for field in ("bytes", "sha256"):
                if before.get(field) != after.get(field):
                    raise RuntimeError("UNRELATED_MODEL_WEIGHT_MUTATION:" + artifact_id + ":" + field)
        else:
            if not isinstance(after.get("sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", after["sha256"]) is None:
                raise RuntimeError("HISTORICAL_Q4_SHA256_INVALID:" + artifact_id)
            size_before = before.get("bytes")
            size_after = after.get("bytes")
            if (isinstance(size_before, bool) or not isinstance(size_before, int)
                or isinstance(size_after, bool) or not isinstance(size_after, int)
                or size_after <= size_before):
                raise RuntimeError("Q4_PRECISION_RECOVERY_NOT_HIGHER_PRECISION:" + artifact_id)
    if historical_q4.get("artifact_count") != current.get("artifact_count"):
        raise RuntimeError("WEIGHT_MANIFEST_DECLARED_COUNT_DRIFT")
    return q4_rows


def resolve_historical_weight_blob(data: bytes, expected_sha256: str, expected_bytes: int, object_root: str | Path) -> dict[str, Any]:
    """Accept a verified LFS pointer/object or a raw Git-show payload with exact pinned identity."""
    try:
        pointer = parse_lfs_pointer(data)
    except ValueError:
        if len(data) == expected_bytes and sha256_bytes(data) == expected_sha256:
            return {
                "source_kind": "RAW_GIT_SHOW_PAYLOAD_SHA256_VERIFIED",
                "source_object": None,
                "source_bytes": data,
                "bytes": expected_bytes,
                "sha256": expected_sha256,
            }
        raise RuntimeError("HISTORICAL_WEIGHT_NOT_POINTER_OR_PINNED_PAYLOAD")
    if pointer != {"sha256": expected_sha256, "bytes": expected_bytes}:
        raise RuntimeError("PINNED_Q4_LFS_POINTER_MISMATCH")
    root = Path(object_root).resolve()
    obj = root / pointer["sha256"][:2] / pointer["sha256"][2:4] / pointer["sha256"]
    if obj.is_symlink() or not obj.is_file():
        raise RuntimeError("PINNED_Q4_LFS_OBJECT_MISSING")
    if obj.stat().st_size != pointer["bytes"] or sha256_file(obj) != pointer["sha256"]:
        raise RuntimeError("PINNED_Q4_LFS_OBJECT_IDENTITY_MISMATCH")
    return {
        "source_kind": "LFS_POINTER_AND_OBJECT_SHA256_VERIFIED",
        "source_object": obj,
        "source_bytes": None,
        "bytes": pointer["bytes"],
        "sha256": pointer["sha256"],
    }


def validate_q4_sidecar(data: bytes, expected_sha256: str) -> dict[str, Any]:
    try:
        sidecar = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("PINNED_Q4_SIDECAR_INVALID_JSON") from exc
    if sidecar.get("schema") != Q4_SCHEMA or sidecar.get("candidate_sha256") != expected_sha256:
        raise RuntimeError("PINNED_Q4_SIDECAR_IDENTITY_MISMATCH")
    entries = sidecar.get("tensors")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("PINNED_Q4_SIDECAR_TENSORS_MISSING")
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("PINNED_Q4_SIDECAR_TENSOR_INVALID")
        encoding = entry.get("encoding", "SIGNED_INT4_BLOCKWISE")
        if encoding != "SIGNED_INT4_BLOCKWISE":
            raise RuntimeError("Q2_OR_UNKNOWN_ENCODING_IN_Q4_SIDECAR")
        shape = entry.get("shape")
        if (not isinstance(shape, list) or not shape
            or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in shape)):
            raise RuntimeError("Q4_SIDECAR_SHAPE_INVALID")
        if int(entry.get("numel", 0)) <= 0:
            raise RuntimeError("Q4_SIDECAR_NUMEL_INVALID")
    return sidecar


def _update_adapter_bindings(adapter_path: Path, rows: dict[str, dict[str, Any]], manifest_sha: str) -> dict[str, Any]:
    if adapter_path.is_symlink() or not adapter_path.is_file():
        raise RuntimeError("TASK_ADAPTER_SOURCE_MISSING_OR_UNSAFE")
    original = adapter_path.read_text(encoding="utf-8")
    updated = original
    changed = []
    for artifact_id, (relative_path, domain_id) in TASK_ADAPTER_ROWS.items():
        row = rows[artifact_id]
        target_line = [line for line in updated.splitlines() if ('"'+domain_id+'": {' in line and '"weight":"'+relative_path+'"' in line)]
        if len(target_line) != 1:
            raise RuntimeError("TASK_ADAPTER_WEIGHT_BINDING_NOT_UNIQUE:" + artifact_id)
        old_line = target_line[0]
        pattern = re.compile(r'("sha":")[0-9a-f]{64}(","bytes":)[0-9]+')
        new_line, substitutions = pattern.subn(
            lambda m: m.group(1) + row["sha256"] + m.group(2) + str(row["bytes"]),
            old_line, count=1
        )
        if substitutions != 1:
            raise RuntimeError("TASK_ADAPTER_WEIGHT_IDENTITY_FIELDS_MISSING:" + artifact_id)
        updated = updated.replace(old_line, new_line, 1)
        changed.append({"id": artifact_id, "domain_id": domain_id,
                        "path": relative_path, "bytes": row["bytes"], "sha256": row["sha256"]})
    manifest_pattern = re.compile(r'^MANIFEST_SHA = "[0-9a-f]{64}"$', re.MULTILINE)
    updated, replacements = manifest_pattern.subn('MANIFEST_SHA = "' + manifest_sha + '"', updated, count=1)
    if replacements != 1:
        raise RuntimeError("TASK_ADAPTER_MANIFEST_SHA_CONSTANT_NOT_UNIQUE")
    adapter_path.write_text(updated, encoding="utf-8")
    reread = adapter_path.read_text(encoding="utf-8")
    if reread != updated or manifest_sha not in reread:
        raise RuntimeError("TASK_ADAPTER_REBIND_POSTCHECK_FAILED")
    for item in changed:
        expected = '"sha":"' + item["sha256"] + '","bytes":' + str(item["bytes"])
        if expected not in reread:
            raise RuntimeError("TASK_ADAPTER_WEIGHT_REBIND_POSTCHECK_FAILED:" + item["id"])
    return {"status": "PASS", "manifest_sha256": manifest_sha, "updated_weight_bindings": changed}


def restore_q4_precision(repo_root: str | Path, runtime_root: str | Path) -> dict[str, Any]:
    """Fetch and restore the pinned Q4 blobs into the staging tree only."""
    repo = Path(repo_root).resolve(strict=True)
    runtime = Path(runtime_root).resolve(strict=True)
    manifest_path = runtime / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise RuntimeError("CURRENT_WEIGHT_MANIFEST_MISSING_OR_UNSAFE")
    current = json.loads(manifest_path.read_text(encoding="utf-8"))
    historical_manifest_raw = _git_show(repo, Q4_SOURCE_REF + ":" + WEIGHT_MANIFEST_REL)
    historical = json.loads(historical_manifest_raw.decode("utf-8"))
    q4_rows = validate_manifest_transition(current, historical)

    restore_paths = [q4_rows[artifact_id]["path"] for artifact_id in RESTORE_IDS]
    fetch = subprocess.run(
        ["git", "-C", str(repo), "lfs", "fetch", "origin", Q4_SOURCE_REF,
         "--include=" + ",".join("cajita-luna-runtime/" + rel for rel in restore_paths),
         "--exclude="],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, check=False, shell=False, timeout=1800,
    )
    if fetch.returncode:
        raise RuntimeError("PINNED_Q4_LFS_FETCH_FAILED:" + fetch.stderr[-1200:])

    object_root_raw = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "--git-path", "lfs/objects"], text=True
    ).strip()
    object_root = Path(object_root_raw)
    if not object_root.is_absolute():
        object_root = repo / object_root
    object_root = object_root.resolve()

    staged: list[dict[str, Any]] = []
    # Fetch and validate all four files and sidecars before mutating the staged tree.
    for artifact_id in RESTORE_IDS:
        row = q4_rows[artifact_id]
        rel = row["path"]
        historical_blob = _git_show(repo, Q4_SOURCE_REF + ":cajita-luna-runtime/" + rel)
        resolved = resolve_historical_weight_blob(historical_blob, row["sha256"], row["bytes"], object_root)
        sidecar_rel = "cajita-luna-runtime/" + rel + ".q4.json"
        sidecar_bytes = _git_show(repo, Q4_SOURCE_REF + ":" + sidecar_rel)
        sidecar = validate_q4_sidecar(sidecar_bytes, row["sha256"])
        staged.append({
            "id": artifact_id, "path": rel,
            "source_object": resolved["source_object"], "source_bytes": resolved["source_bytes"],
            "source_kind": resolved["source_kind"], "bytes": resolved["bytes"],
            "sha256": resolved["sha256"], "sidecar_bytes": sidecar_bytes,
            "sidecar_sha256": sha256_bytes(sidecar_bytes), "factor_tensor_count": len(sidecar["tensors"]),
        })

    # Atomic per-file copies are only into the ephemeral factory stage, never the source checkout.
    for item in staged:
        destination = runtime / item["path"]
        if destination.is_symlink() or not destination.is_file():
            raise RuntimeError("Q2_STAGE_WEIGHT_MISSING_OR_UNSAFE:" + item["id"])
    for item in staged:
        destination = runtime / item["path"]
        temporary = destination.with_name(destination.name + ".q4-restoring")
        try:
            if item["source_object"] is not None:
                shutil.copyfile(item["source_object"], temporary)
            else:
                temporary.write_bytes(item["source_bytes"])
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        sidecar = destination.with_name(destination.name + ".q4.json")
        if sidecar.is_symlink():
            raise RuntimeError("Q4_RESTORE_SIDECAR_SYMLINK:" + item["id"])
        sidecar_temp = sidecar.with_name(sidecar.name + ".q4-restoring")
        sidecar_temp.write_bytes(item["sidecar_bytes"])
        os.replace(sidecar_temp, sidecar)

    historical["precision_recovery"] = {
        "schema": "CAJITA_Q4_PRECISION_RECOVERY/1.0",
        "source_ref": Q4_SOURCE_REF,
        "restored_artifact_ids": list(RESTORE_IDS),
        "unchanged_artifact_ids": list(UNCHANGED_IDS),
        "packing": "SIGNED_INT4_BLOCKWISE",
        "second_stage_unsigned_q2_packing": "REMOVED",
        "canonical_candidate_id_preserved": True,
        "model_id_or_engine_reassignment": False,
        "factorization_rank_changed": False,
        "source_worktree_mutated": False,
        "semantic_quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED",
    }
    actual_weight_bytes = sum(int(row["bytes"]) for row in historical["artifacts"])
    historical["total_weight_bytes"] = actual_weight_bytes
    historical["total_weight_decimal_mb"] = round(actual_weight_bytes / 1_000_000, 3)
    historical["packed_artifact_total_decimal_mb"] = round(actual_weight_bytes / 1_000_000, 3)
    manifest_bytes = (json.dumps(historical, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    manifest_sha = sha256_bytes(manifest_bytes)
    adapter_report = _update_adapter_bindings(runtime / "cajita_task_adapters.py", q4_rows, manifest_sha)

    actual_rows = []
    for item in staged:
        path = runtime / item["path"]
        if path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise RuntimeError("RESTORED_Q4_WEIGHT_POSTCHECK_FAILED:" + item["id"])
        sidecar = path.with_name(path.name + ".q4.json")
        if sidecar.read_bytes() != item["sidecar_bytes"] or sha256_file(sidecar) != item["sidecar_sha256"]:
            raise RuntimeError("RESTORED_Q4_SIDECAR_POSTCHECK_FAILED:" + item["id"])
        actual_rows.append({
            "id": item["id"], "path": item["path"], "bytes": item["bytes"],
            "sha256": item["sha256"], "sidecar_sha256": item["sidecar_sha256"],
            "source_kind": item["source_kind"],
            "factor_tensor_count": item["factor_tensor_count"],
        })
    return {
        "schema": "CAJITA_Q4_PRECISION_RECOVERY/1.0",
        "status": "PASS_SAME_MODEL_Q4_FACTORS_RESTORED",
        "source_ref": Q4_SOURCE_REF,
        "restored": actual_rows,
        "unchanged_artifact_ids": list(UNCHANGED_IDS),
        "weight_manifest_sha256": manifest_sha,
        "weight_manifest_bytes": len(manifest_bytes),
        "weight_manifest_total_weight_bytes": actual_weight_bytes,
        "weight_manifest_decimal_mb": historical["total_weight_decimal_mb"],
        "task_adapter_binding": adapter_report,
        "candidate_id_preserved": True,
        "canonical_engine_identities_changed": False,
        "model_id_or_factorization_rank_changed": False,
        "source_worktree_mutated": False,
        "second_stage_q2_packing_removed": True,
        "semantic_quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED",
    }
