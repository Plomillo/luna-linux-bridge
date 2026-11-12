#!/usr/bin/env python3
"""Create a disposable, hash-bound JASP fixture copy with its stored seed enabled.

JASP embeds R through RInside using --vanilla; R startup profiles are therefore
not a valid control point for this lane. The fixture's native setSeed/seed
options are the supported deterministic control. The source .jasp archive is
never modified; exactly one matching option in the disposable copy may change.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import stat
import zipfile


SCHEMA = "LUNITA_JASP_DETERMINISTIC_FIXTURE/1.0"
EXPECTED_SEED = 1
ACTIVE_ANALYSES_MEMBER = "analyses.json"


class FixtureError(RuntimeError):
    pass


def sha_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pointer(parts: tuple[str, ...]) -> str:
    def esc(value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")
    return "/" + "/".join(esc(part) for part in parts)


def _walk_seed_options(value, path=()):
    if isinstance(value, dict):
        if (
            isinstance(value.get("setSeed"), bool)
            and value.get("setSeed") is False
            and isinstance(value.get("seed"), (int, float))
            and not isinstance(value.get("seed"), bool)
            and value.get("seed") == EXPECTED_SEED
        ):
            yield path, value
        for key, child in value.items():
            yield from _walk_seed_options(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_seed_options(child, path + (str(index),))


def _safe_members(archive: zipfile.ZipFile):
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise FixtureError("JASP archive contains duplicate member names")
    for info in infos:
        path = pathlib.PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
            raise FixtureError(f"Unsafe JASP archive member: {info.filename!r}")
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise FixtureError(f"Symlink member is not allowed in JASP fixture: {info.filename!r}")
    return infos


def inspect_seed_option(source: pathlib.Path) -> dict:
    """Inspect active analysis options, not serialized result/output JSON.

    JASP archives may persist copies of seed values in resources/.../jaspResults.json.
    Those are saved outputs, not the active analysis configuration, and must remain
    byte-for-byte unchanged when creating a deterministic disposable fixture copy.
    """
    if source.is_symlink() or not source.is_file():
        raise FixtureError("Packaged Death Penalty fixture is missing or is a symlink")
    matches = []
    with zipfile.ZipFile(source, "r") as archive:
        infos = _safe_members(archive)
        active_infos = [info for info in infos if info.filename == ACTIVE_ANALYSES_MEMBER]
        if len(active_infos) != 1:
            raise FixtureError(
                f"Expected exactly one {ACTIVE_ANALYSES_MEMBER!r} active-configuration member; "
                f"found {len(active_infos)}"
            )
        info = active_infos[0]
        if info.is_dir() or info.file_size > 8 * 1024 * 1024:
            raise FixtureError("Active JASP analyses.json is a directory or exceeds the size limit")
        try:
            document = json.loads(archive.read(info).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FixtureError("Active JASP analyses.json is not valid UTF-8 JSON") from exc
        if not isinstance(document, dict) or not isinstance(document.get("analyses"), list):
            raise FixtureError("Active JASP analyses.json has no analyses list")
        analyses = document["analyses"]
        if not analyses:
            raise FixtureError("Active JASP analyses.json contains no analyses")
        for pointer_parts, option in _walk_seed_options(analyses):
            pointer_parts = tuple(pointer_parts)
            analysis_index = int(pointer_parts[0]) if pointer_parts and str(pointer_parts[0]).isdigit() else None
            analysis = analyses[analysis_index] if analysis_index is not None else None
            dynamic = analysis.get("dynamicModule", {}) if isinstance(analysis, dict) else {}
            matches.append({
                "archive_member": ACTIVE_ANALYSES_MEMBER,
                "json_pointer": _pointer(("analyses",) + pointer_parts),
                "analysis_index": analysis_index,
                "analysis_id": analysis.get("id") if isinstance(analysis, dict) else None,
                "analysis_name": analysis.get("name") if isinstance(analysis, dict) else None,
                "module_name": dynamic.get("moduleName") if isinstance(dynamic, dict) else None,
                "setSeed": option["setSeed"],
                "seed": option["seed"],
            })
    return {
        "archive_member_count": len(infos),
        "active_configuration_member": ACTIVE_ANALYSES_MEMBER,
        "active_analysis_count": len(analyses),
        "seed_option_match_count": len(matches),
        "matches": matches,
    }


def _replace_pointer(document, pointer: str) -> None:
    if not pointer.startswith("/"):
        raise FixtureError("Invalid JSON pointer")
    parts = [
        part.replace("~1", "/").replace("~0", "~")
        for part in pointer[1:].split("/")
    ]
    node = document
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    key = parts[-1]
    if isinstance(node, list):
        raise FixtureError("Seed option pointer resolved to a list, not an object")
    target = node.get(key)
    if not isinstance(target, dict):
        raise FixtureError("Seed option pointer no longer resolves to an object")
    if target.get("setSeed") is not False or target.get("seed") != EXPECTED_SEED:
        raise FixtureError("Seed option values changed after inspection")
    target["setSeed"] = True


def prepare_deterministic_fixture(
    source: pathlib.Path,
    destination: pathlib.Path,
    receipt_path: pathlib.Path,
    expected_source_sha256: str,
) -> dict:
    source = pathlib.Path(source)
    destination = pathlib.Path(destination)
    receipt_path = pathlib.Path(receipt_path)
    if destination.exists() or destination.is_symlink():
        raise FixtureError("Refusing to overwrite an existing deterministic fixture copy")
    if receipt_path.exists() or receipt_path.is_symlink():
        raise FixtureError("Refusing to overwrite an existing deterministic fixture receipt")
    source_before = sha_file(source)
    if source_before != expected_source_sha256:
        raise FixtureError("Packaged source fixture SHA-256 does not match its immutable pin")

    inspection = inspect_seed_option(source)
    if inspection["seed_option_match_count"] != 1:
        raise FixtureError(
            "Expected exactly one active Death Penalty setSeed=false, seed=1 option "
            f"in {ACTIVE_ANALYSES_MEMBER}; found {inspection['seed_option_match_count']}"
        )
    match = inspection["matches"][0]
    changed_member = match["archive_member"]
    changed_pointer = match["json_pointer"]
    if changed_member != ACTIVE_ANALYSES_MEMBER:
        raise FixtureError("Refusing to change a non-active JASP result/archive member")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(destination, "x") as dst:
        dst.comment = src.comment
        changed_count = 0
        for info in _safe_members(src):
            payload = src.read(info)
            if info.filename == changed_member:
                document = json.loads(payload.decode("utf-8"))
                _replace_pointer(document, changed_pointer)
                payload = (json.dumps(
                    document, ensure_ascii=False, separators=(",", ":")
                )).encode("utf-8")
                changed_count += 1
            dst.writestr(info, payload)
    if changed_count != 1:
        destination.unlink(missing_ok=True)
        raise FixtureError(f"Expected one changed archive member; wrote {changed_count}")

    source_after = sha_file(source)
    clone_sha = sha_file(destination)
    if source_after != source_before or clone_sha == source_before:
        destination.unlink(missing_ok=True)
        raise FixtureError("Source preservation or deterministic-copy identity check failed")

    verified = inspect_seed_option(destination)
    if verified["active_configuration_member"] != ACTIVE_ANALYSES_MEMBER or verified["seed_option_match_count"] != 0:
        destination.unlink(missing_ok=True)
        raise FixtureError("Deterministic copy still contains the original active false/1 seed option")
    unchanged_member_count = 0
    with zipfile.ZipFile(source, "r") as original, zipfile.ZipFile(destination, "r") as seeded:
        original_names = [info.filename for info in original.infolist()]
        seeded_names = [info.filename for info in seeded.infolist()]
        if original_names != seeded_names:
            destination.unlink(missing_ok=True)
            raise FixtureError("Deterministic copy changed JASP archive member identity or order")
        for name in original_names:
            if name == changed_member:
                continue
            if original.read(name) != seeded.read(name):
                destination.unlink(missing_ok=True)
                raise FixtureError(f"Non-active JASP archive member changed: {name}")
            unchanged_member_count += 1
    with zipfile.ZipFile(destination, "r") as archive:
        document = json.loads(archive.read(changed_member).decode("utf-8"))
    # Verify exact selected pointer in the output, not just absence of the old state.
    parts = [
        part.replace("~1", "/").replace("~0", "~")
        for part in changed_pointer[1:].split("/")
    ]
    selected = document
    for part in parts:
        selected = selected[int(part)] if isinstance(selected, list) else selected[part]
    if selected.get("setSeed") is not True or selected.get("seed") != EXPECTED_SEED:
        destination.unlink(missing_ok=True)
        raise FixtureError("Deterministic copy did not retain the exact seed=1 option")

    receipt = {
        "schema": SCHEMA,
        "status": "PASS_DETERMINISTIC_FIXTURE_COPY_CREATED",
        "purpose": "TEST_ONLY_DISPOSABLE_COPY;SOURCE_FIXTURE_AND_REFERENCE_RESULTS_UNCHANGED",
        "source_path": str(source),
        "source_sha256": source_before,
        "expected_source_sha256": expected_source_sha256,
        "source_sha256_after": source_after,
        "source_unchanged": source_before == source_after,
        "clone_path": str(destination),
        "clone_sha256": clone_sha,
        "clone_is_distinct": clone_sha != source_before,
        "active_configuration_member": ACTIVE_ANALYSES_MEMBER,
        "changed_archive_member": changed_member,
        "changed_json_pointer": changed_pointer,
        "analysis_index": match.get("analysis_index"),
        "analysis_id": match.get("analysis_id"),
        "analysis_name": match.get("analysis_name"),
        "module_name": match.get("module_name"),
        "before": {"setSeed": False, "seed": EXPECTED_SEED},
        "after": {"setSeed": True, "seed": EXPECTED_SEED},
        "archive_member_count": inspection["archive_member_count"],
        "changed_archive_member_count": changed_count,
        "unchanged_non_active_member_count": unchanged_member_count,
        "result_output_members_changed": False,
        "reference_results_modified": False,
        "certification": "NOT_GRANTED",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    receipt["receipt_path"] = str(receipt_path)
    receipt["receipt_sha256"] = sha_file(receipt_path)
    return receipt


def verify_deterministic_fixture_receipt(
    receipt: dict | None,
    expected_source_sha256: str,
    require_clone: bool = True,
) -> bool:
    if not isinstance(receipt, dict):
        return False
    if receipt.get("schema") != SCHEMA or receipt.get("status") != "PASS_DETERMINISTIC_FIXTURE_COPY_CREATED":
        return False
    source = pathlib.Path(str(receipt.get("source_path") or ""))
    clone = pathlib.Path(str(receipt.get("clone_path") or ""))
    receipt_path = pathlib.Path(str(receipt.get("receipt_path") or ""))
    if not source.is_file() or source.is_symlink():
        return False
    if require_clone and (not clone.is_file() or clone.is_symlink()):
        return False
    if not receipt_path.is_file() or receipt_path.is_symlink():
        return False
    if receipt.get("receipt_sha256") != sha_file(receipt_path):
        return False
    on_disk = json.loads(receipt_path.read_text(encoding="utf-8"))
    if on_disk.get("clone_path") != str(clone) or on_disk.get("clone_sha256") != receipt.get("clone_sha256"):
        return False
    return bool(
        receipt.get("expected_source_sha256") == expected_source_sha256
        and receipt.get("source_sha256") == expected_source_sha256
        and receipt.get("source_sha256_after") == expected_source_sha256
        and receipt.get("source_unchanged") is True
        and sha_file(source) == expected_source_sha256
        and (not require_clone or sha_file(clone) == receipt.get("clone_sha256"))
        and receipt.get("clone_is_distinct") is True
        and receipt.get("active_configuration_member") == ACTIVE_ANALYSES_MEMBER
        and receipt.get("changed_archive_member") == ACTIVE_ANALYSES_MEMBER
        and receipt.get("changed_archive_member_count") == 1
        and isinstance(receipt.get("unchanged_non_active_member_count"), int)
        and receipt.get("unchanged_non_active_member_count") >= 0
        and receipt.get("result_output_members_changed") is False
        and receipt.get("before") == {"setSeed": False, "seed": EXPECTED_SEED}
        and receipt.get("after") == {"setSeed": True, "seed": EXPECTED_SEED}
        and receipt.get("reference_results_modified") is False
    )
