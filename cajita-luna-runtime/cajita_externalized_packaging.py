#!/usr/bin/env python3
"""Fail-closed packaging and reconstruction contract for Cajita externalized assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

RUNTIME_PREFIX = "cajita-luna-runtime/"
PLACEMENT_NAME = "EXTERNALIZED_ASSET_PLACEMENT.json"
SOURCE_REGISTRY_NAME = "module_registry.json"
DISTRIBUTION_REGISTRY_NAME = "CAJITA_DISTRIBUTION_MODULE_REGISTRY.json"
MODULE_DESCRIPTOR_NAME = "CAJITA_MODULE.json"
EXPECTED_ASSET_COUNT = 10


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _runtime_relative(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeError("EXTERNALIZED_PATH_MISSING:" + field)
    value = value.replace("\\", "/")
    if not value.startswith(RUNTIME_PREFIX):
        raise RuntimeError("EXTERNALIZED_PATH_PREFIX_INVALID:" + field + ":" + value[:180])
    rel = value[len(RUNTIME_PREFIX):]
    p = PurePosixPath(rel)
    if p.is_absolute() or not rel or any(part in {"", ".."} for part in p.parts):
        raise RuntimeError("EXTERNALIZED_PATH_UNSAFE:" + field + ":" + value[:180])
    if re.match(r"^[A-Za-z]:", rel) or p.as_posix() in {"", ".", ".."}:
        raise RuntimeError("EXTERNALIZED_PATH_UNSAFE:" + field + ":" + value[:180])
    return p.as_posix()


def _safe_archive_member(value: str) -> str:
    value = value.replace("\\", "/")
    value = value.rstrip("/")
    if not value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise RuntimeError("EXTERNALIZED_ARCHIVE_ABSOLUTE_MEMBER:" + value[:180])
    p = PurePosixPath(value)
    if any(part in {"", ".."} for part in p.parts) or p.as_posix() in {"", ".", ".."}:
        raise RuntimeError("EXTERNALIZED_ARCHIVE_TRAVERSAL_MEMBER:" + value[:180])
    return p.as_posix()


def _tree_summary(root: Path) -> dict:
    root = Path(root).resolve()
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("EXTERNALIZED_TREE_ROOT_INVALID:" + str(root))
    rows = []
    for base, dirs, names in os.walk(root, topdown=True, followlinks=False):
        base_path = Path(base)
        kept_dirs = []
        for name in sorted(dirs):
            directory = base_path / name
            if directory.is_symlink() or not directory.resolve().is_relative_to(root):
                raise RuntimeError("EXTERNALIZED_TREE_SYMLINK_OR_ESCAPE:" + str(directory))
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in sorted(names):
            path = base_path / name
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise RuntimeError("EXTERNALIZED_TREE_SYMLINK_OR_ESCAPE:" + str(path))
            if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
                raise RuntimeError("EXTERNALIZED_TREE_NON_REGULAR:" + str(path))
            if name == MODULE_DESCRIPTOR_NAME:
                continue
            rows.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha_file(path),
            })
    rows.sort(key=lambda item: item["path"].encode("utf-8"))
    return {
        "file_count": len(rows),
        "bytes": sum(item["bytes"] for item in rows),
        "tree_sha256": sha_bytes(canonical_json(rows)),
    }


def _tree_rows(root: Path) -> list[dict]:
    root = Path(root).resolve()
    if not root.is_dir():
        raise RuntimeError("EXTERNALIZED_TREE_ROOT_INVALID:" + str(root))
    rows = []
    for base, dirs, names in os.walk(root, topdown=True, followlinks=False):
        base_path = Path(base)
        kept_dirs = []
        for name in sorted(dirs):
            directory = base_path / name
            if directory.is_symlink() or not directory.resolve().is_relative_to(root):
                raise RuntimeError("EXTERNALIZED_TREE_SYMLINK_OR_ESCAPE:" + str(directory))
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in sorted(names):
            path = base_path / name
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise RuntimeError("EXTERNALIZED_TREE_SYMLINK_OR_ESCAPE:" + str(path))
            if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
                raise RuntimeError("EXTERNALIZED_TREE_NON_REGULAR:" + str(path))
            if name == MODULE_DESCRIPTOR_NAME:
                continue
            rows.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha_file(path),
            })
    rows.sort(key=lambda item: item["path"].encode("utf-8"))
    return rows


def _tree_diff(source: Path, reconstructed: Path, sample_limit: int = 80) -> dict:
    source_rows = _tree_rows(source)
    reconstructed_rows = _tree_rows(reconstructed)
    a = {row["path"]: row for row in source_rows}
    b = {row["path"]: row for row in reconstructed_rows}
    source_only = [a[key] for key in sorted(a.keys() - b.keys(), key=lambda x: x.encode("utf-8"))]
    archive_only = [b[key] for key in sorted(b.keys() - a.keys(), key=lambda x: x.encode("utf-8"))]
    changed = [
        {"path": key, "source": a[key], "archive": b[key]}
        for key in sorted(a.keys() & b.keys(), key=lambda x: x.encode("utf-8"))
        if a[key]["bytes"] != b[key]["bytes"] or a[key]["sha256"] != b[key]["sha256"]
    ]
    return {
        "source_file_count": len(source_rows),
        "archive_file_count": len(reconstructed_rows),
        "source_bytes": sum(row["bytes"] for row in source_rows),
        "archive_bytes": sum(row["bytes"] for row in reconstructed_rows),
        "source_only_count": len(source_only),
        "archive_only_count": len(archive_only),
        "changed_count": len(changed),
        "source_only_sample": source_only[:sample_limit],
        "archive_only_sample": archive_only[:sample_limit],
        "changed_sample": changed[:sample_limit],
        "sample_limit": sample_limit,
    }


def placement_binding_sha256(placement: dict) -> str:
    # The placement gate/status fields are updated during every build. Bind only
    # the immutable externalized-asset identities and tree/container evidence.
    binding = {
        "schema": placement.get("schema"),
        "hard_cap_bytes": placement.get("hard_cap_bytes"),
        "assets": placement.get("assets"),
    }
    return sha_bytes(canonical_json(binding))


def _load_json(path: Path, label: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(label + "_NOT_REGULAR_FILE:" + str(path))
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(label + "_INVALID_JSON:" + type(exc).__name__) from exc
    if not isinstance(result, dict):
        raise RuntimeError(label + "_ROOT_NOT_OBJECT")
    return result


def _stage_container_from_externalized_source(
    root: Path, container_rel: str, expected_size: int, expected_sha: str, asset_id: str
) -> Path:
    """Copy a container from the governed staging store into the build runtime."""
    root = Path(root).resolve()
    rel = PurePosixPath(container_rel)
    destination = root / Path(*rel.parts)
    if destination.is_symlink():
        raise RuntimeError("EXTERNALIZED_CONTAINER_DESTINATION_SYMLINK:" + asset_id)
    if destination.exists():
        raise RuntimeError("EXTERNALIZED_CONTAINER_DESTINATION_COLLISION:" + asset_id)
    if not destination.resolve().is_relative_to(root):
        raise RuntimeError("EXTERNALIZED_CONTAINER_DESTINATION_ESCAPE:" + asset_id)

    basename = rel.name
    source = None
    for ancestor in (root, *root.parents):
        candidate = ancestor / "externalized-assets-staging" / "optimized-containers" / basename
        if candidate.is_symlink():
            raise RuntimeError("EXTERNALIZED_STAGING_CONTAINER_SYMLINK:" + asset_id)
        if candidate.is_file():
            source = candidate
            break
    if source is None:
        raise RuntimeError("EXTERNALIZED_STAGING_CONTAINER_MISSING:" + asset_id)

    source_size = source.stat().st_size
    source_sha = sha_file(source)
    if source_size != expected_size or source_sha != expected_sha:
        raise RuntimeError(
            "EXTERNALIZED_STAGING_CONTAINER_IDENTITY_MISMATCH:" + asset_id + ":" +
            json.dumps({"expected_bytes": expected_size, "actual_bytes": source_size,
                        "expected_sha256": expected_sha, "actual_sha256": source_sha}, sort_keys=True)
        )

    parent = destination.parent
    if not parent.resolve().is_relative_to(root):
        raise RuntimeError("EXTERNALIZED_CONTAINER_PARENT_ESCAPE:" + asset_id)
    cursor = root
    for part in parent.relative_to(root).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise RuntimeError("EXTERNALIZED_CONTAINER_PARENT_SYMLINK:" + asset_id)
        cursor.mkdir(exist_ok=True)

    temporary = destination.with_name(destination.name + ".verified-building")
    if temporary.exists() or temporary.is_symlink():
        raise RuntimeError("EXTERNALIZED_CONTAINER_TEMP_COLLISION:" + asset_id)
    try:
        shutil.copyfile(source, temporary)
        if temporary.stat().st_size != expected_size or sha_file(temporary) != expected_sha:
            raise RuntimeError("EXTERNALIZED_CONTAINER_COPY_REVERIFY_FAILED:" + asset_id)
        if destination.exists() or destination.is_symlink():
            raise RuntimeError("EXTERNALIZED_CONTAINER_DESTINATION_RACE:" + asset_id)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def _record_externalized_container_retention(placement: dict, contract: list[dict]) -> None:
    by_id = {item["id"]: item for item in contract}
    retained_paths = {item["container_relpath"] for item in contract}
    factory = placement.get("factory_reconciliation")
    if not isinstance(factory, dict):
        raise RuntimeError("FACTORY_RECONCILIATION_MISSING_FOR_CONTAINER_RETENTION")
    history = factory.get("archives")
    if not isinstance(history, list):
        raise RuntimeError("FACTORY_ARCHIVE_HISTORY_MISSING_FOR_CONTAINER_RETENTION")

    for row in history:
        if not isinstance(row, dict):
            raise RuntimeError("FACTORY_ARCHIVE_HISTORY_ROW_INVALID")
        if row.get("source_path") in retained_paths:
            row["archive_removed_from_runtime"] = False
            row["container_retained_in_distribution"] = True

    present_paths = {row.get("source_path") for row in history}
    for item in contract:
        rel = item["container_relpath"]
        if rel not in present_paths:
            history.append({
                "source_path": rel,
                "source_sha256": item["container_sha256"],
                "source_bytes": item["container_bytes"],
                "expanded_path": item["expanded_relpath"],
                "archive_removed_from_runtime": False,
                "container_retained_in_distribution": True,
                "rollback_path": "externalized-assets-staging/optimized-containers/" + Path(rel).name,
                "asset_id": item["id"],
            })
    history.sort(key=lambda row: (str(row.get("source_path", "")).encode("utf-8"), str(row.get("source_sha256", ""))))
    removed = [row for row in history if row.get("archive_removed_from_runtime") is True]
    retained = [row for row in history if row.get("archive_removed_from_runtime") is False]
    factory.update({
        "archive_count_materialized": len(history),
        "archive_count_removed": len(removed),
        "archive_count_retained": len(retained),
        "archive_bytes_removed": sum(int(row.get("source_bytes", 0)) for row in removed),
        "archive_bytes_retained": sum(int(row.get("source_bytes", 0)) for row in retained),
        "all_zip_7z_removed": len(retained) == 0,
        "all_unregistered_archives_removed": True,
        "externalized_container_retention": "PASS_HASH_AND_SIZE_VERIFIED",
        "retained_externalized_container_paths": sorted(retained_paths, key=lambda value: value.encode("utf-8")),
    })
    for asset in placement.get("assets", []):
        item = by_id.get(asset.get("id"))
        if item is None:
            continue
        nested = asset.get("factory_reconciliation")
        if not isinstance(nested, dict):
            nested = {}
        nested.update({
            "archive_removed_from_runtime": False,
            "container_retained_in_distribution": True,
            "container_source": "externalized-assets-staging/optimized-containers/" + Path(item["container_relpath"]).name,
            "container_sha256_verified": item["container_sha256"],
            "container_bytes_verified": item["container_bytes"],
        })
        asset["factory_reconciliation"] = nested
        asset["included_in_current_macrodown_manifest"] = True
        asset["placement"] = "MATERIALIZED_DIRECTORY_AND_HASH_PINNED_CONTAINER"


def _same_tree(left: dict, right: dict) -> bool:
    return (
        left.get("bytes") == right.get("bytes")
        and left.get("file_count") == right.get("file_count")
        and left.get("tree_sha256") == right.get("tree_sha256")
    )


def _extract_archive_for_rebuild(archive: Path, destination: Path) -> dict:
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError("EXTERNALIZED_REBUILD_EXTRACTION_TARGET_NOT_EMPTY")
    destination.mkdir(parents=True, exist_ok=True)
    binary = _seven_zip()
    _validate_archive_listing(binary, archive)
    test = subprocess.run(
        [binary, "t", "-bd", str(archive)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=900, check=False,
    )
    if test.returncode != 0:
        raise RuntimeError("EXTERNALIZED_REBUILD_7Z_TEST_FAILED:" + test.stdout[-700:])
    extracted = subprocess.run(
        [binary, "x", "-y", "-bd", "-o" + str(destination), str(archive)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=1800, check=False,
    )
    if extracted.returncode != 0:
        raise RuntimeError("EXTERNALIZED_REBUILD_7Z_EXTRACT_FAILED:" + extracted.stdout[-900:])
    if (destination / MODULE_DESCRIPTOR_NAME).exists() or (destination / MODULE_DESCRIPTOR_NAME).is_symlink():
        raise RuntimeError("EXTERNALIZED_REBUILD_RESERVED_DESCRIPTOR_IN_ARCHIVE")
    return _tree_summary(destination)


def _normalized_text_bytes(data: bytes):
    if b"\x00" in data:
        return None
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _copy_registered_tree_from_checkout_or_archive(
    source_root: Path,
    source_archive: Path,
    expected: dict,
    destination: Path,
    work_root: Path,
    asset_id: str,
) -> dict:
    source_root = Path(source_root).resolve()
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise RuntimeError("EXTERNALIZED_CANONICAL_TREE_DESTINATION_COLLISION:" + asset_id)
    destination.mkdir(parents=True)
    source_actual = _tree_summary(source_root)

    # The registered tree hash, not the compressed source blob, is the identity.
    # A matching checked-out tree can be repacked directly, excluding the
    # separately registered CAJITA_MODULE.json descriptor.
    source_rows = _tree_rows(source_root)
    if _same_tree(source_actual, expected):
        for row in source_rows:
            rel = PurePosixPath(row["path"])
            src = source_root / Path(*rel.parts)
            dst = destination / Path(*rel.parts)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            os.chmod(dst, stat.S_IMODE(src.stat().st_mode))
        actual = _tree_summary(destination)
        if not _same_tree(actual, expected):
            raise RuntimeError("EXTERNALIZED_CANONICAL_COPY_CHANGED:" + asset_id)
        return {"status": "PASS_CHECKOUT_TREE_HASH", "tree": actual}

    # Some committed text files have normalized LF line endings while the
    # registered pre-checkout tree retained CRLF. Recover original bytes only
    # where the archive's LF-normalized content exactly equals the checkout
    # bytes. All paths still come from the registered checkout tree; archive-
    # only files are never imported into the canonical candidate.
    archive_root = work_root / (asset_id + ".archive-source")
    archive_actual = _extract_archive_for_rebuild(source_archive, archive_root)
    archive_rows = {row["path"]: row for row in _tree_rows(archive_root)}
    for row in source_rows:
        rel = PurePosixPath(row["path"])
        src = source_root / Path(*rel.parts)
        data = src.read_bytes()
        archive_row = archive_rows.get(row["path"])
        if archive_row is not None:
            archived = archive_root / Path(*rel.parts)
            if archived.is_symlink() or not archived.is_file():
                raise RuntimeError("EXTERNALIZED_REBUILD_ARCHIVE_MEMBER_NOT_REGULAR:" + asset_id + ":" + row["path"])
            archived_bytes = archived.read_bytes()
            normalized = _normalized_text_bytes(archived_bytes)
            if normalized is not None and normalized == data:
                data = archived_bytes
        dst = destination / Path(*rel.parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        os.chmod(dst, stat.S_IMODE(src.stat().st_mode))

    candidate_actual = _tree_summary(destination)
    if not _same_tree(candidate_actual, expected):
        raise RuntimeError(
            "EXTERNALIZED_REGISTERED_TREE_RECOVERY_FAILED:" + asset_id + ":" +
            json.dumps({
                "expected": expected,
                "checkout_tree": source_actual,
                "source_archive_tree": archive_actual,
                "recovered_candidate": candidate_actual,
                "policy": "RESTORE_ARCHIVE_LINE_ENDINGS_ONLY_WHEN_LF_NORMALIZATION_MATCHES_CHECKOUT",
            }, sort_keys=True)
        )
    return {
        "status": "PASS_RECONSTRUCTED_REGISTERED_TREE_WITH_VERIFIED_LINE_ENDINGS",
        "tree": candidate_actual,
        "source_archive_tree": archive_actual,
    }


def _verify_archive_tree(archive: Path, expected: dict, work_root: Path, asset_id: str) -> dict:
    destination = work_root / (asset_id + ".roundtrip")
    actual = _extract_archive_for_rebuild(archive, destination)
    if not _same_tree(actual, expected):
        raise RuntimeError(
            "EXTERNALIZED_REPACK_ROUNDTRIP_MISMATCH:" + asset_id + ":" +
            json.dumps({"expected": expected, "actual": actual}, sort_keys=True)
        )
    shutil.rmtree(destination)
    return actual


def _pack_registered_tree(
    canonical_root: Path, output: Path, expected: dict, work_root: Path, asset_id: str
) -> dict:
    canonical_root = Path(canonical_root).resolve()
    output = Path(output)
    measured = _tree_summary(canonical_root)
    if not _same_tree(measured, expected):
        raise RuntimeError(
            "EXTERNALIZED_REPACK_SOURCE_TREE_NOT_REGISTERED:" + asset_id + ":" +
            json.dumps({"expected": expected, "actual": measured}, sort_keys=True)
        )
    if output.is_symlink():
        raise RuntimeError("EXTERNALIZED_REPACK_OUTPUT_SYMLINK:" + asset_id)
    output.parent.mkdir(parents=True, exist_ok=True)

    # A second prepare/build invocation in the same job reuses only a container
    # that independently reconstructs to the exact registered tree.
    if output.is_file():
        _verify_archive_tree(output, expected, work_root, asset_id)
        return {"bytes": output.stat().st_size, "sha256": sha_file(output), "reused": True}

    temporary = output.with_name(output.name + ".building")
    if temporary.exists() or temporary.is_symlink():
        raise RuntimeError("EXTERNALIZED_REPACK_TEMP_COLLISION:" + asset_id)
    binary = _seven_zip()
    packed = subprocess.run(
        [binary, "a", "-t7z", "-mx=9", "-mmt=1", "-mtc=off", "-mta=off", "-mtm=off", str(temporary), "."],
        cwd=str(canonical_root), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=1800, check=False,
    )
    if packed.returncode != 0 or not temporary.is_file():
        raise RuntimeError("EXTERNALIZED_REPACK_7Z_FAILED:" + asset_id + ":" + packed.stdout[-900:])
    try:
        _verify_archive_tree(temporary, expected, work_root, asset_id)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"bytes": output.stat().st_size, "sha256": sha_file(output), "reused": False}


def _source_contract(root: Path, canonical_work_root: Path) -> tuple[dict, dict, list[dict]]:
    root = Path(root).resolve()
    canonical_work_root = Path(canonical_work_root).resolve()
    placement_path = root / PLACEMENT_NAME
    registry_path = root / SOURCE_REGISTRY_NAME
    placement = _load_json(placement_path, "EXTERNALIZED_ASSET_PLACEMENT")
    source_registry = _load_json(registry_path, "SOURCE_MODULE_REGISTRY")
    assets = placement.get("assets")
    if not isinstance(assets, list) or len(assets) != EXPECTED_ASSET_COUNT:
        raise RuntimeError("EXTERNALIZED_ASSET_COUNT_INVALID")
    modules = source_registry.get("modules")
    if source_registry.get("schema") != "CAJITA_MODULE_REGISTRY/1.0" or not isinstance(modules, list):
        raise RuntimeError("SOURCE_MODULE_REGISTRY_SCHEMA_INVALID")

    seen_ids = set()
    seen_expanded = set()
    contract = []
    for asset in assets:
        if not isinstance(asset, dict):
            raise RuntimeError("EXTERNALIZED_ASSET_ROW_INVALID")
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or not asset_id or asset_id in seen_ids:
            raise RuntimeError("EXTERNALIZED_ASSET_ID_COLLISION_OR_MISSING")
        seen_ids.add(asset_id)

        expanded_rel = _runtime_relative(asset.get("expanded_path"), asset_id + ":expanded_path")
        container_meta = asset.get("compact_runtime_container")
        if not isinstance(container_meta, dict):
            raise RuntimeError("EXTERNALIZED_CONTAINER_METADATA_MISSING:" + asset_id)
        container_rel = _runtime_relative(container_meta.get("path"), asset_id + ":container_path")
        if expanded_rel in seen_expanded:
            raise RuntimeError("EXTERNALIZED_EXPANSION_PATH_COLLISION:" + expanded_rel)
        seen_expanded.add(expanded_rel)
        if expanded_rel == container_rel or expanded_rel.startswith(container_rel + "/") or container_rel.startswith(expanded_rel + "/"):
            raise RuntimeError("EXTERNALIZED_CONTAINER_TREE_OVERLAP:" + asset_id)
        if not container_rel.lower().endswith(".7z"):
            raise RuntimeError("EXTERNALIZED_CONTAINER_SUFFIX_INVALID:" + asset_id)
        if asset.get("placed_path") != container_meta.get("path"):
            raise RuntimeError("EXTERNALIZED_PLACED_PATH_MISMATCH:" + asset_id)

        container = root / Path(*PurePosixPath(container_rel).parts)
        expected_size = container_meta.get("size_bytes", asset.get("container_size_bytes"))
        expected_sha = container_meta.get("sha256", asset.get("container_sha256"))
        if isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size < 1:
            raise RuntimeError("EXTERNALIZED_CONTAINER_SIZE_INVALID:" + asset_id)
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise RuntimeError("EXTERNALIZED_CONTAINER_SHA256_INVALID:" + asset_id)
        if container.is_symlink():
            raise RuntimeError("EXTERNALIZED_CONTAINER_SYMLINK_REFUSED:" + asset_id)
        if not container.is_file():
            container = _stage_container_from_externalized_source(
                root, container_rel, expected_size, expected_sha, asset_id
            )
        actual_size = container.stat().st_size
        actual_sha = sha_file(container)
        if actual_size != expected_size or actual_sha != expected_sha:
            raise RuntimeError("EXTERNALIZED_CONTAINER_IDENTITY_MISMATCH:" + asset_id)
        if asset.get("container_size_bytes", expected_size) != expected_size or asset.get("container_sha256", expected_sha) != expected_sha:
            raise RuntimeError("EXTERNALIZED_CONTAINER_DUPLICATE_METADATA_MISMATCH:" + asset_id)

        expanded = root / Path(*PurePosixPath(expanded_rel).parts)
        if expanded.is_symlink() or not expanded.is_dir():
            raise RuntimeError("EXTERNALIZED_SOURCE_TREE_MISSING:" + asset_id)
        expected_tree = {
            "bytes": asset.get("expanded_bytes"),
            "file_count": asset.get("expanded_file_count"),
            "tree_sha256": asset.get("expanded_tree_sha256"),
        }
        if (
            isinstance(expected_tree["bytes"], bool) or not isinstance(expected_tree["bytes"], int) or expected_tree["bytes"] < 1
            or isinstance(expected_tree["file_count"], bool) or not isinstance(expected_tree["file_count"], int) or expected_tree["file_count"] < 1
            or not isinstance(expected_tree["tree_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", expected_tree["tree_sha256"])
        ):
            raise RuntimeError("EXTERNALIZED_EXPECTED_TREE_METADATA_INVALID:" + asset_id)
        canonical_tree = canonical_work_root / (asset_id + ".canonical")
        recovery = _copy_registered_tree_from_checkout_or_archive(
            expanded, container, expected_tree, canonical_tree, canonical_work_root, asset_id
        )
        measured = recovery["tree"]
        if not _same_tree(measured, expected_tree):
            raise RuntimeError("EXTERNALIZED_REGISTERED_TREE_CONTRACT_MISMATCH:" + asset_id)

        descriptor_path = expanded / MODULE_DESCRIPTOR_NAME
        descriptor_raw = descriptor_path.read_text(encoding="utf-8")
        descriptor_sha = sha_bytes(descriptor_raw.encode("utf-8"))
        expected_descriptor_sha = asset.get("factory_reconciliation", {}).get("module_manifest_sha256")
        if descriptor_sha != expected_descriptor_sha:
            raise RuntimeError("EXTERNALIZED_MODULE_DESCRIPTOR_HASH_MISMATCH:" + asset_id)
        descriptor = _load_json(descriptor_path, "EXTERNALIZED_MODULE_DESCRIPTOR")
        if descriptor.get("canonical_asset_id") != asset_id or descriptor.get("module_key") != expanded_rel:
            raise RuntimeError("EXTERNALIZED_MODULE_DESCRIPTOR_IDENTITY_MISMATCH:" + asset_id)
        descriptor_materialization = descriptor.get("materialization", {})
        for key, value in (("bytes", measured["bytes"]), ("file_count", measured["file_count"]), ("tree_sha256", measured["tree_sha256"])):
            if descriptor_materialization.get(key) != value:
                raise RuntimeError("EXTERNALIZED_DESCRIPTOR_TREE_METADATA_MISMATCH:" + asset_id + ":" + key)
        source_archives = descriptor.get("source_archives")
        if not isinstance(source_archives, list) or len(source_archives) != 1:
            raise RuntimeError("EXTERNALIZED_DESCRIPTOR_ARCHIVE_SET_INVALID:" + asset_id)
        descriptor_archive = source_archives[0]
        if descriptor_archive.get("path") != container_rel or descriptor_archive.get("sha256") != expected_sha or descriptor_archive.get("bytes") != expected_size:
            raise RuntimeError("EXTERNALIZED_DESCRIPTOR_ARCHIVE_BINDING_MISMATCH:" + asset_id)

        module_matches = [m for m in modules if isinstance(m, dict) and m.get("module_key") == expanded_rel and m.get("path") == expanded_rel]
        if len(module_matches) != 1:
            raise RuntimeError("EXTERNALIZED_SOURCE_REGISTRY_BINDING_COUNT:" + asset_id)
        source_module = module_matches[0]
        if source_module.get("tree_sha256") != measured["tree_sha256"] or source_module.get("bytes") != measured["bytes"] or source_module.get("file_count") != measured["file_count"]:
            raise RuntimeError("EXTERNALIZED_SOURCE_REGISTRY_TREE_MISMATCH:" + asset_id)
        if source_module.get("manifest_sha256") != descriptor_sha:
            raise RuntimeError("EXTERNALIZED_SOURCE_REGISTRY_DESCRIPTOR_MISMATCH:" + asset_id)

        contract.append({
            "id": asset_id,
            "expanded_relpath": expanded_rel,
            "source_container_path": container_meta.get("path"),
            "source_container_relpath": container_rel,
            "source_container_bytes": expected_size,
            "source_container_sha256": expected_sha,
            "container_relpath": RUNTIME_PREFIX + "CAJITA_DISTRIBUTION_ASSETS/" + asset_id + ".7z",
            "container_bytes": 0,
            "container_sha256": "",
            "container_rebuild_status": recovery["status"],
            "canonical_tree_path": str(canonical_tree),
            "expanded_bytes": measured["bytes"],
            "expanded_file_count": measured["file_count"],
            "expanded_tree_sha256": measured["tree_sha256"],
            "module_descriptor_sha256": descriptor_sha,
            "module_descriptor_raw": descriptor_raw,
            "module_descriptor": descriptor,
            "source_module_registry_row": source_module,
        })

    if seen_ids.__len__() != EXPECTED_ASSET_COUNT:
        raise RuntimeError("EXTERNALIZED_ASSET_ID_SET_INVALID")
    return placement, source_registry, contract


def prepare_distribution_registry(root: Path) -> list[dict]:
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix="cajita-registered-tree-repack-") as scratch_name:
        scratch = Path(scratch_name)
        placement, source_registry, contract = _source_contract(root, scratch)
        for item in contract:
            output_rel = _runtime_relative(item["container_relpath"], item["id"] + ":distribution_container_path")
            output_path = root / Path(*PurePosixPath(output_rel).parts)
            expected = {
                "bytes": item["expanded_bytes"],
                "file_count": item["expanded_file_count"],
                "tree_sha256": item["expanded_tree_sha256"],
            }
            packed = _pack_canonical_tree(
                Path(item["canonical_tree_path"]), output_path, expected, scratch, item["id"]
            )
            item["container_bytes"] = packed["bytes"]
            item["container_sha256"] = packed["sha256"]
            item["container_rebuild_status"] = (
                "PASS_REPACKAGED_AND_ROUNDTRIP_VERIFIED_REUSED"
                if packed.get("reused") else "PASS_REPACKAGED_AND_ROUNDTRIP_VERIFIED"
            )
            item.pop("canonical_tree_path", None)

    source_registry_path = root / SOURCE_REGISTRY_NAME
    placement_path = root / PLACEMENT_NAME
    by_asset_id = {item["id"]: item for item in contract}
    placement["distribution_repackaging"] = {
        "schema": "CAJITA_DISTRIBUTION_REPACKAGING/1.0",
        "policy": "REBUILD_FROM_REGISTERED_EXPANDED_TREE_HASH_WITH_EXACT_ROUNDTRIP",
        "source_containers_preserved_in_staging": True,
        "source_container_blobs_embedded_in_distribution": False,
        "derived_distribution_container_count": len(contract),
        "all_registered_tree_hashes_verified_before_packaging": True,
        "all_derived_container_roundtrips_verified": all(
            item["container_rebuild_status"].startswith("PASS_REPACKAGED_AND_ROUNDTRIP_VERIFIED")
            for item in contract
        ),
        "certification": "NOT_GRANTED",
    }
    for asset in placement.get("assets", []):
        item = by_asset_id.get(asset.get("id"))
        if item is None:
            continue
        asset["distribution_repackaging"] = {
            "source_container_path": item["source_container_path"],
            "source_container_bytes": item["source_container_bytes"],
            "source_container_sha256": item["source_container_sha256"],
            "distribution_container_path": item["container_relpath"],
            "distribution_container_bytes": item["container_bytes"],
            "distribution_container_sha256": item["container_sha256"],
            "source_tree_bytes": item["expanded_bytes"],
            "source_tree_file_count": item["expanded_file_count"],
            "source_tree_sha256": item["expanded_tree_sha256"],
            "status": item["container_rebuild_status"],
            "certification": "NOT_GRANTED",
        }
    placement_output = (json.dumps(placement, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    placement_temp = placement_path.with_name(placement_path.name + ".building")
    if placement_temp.is_symlink():
        raise RuntimeError("PLACEMENT_TEMP_SYMLINK_REFUSED")
    placement_temp.write_bytes(placement_output)
    os.replace(placement_temp, placement_path)
    placement_sha = placement_binding_sha256(placement)
    source_registry_sha = sha_file(source_registry_path)
    externalized_paths = {item["expanded_relpath"] for item in contract}

    source_modules = source_registry.get("modules", [])
    extracted_modules = []
    externalized_modules = []
    by_key = {item["expanded_relpath"]: item for item in contract}
    for row in source_modules:
        key = row.get("module_key") if isinstance(row, dict) else None
        if key not in by_key:
            extracted_modules.append(row)
            continue
        item = by_key[key]
        if item["source_module_registry_row"] != row:
            raise RuntimeError("EXTERNALIZED_REGISTRY_ROW_CHANGED_DURING_BUILD:" + str(key))
        distribution_row = dict(row)
        distribution_row.update({
            "state": "EXTERNALIZED_COMPRESSED_CONTAINER_NOT_MATERIALIZED",
            "container_path": item["container_relpath"],
            "container_bytes": item["container_bytes"],
            "container_sha256": item["container_sha256"],
            "source_container_path": item["source_container_path"],
            "source_container_bytes": item["source_container_bytes"],
            "source_container_sha256": item["source_container_sha256"],
            "container_rebuilt_from_registered_tree": True,
            "container_rebuild_status": item["container_rebuild_status"],
            "materialization_required": True,
            "materialization": {
                "status": "PACKED_NOT_EXPANDED",
                "bytes": item["expanded_bytes"],
                "file_count": item["expanded_file_count"],
                "tree_sha256": item["expanded_tree_sha256"],
            },
            "module_descriptor_raw": item["module_descriptor_raw"],
            "module_descriptor_sha256": item["module_descriptor_sha256"],
            "consumer_adapter": "NOT_PROVEN_BY_EXTRACTION",
            "execution": "NOT_GRANTED_WITHOUT_ADAPTER_AND_SMOKE",
            "certification": "NOT_GRANTED",
        })
        externalized_modules.append(distribution_row)

    if len(externalized_modules) != EXPECTED_ASSET_COUNT or len(extracted_modules) + len(externalized_modules) != len(source_modules):
        raise RuntimeError("DISTRIBUTION_REGISTRY_MODULE_PARTITION_INVALID")
    externalized_modules.sort(key=lambda row: row["module_key"].encode("utf-8"))
    extracted_modules.sort(key=lambda row: row["module_key"].encode("utf-8"))

    result = dict(source_registry)
    result["source_module_registry_sha256"] = source_registry_sha
    result["externalized_asset_placement_sha256"] = placement_sha
    result["source_materialized_module_count"] = len(source_modules)
    result["materialized_module_count"] = len(extracted_modules)
    result["modules"] = extracted_modules
    result["externalized_module_count"] = len(externalized_modules)
    result["externalized_modules"] = externalized_modules
    result["distribution_profile"] = {
        "policy": "REBUILD_CONTAINER_FROM_REGISTERED_TREE_HASH_AND_RECONSTRUCT_ON_DEMAND",
        "source_only_registry_excluded": SOURCE_REGISTRY_NAME,
        "expanded_tree_file_bytes_embedded": False,
        "compressed_container_bytes_embedded": True,
        "materialization_helper": "cajita_externalized_asset_loader.py",
        "consumer_adapter_validation": "NOT_ESTABLISHED",
        "native_smoke_validation": "REQUIRED",
        "certification": "NOT_GRANTED",
    }

    # The distribution's route file must point to the distribution registry,
    # while the source route file continues to point to the full factory registry.
    source_routing_path = root / "command_subdomain_routing.json"
    source_routing = _load_json(source_routing_path, "SOURCE_ROUTING_CATALOG")
    source_materialization = source_routing.get("materialization")
    if not isinstance(source_materialization, dict):
        raise RuntimeError("SOURCE_ROUTING_MATERIALIZATION_BLOCK_MISSING")
    distribution_routing = dict(source_routing)
    distribution_routing["source_materialization_history"] = source_materialization
    routing_materialization = dict(source_materialization)
    routing_materialization.update({
        "module_registry": DISTRIBUTION_REGISTRY_NAME,
        "distribution_module_registry": DISTRIBUTION_REGISTRY_NAME,
        "module_count": len(source_modules),
        "materialized_module_count": len(extracted_modules),
        "externalized_asset_module_count": len(externalized_modules),
        "externalized_container_count": len(externalized_modules),
        "archive_policy": "HASH_PINNED_COMPRESSED_CONTAINERS_WITH_EXPLICIT_ON_DEMAND_RECONSTRUCTION",
        "reconstruction_helper": "cajita_externalized_asset_loader.py",
        "native_execution_smoke": "REQUIRED",
        "certification": "NOT_GRANTED",
    })
    distribution_routing["materialization"] = routing_materialization
    for support in distribution_routing.get("support_assets", []):
        if not isinstance(support, dict):
            continue
        candidates = {support.get("id"), support.get("asset_id"), support.get("canonical_asset_id"),
                      support.get("relative_path"), support.get("materialized_path"), support.get("source_archive_path")}
        for item in contract:
            if item["id"] in candidates or item["expanded_relpath"] in candidates or item["container_relpath"] in candidates:
                support.update({
                    "container_path": item["container_relpath"],
                    "container_sha256": item["container_sha256"],
                    "container_bytes": item["container_bytes"],
                    "source_container_path": item["source_container_path"],
                    "source_container_sha256": item["source_container_sha256"],
                    "source_container_bytes": item["source_container_bytes"],
                    "container_rebuilt_from_registered_tree": True,
                    "container_retained_in_distribution": True,
                    "archive_removed_from_runtime": False,
                    "activation_status": "MATERIALIZED_NOT_FUNCTIONALLY_VALIDATED",
                })
                break
    distribution_routing["externalized_assets"] = [
        {"id": item["id"], "container_path": item["container_relpath"],
         "container_sha256": item["container_sha256"], "container_bytes": item["container_bytes"],
         "source_container_path": item["source_container_path"],
         "source_container_sha256": item["source_container_sha256"],
         "source_container_bytes": item["source_container_bytes"],
         "container_rebuild_status": item["container_rebuild_status"],
         "expanded_path": item["expanded_relpath"], "expanded_tree_sha256": item["expanded_tree_sha256"],
         "materialization": "ON_DEMAND", "consumer_adapter": "NOT_ESTABLISHED",
         "native_smoke": "REQUIRED", "certification": "NOT_GRANTED"}
        for item in contract
    ]
    routing_path = root / "CAJITA_DISTRIBUTION_ROUTING.json"
    if routing_path.is_symlink():
        raise RuntimeError("DISTRIBUTION_ROUTING_SYMLINK_REFUSED")
    routing_output = (json.dumps(distribution_routing, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    current_routing = routing_path.read_bytes() if routing_path.is_file() else None
    if current_routing != routing_output:
        routing_temp = routing_path.with_name(routing_path.name + ".building")
        if routing_temp.is_symlink():
            raise RuntimeError("DISTRIBUTION_ROUTING_TEMP_SYMLINK_REFUSED")
        routing_temp.write_bytes(routing_output)
        os.replace(routing_temp, routing_path)
    result["distribution_routing_sha256"] = sha_bytes(routing_output)

    output_path = root / DISTRIBUTION_REGISTRY_NAME
    if output_path.is_symlink():
        raise RuntimeError("DISTRIBUTION_REGISTRY_SYMLINK_REFUSED")
    output = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    current = output_path.read_bytes() if output_path.is_file() else None
    if current != output:
        temporary = output_path.with_name(output_path.name + ".building")
        if temporary.is_symlink():
            raise RuntimeError("DISTRIBUTION_REGISTRY_TEMP_SYMLINK_REFUSED")
        temporary.write_bytes(output)
        os.replace(temporary, output_path)
    return contract


def distribution_contract(root: Path) -> list[dict]:
    root = Path(root).resolve()
    placement_path = root / PLACEMENT_NAME
    registry_path = root / DISTRIBUTION_REGISTRY_NAME
    placement = _load_json(placement_path, "EXTERNALIZED_ASSET_PLACEMENT")
    registry = _load_json(registry_path, "DISTRIBUTION_MODULE_REGISTRY")
    if registry.get("schema") != "CAJITA_MODULE_REGISTRY/1.0":
        raise RuntimeError("DISTRIBUTION_MODULE_REGISTRY_SCHEMA_INVALID")
    if registry.get("externalized_asset_placement_sha256") != placement_binding_sha256(placement):
        raise RuntimeError("DISTRIBUTION_PLACEMENT_REGISTRY_HASH_MISMATCH")
    rows = registry.get("externalized_modules")
    routing_path = root / "CAJITA_DISTRIBUTION_ROUTING.json"
    routing = _load_json(routing_path, "DISTRIBUTION_ROUTING_CATALOG")
    if registry.get("distribution_routing_sha256") != sha_file(routing_path):
        raise RuntimeError("DISTRIBUTION_ROUTING_HASH_MISMATCH")
    if routing.get("materialization", {}).get("module_registry") != DISTRIBUTION_REGISTRY_NAME:
        raise RuntimeError("DISTRIBUTION_ROUTING_REGISTRY_TARGET_MISMATCH")
    assets = placement.get("assets")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ASSET_COUNT or not isinstance(assets, list) or len(assets) != EXPECTED_ASSET_COUNT:
        raise RuntimeError("DISTRIBUTION_EXTERNALIZED_ASSET_SET_INVALID")
    by_id = {row.get("canonical_asset_id"): row for row in rows if isinstance(row, dict)}
    if len(by_id) != EXPECTED_ASSET_COUNT:
        raise RuntimeError("DISTRIBUTION_EXTERNALIZED_ASSET_ID_COLLISION")
    output = []
    for asset in assets:
        asset_id = asset.get("id")
        row = by_id.get(asset_id)
        if row is None:
            raise RuntimeError("DISTRIBUTION_EXTERNALIZED_MODULE_MISSING:" + str(asset_id))
        expanded_rel = _runtime_relative(asset.get("expanded_path"), str(asset_id) + ":expanded_path")
        source_container = asset.get("compact_runtime_container", {})
        source_container_rel = _runtime_relative(source_container.get("path"), str(asset_id) + ":source_container_path")
        distribution_meta = asset.get("distribution_repackaging")
        if not isinstance(distribution_meta, dict):
            raise RuntimeError("DISTRIBUTION_REPACKAGING_EVIDENCE_MISSING:" + str(asset_id))
        container_rel = _runtime_relative(row.get("container_path"), str(asset_id) + ":distribution_container_path")
        if row.get("path") != expanded_rel or row.get("module_key") != expanded_rel:
            raise RuntimeError("DISTRIBUTION_MODULE_PATH_MISMATCH:" + str(asset_id))
        if (
            row.get("source_container_path") != source_container.get("path")
            or row.get("source_container_sha256") != source_container.get("sha256")
            or row.get("source_container_bytes") != source_container.get("size_bytes")
            or distribution_meta.get("source_container_path") != source_container.get("path")
            or distribution_meta.get("source_container_sha256") != source_container.get("sha256")
            or distribution_meta.get("source_container_bytes") != source_container.get("size_bytes")
            or distribution_meta.get("distribution_container_path") != row.get("container_path")
            or distribution_meta.get("distribution_container_sha256") != row.get("container_sha256")
            or distribution_meta.get("distribution_container_bytes") != row.get("container_bytes")
            or row.get("container_rebuilt_from_registered_tree") is not True
            or not str(row.get("container_rebuild_status", "")).startswith("PASS_REPACKAGED_AND_ROUNDTRIP_VERIFIED")
        ):
            raise RuntimeError("DISTRIBUTION_CONTAINER_BINDING_MISMATCH:" + str(asset_id))
        if row.get("tree_sha256") != asset.get("expanded_tree_sha256") or row.get("bytes") != asset.get("expanded_bytes") or row.get("file_count") != asset.get("expanded_file_count"):
            raise RuntimeError("DISTRIBUTION_TREE_BINDING_MISMATCH:" + str(asset_id))
        descriptor_raw = row.get("module_descriptor_raw")
        descriptor_sha = row.get("module_descriptor_sha256")
        if not isinstance(descriptor_raw, str) or sha_bytes(descriptor_raw.encode("utf-8")) != descriptor_sha:
            raise RuntimeError("DISTRIBUTION_DESCRIPTOR_RAW_HASH_MISMATCH:" + str(asset_id))
        descriptor = json.loads(descriptor_raw)
        if descriptor.get("canonical_asset_id") != asset_id or descriptor.get("module_key") != expanded_rel:
            raise RuntimeError("DISTRIBUTION_DESCRIPTOR_IDENTITY_MISMATCH:" + str(asset_id))
        container_path = root / Path(*PurePosixPath(container_rel).parts)
        if container_path.is_symlink() or not container_path.is_file():
            raise RuntimeError("DISTRIBUTION_CONTAINER_MISSING:" + str(asset_id))
        actual_bytes = container_path.stat().st_size
        actual_sha = sha_file(container_path)
        if actual_bytes != row.get("container_bytes") or actual_sha != row.get("container_sha256"):
            raise RuntimeError("DISTRIBUTION_CONTAINER_IDENTITY_MISMATCH:" + str(asset_id))
        output.append({
            "id": asset_id,
            "expanded_relpath": expanded_rel,
            "source_container_relpath": source_container_rel,
            "source_container_bytes": source_container.get("size_bytes"),
            "source_container_sha256": source_container.get("sha256"),
            "container_relpath": container_rel,
            "container_bytes": actual_bytes,
            "container_sha256": actual_sha,
            "container_rebuild_status": row.get("container_rebuild_status"),
            "expanded_bytes": row["bytes"],
            "expanded_file_count": row["file_count"],
            "expanded_tree_sha256": row["tree_sha256"],
            "module_descriptor_sha256": descriptor_sha,
            "module_descriptor_raw": descriptor_raw,
            "module_descriptor": descriptor,
        })
    return output


def _seven_zip() -> str:
    binary = shutil.which("7z") or shutil.which("7zz")
    if not binary:
        raise RuntimeError("SEVEN_ZIP_EXECUTABLE_MISSING")
    return binary


def _validate_archive_listing(binary: str, archive: Path) -> None:
    listing = subprocess.run([binary, "l", "-slt", str(archive)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=False)
    if listing.returncode != 0:
        raise RuntimeError("EXTERNALIZED_7Z_LIST_FAILED:" + listing.stdout[-500:])
    entries = [line[7:] for line in listing.stdout.splitlines() if line.startswith("Path = ")]
    if len(entries) < 2:
        raise RuntimeError("EXTERNALIZED_7Z_HAS_NO_MEMBERS:" + archive.name)
    # 7z -slt prints the archive path first, followed by member paths.
    for entry in entries[1:]:
        _safe_archive_member(entry)
    for block in listing.stdout.split("\n\n")[1:]:
        fields = {}
        for line in block.splitlines():
            if " = " in line:
                key, value = line.split(" = ", 1)
                fields[key.strip()] = value.strip()
        mode = fields.get("Mode", "")
        attributes = fields.get("Attributes", "")
        if mode.startswith("l") or fields.get("Symbolic Link") or fields.get("Hard Link"):
            raise RuntimeError("EXTERNALIZED_7Z_LINK_MEMBER_REFUSED:" + str(fields.get("Path", "")))
        if attributes.lower().startswith("l"):
            raise RuntimeError("EXTERNALIZED_7Z_LINK_ATTRIBUTE_REFUSED:" + str(fields.get("Path", "")))


def _extract_raw_tree(root: Path, item: dict, destination: Path) -> dict:
    root = Path(root).resolve()
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError("EXTERNALIZED_EXTRACTION_TARGET_NOT_EMPTY")
    destination.mkdir(parents=True, exist_ok=True)
    archive = root / Path(*PurePosixPath(item["container_relpath"]).parts)
    binary = _seven_zip()
    _validate_archive_listing(binary, archive)
    test = subprocess.run([binary, "t", "-bd", str(archive)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900, check=False)
    if test.returncode != 0:
        raise RuntimeError("EXTERNALIZED_7Z_TEST_FAILED:" + test.stdout[-500:])
    extracted = subprocess.run([binary, "x", "-y", "-bd", "-o" + str(destination), str(archive)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800, check=False)
    if extracted.returncode != 0:
        raise RuntimeError("EXTERNALIZED_7Z_EXTRACT_FAILED:" + extracted.stdout[-700:])
    if (destination / MODULE_DESCRIPTOR_NAME).exists() or (destination / MODULE_DESCRIPTOR_NAME).is_symlink():
        raise RuntimeError("EXTERNALIZED_ARCHIVE_CONTAINS_RESERVED_MODULE_DESCRIPTOR")
    actual = _tree_summary(destination)
    expected = {
        "bytes": item["expanded_bytes"],
        "file_count": item["expanded_file_count"],
        "tree_sha256": item["expanded_tree_sha256"],
    }
    if actual != {"bytes": expected["bytes"], "file_count": expected["file_count"], "tree_sha256": expected["tree_sha256"]}:
        detail = {"expected": expected, "archive_reconstructed": actual}
        try:
            source_root = root / Path(*PurePosixPath(item["expanded_relpath"]).parts)
            detail["working_copy_actual"] = _tree_summary(source_root)
            detail["working_copy_vs_archive"] = _tree_diff(source_root, destination)
        except Exception as exc:
            detail["comparison_error"] = type(exc).__name__ + ":" + str(exc)[:300]
        raise RuntimeError("EXTERNALIZED_ARCHIVE_RECONSTRUCTION_MISMATCH:" + item["id"] + ":" + json.dumps(detail, sort_keys=True))
    return actual


def verify_all_archives(root: Path) -> dict:
    root = Path(root).resolve()
    contract = distribution_contract(root)
    results = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="cajita-externalized-verify-") as temp_name:
        temporary_root = Path(temp_name)
        for item in contract:
            destination = temporary_root / item["id"]
            try:
                actual = _extract_raw_tree(root, item, destination)
                results.append({"id": item["id"], "status": "PASS", **actual, "container_bytes": item["container_bytes"], "container_sha256": item["container_sha256"]})
            except Exception as exc:
                # Continue independent asset checks to collect the full failure set,
                # but never turn any individual failure into a pass.
                failures.append({
                    "id": item["id"],
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                    "reason": str(exc)[:12000],
                    "container_bytes": item["container_bytes"],
                    "container_sha256": item["container_sha256"],
                })
    return {
        "schema": "CAJITA_EXTERNALIZED_ASSET_RECONSTRUCTION/1.0",
        "status": "PASS_CONTAINER_RECONSTRUCTION_ONLY" if not failures and len(results) == len(contract) else "FAIL_CONTAINER_RECONSTRUCTION",
        "asset_count": len(contract),
        "passed_count": len(results),
        "failed_count": len(failures),
        "assets": results,
        "failures": failures,
        "consumer_adapter_validation": "NOT_ESTABLISHED",
        "native_smoke_validation": "REQUIRED",
        "certification": "NOT_GRANTED",
    }


def materialize_asset(root: Path, asset_id: str) -> dict:
    root = Path(root).resolve()
    contract = distribution_contract(root)
    matches = [item for item in contract if item["id"] == asset_id]
    if len(matches) != 1:
        raise RuntimeError("EXTERNALIZED_ASSET_ID_NOT_REGISTERED:" + str(asset_id))
    item = matches[0]
    target = root / Path(*PurePosixPath(item["expanded_relpath"]).parts)
    if not target.resolve().is_relative_to(root) or target.is_symlink():
        raise RuntimeError("EXTERNALIZED_MATERIALIZATION_PATH_ESCAPE_OR_SYMLINK")
    if target.exists():
        if not target.is_dir():
            raise RuntimeError("EXTERNALIZED_MATERIALIZATION_TARGET_NOT_DIRECTORY")
        current = _tree_summary(target)
        descriptor_path = target / MODULE_DESCRIPTOR_NAME
        descriptor_hash = sha_file(descriptor_path) if descriptor_path.is_file() and not descriptor_path.is_symlink() else None
        expected = {"bytes": item["expanded_bytes"], "file_count": item["expanded_file_count"], "tree_sha256": item["expanded_tree_sha256"]}
        if current != expected or descriptor_hash != item["module_descriptor_sha256"]:
            raise RuntimeError("EXTERNALIZED_EXISTING_TREE_MISMATCH_FAIL_CLOSED:" + asset_id)
        return {"id": asset_id, "status": "ALREADY_MATERIALIZED_EXACT", **current, "certification": "NOT_GRANTED"}

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".cajita-materializing-" + asset_id + "-", dir=str(target.parent)))
    try:
        actual = _extract_raw_tree(root, item, temporary)
        descriptor_path = temporary / MODULE_DESCRIPTOR_NAME
        descriptor_raw = item["module_descriptor_raw"].encode("utf-8")
        descriptor_path.write_bytes(descriptor_raw)
        if sha_file(descriptor_path) != item["module_descriptor_sha256"]:
            raise RuntimeError("EXTERNALIZED_DESCRIPTOR_RESTORE_HASH_MISMATCH:" + asset_id)
        try:
            os.replace(temporary, target)
        except OSError as exc:
            raise RuntimeError("EXTERNALIZED_MATERIALIZATION_ATOMIC_COMMIT_FAILED:" + asset_id + ":" + type(exc).__name__) from exc
        return {"id": asset_id, "status": "PASS_MATERIALIZED_FROM_HASH_PINNED_CONTAINER", **actual, "descriptor_sha256": item["module_descriptor_sha256"], "certification": "NOT_GRANTED"}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify-all", "materialize"))
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--asset-id")
    args = parser.parse_args()
    try:
        if args.command == "verify-all":
            if args.asset_id:
                parser.error("--asset-id is valid only for materialize")
            result = verify_all_archives(Path(args.root))
        else:
            if not args.asset_id:
                parser.error("materialize requires --asset-id")
            result = materialize_asset(Path(args.root), args.asset_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "schema": "CAJITA_EXTERNALIZED_ASSET_RECONSTRUCTION/1.0",
            "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "reason": str(exc)[:1200],
            "certification": "NOT_GRANTED",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
