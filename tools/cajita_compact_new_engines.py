#!/usr/bin/env python3
"""Size-first, reversible-container compaction for the ten newly added Cajita assets.

This pass never edits the six model-weight paths. Original official/recovered assets
remain in externalized-assets-staging for rollback. Runtime path repair is a later phase.
"""
from __future__ import annotations

import hashlib
import json
import os
import posixpath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "cajita-luna-runtime"
PLACEMENT_PATH = RUNTIME / "EXTERNALIZED_ASSET_PLACEMENT.json"
WEIGHT_MANIFEST = RUNTIME / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
REPORT_PATH = ROOT / "docs" / "cajita-luna" / "CAJITA_NEW_ENGINE_COMPACTION_20261023.json"
HARD_CAP = 470_000_000

PROTECTED_WEIGHT_PATHS = [
    "1. Cerebro/model.safetensors",
    "3. Transcripción/model.safetensors",
    "4. Traductor Inteligente/Traducción general/model.safetensors",
    "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin",
    "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
    "6. Sistema Inteligente/Anti-Alucinaciones/model.onnx",
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def require_safe_rel(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe archive member path: {name!r}")
    if any(part in ("",) for part in path.parts):
        raise RuntimeError(f"Invalid archive member path: {name!r}")
    return path

def ensure_symlink_safe(member_name: str, link_name: str) -> None:
    link = PurePosixPath(link_name)
    if link.is_absolute():
        raise RuntimeError(f"Absolute symlink rejected: {member_name!r} -> {link_name!r}")
    parent = posixpath.dirname(str(require_safe_rel(member_name)))
    resolved = posixpath.normpath(posixpath.join(parent, link_name))
    if resolved == ".." or resolved.startswith("../"):
        raise RuntimeError(f"Escaping symlink rejected: {member_name!r} -> {link_name!r}")

def unpack_zip(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise RuntimeError(f"Duplicate ZIP member names rejected: {source.name}")
        for info in infos:
            rel = require_safe_rel(info.filename)
            target = destination.joinpath(*rel.parts)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                link_text = archive.read(info).decode("utf-8")
                ensure_symlink_safe(info.filename, link_text)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(link_text, target)
                continue
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
            permissions = mode & 0o777
            if permissions:
                target.chmod(permissions)

def unpack_tar(source: Path, destination: Path) -> None:
    with tarfile.open(source, mode="r:*") as archive:
        members = archive.getmembers()
        for member in members:
            require_safe_rel(member.name)
            if member.issym() or member.islnk():
                ensure_symlink_safe(member.name, member.linkname)
        # The data filter rejects path traversal and unsafe links. Nothing is executed.
        archive.extractall(destination, members=members, filter="data")

def fingerprint_tree(base: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for path in sorted(base.rglob("*"), key=lambda p: p.relative_to(base).as_posix()):
        rel = path.relative_to(base).as_posix()
        if path.is_symlink():
            result[rel] = {
                "kind": "symlink",
                "target": os.readlink(path),
                "executable": bool(path.lstat().st_mode & 0o111),
            }
        elif path.is_file():
            result[rel] = {
                "kind": "file",
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "executable": bool(path.stat().st_mode & 0o111),
            }
    return result

def try_upx(path: Path, eligible_ids: set[str]) -> dict[str, object] | None:
    if not eligible_ids or shutil.which("upx") is None or not path.is_file() or path.is_symlink():
        return None
    try:
        if path.read_bytes()[:4] != b"\x7fELF":
            return None
        if not (path.stat().st_mode & 0o111):
            return None
        original = path.read_bytes()
        original_hash = hashlib.sha256(original).hexdigest()
        original_size = len(original)
        run = subprocess.run(
            ["upx", "-9", "--lzma", "--no-backup", "--force", str(path)],
            capture_output=True, text=True, timeout=180
        )
        if run.returncode != 0 or path.stat().st_size >= original_size:
            path.write_bytes(original)
            path.chmod(path.stat().st_mode | 0o111)
            return None
        test = subprocess.run(["upx", "-t", str(path)], capture_output=True, text=True, timeout=60)
        roundtrip = path.parent / (path.name + ".upx-roundtrip")
        try:
            dec = subprocess.run(
                ["upx", "-d", "-o", str(roundtrip), str(path)],
                capture_output=True, text=True, timeout=180
            )
            if dec.returncode != 0 or not roundtrip.is_file() or sha256_file(roundtrip) != original_hash:
                path.write_bytes(original)
                path.chmod(path.stat().st_mode | 0o111)
                return None
            if test.returncode != 0:
                path.write_bytes(original)
                path.chmod(path.stat().st_mode | 0o111)
                return None
        finally:
            roundtrip.unlink(missing_ok=True)
        return {
            "path": path.name,
            "before_bytes": original_size,
            "after_bytes": path.stat().st_size,
            "before_sha256": original_hash,
            "after_sha256": sha256_file(path),
            "upx_test": "PASS",
            "decompression_sha256_roundtrip": "PASS",
            "method": "UPX-9-LZMA",
        }
    except (OSError, subprocess.TimeoutExpired):
        return None

def compress_tree_to_7z(source_tree: Path, output: Path) -> None:
    if shutil.which("7z") is None:
        raise RuntimeError("7z was not installed on the GitHub runner")
    output.unlink(missing_ok=True)
    args = [
        "7z", "a", "-t7z", "-mx=9", "-m0=lzma2",
        "-md=64m", "-mfb=273", "-ms=on", "-mmt=on", "-snl",
        str(output), "."
    ]
    completed = subprocess.run(args, cwd=source_tree, capture_output=True, text=True, timeout=1800)
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError(
            f"7z compression failed ({completed.returncode}) for {output.name}: "
            f"{completed.stderr[-2000:]}\n{completed.stdout[-2000:]}"
        )
    tested = subprocess.run(["7z", "t", str(output)], capture_output=True, text=True, timeout=600)
    if tested.returncode != 0:
        raise RuntimeError(f"7z integrity test failed for {output.name}: {tested.stdout[-2000:]}")

def materialized_payload_estimate() -> int:
    weights = json.loads(WEIGHT_MANIFEST.read_text(encoding="utf-8"))
    lfs_declared = {item["path"]: int(item["bytes"]) for item in weights.get("artifacts", [])}
    total = 0
    for path in RUNTIME.rglob("*"):
        if not path.is_file() or path.name == "MACRODOWN_MANIFEST.json":
            continue
        rel = path.relative_to(RUNTIME).as_posix()
        size = path.stat().st_size
        declared = lfs_declared.get(rel)
        if declared is not None and size <= 1024:
            size = declared
        total += size
    return total

def current_weight_pointer_hashes() -> dict[str, str]:
    return {
        rel: sha256_file(RUNTIME / rel)
        for rel in PROTECTED_WEIGHT_PATHS
    }

def main() -> int:
    if not PLACEMENT_PATH.is_file() or not WEIGHT_MANIFEST.is_file():
        raise RuntimeError("Required placement or weight manifest is missing")
    placement = json.loads(PLACEMENT_PATH.read_text(encoding="utf-8"))
    if len(placement.get("assets", [])) != 10:
        raise RuntimeError("Fail closed: expected exactly ten registered new assets")
    protected_before = current_weight_pointer_hashes()
    upx_version = None
    if shutil.which("upx"):
        ver = subprocess.run(["upx", "--version"], capture_output=True, text=True)
        upx_version = (ver.stdout or ver.stderr).splitlines()[0] if (ver.stdout or ver.stderr) else "unknown"
    sevenzip_version = subprocess.run(["7z"], capture_output=True, text=True)
    sevenzip_version_text = (sevenzip_version.stdout or sevenzip_version.stderr).splitlines()[0:3]

    eligible_upx_ids = {
        "DAGGER_0_21_8_LINUX_AMD64",
        "OPA_STATIC_LINUX_AMD64_CANDIDATE",
        "RQLITE_10_2_7_LINUX_AMD64",
    }
    ordered = sorted(
        placement["assets"],
        key=lambda item: (-int(item.get("size_bytes", 0)), item.get("id", ""))
    )
    results = []
    original_total = 0
    final_total = 0
    total_saved = 0

    for asset in ordered:
        asset_id = asset["id"]
        current_rel = asset["placed_path"]
        current = ROOT / current_rel
        existing_optimization = asset.get("optimization", {})
        if existing_optimization.get("status") in {
            "COMPACTED_TO_7Z_REPAIR_PENDING",
            "ATTEMPTED_NO_STRICT_SIZE_GAIN_ORIGINAL_PRESERVED",
        }:
            size = current.stat().st_size
            saved = int(existing_optimization.get("saved_bytes", 0))
            results.append({
                "id": asset_id,
                "status": existing_optimization["status"],
                "final_path": current_rel,
                "final_bytes": size,
                "final_sha256": sha256_file(current),
                "saved_bytes": saved,
                "idempotent_skip": True,
            })
            original_total += int(asset.get("upstream_size_bytes", asset.get("size_bytes", size)))
            final_total += size
            total_saved += saved
            continue
        if not current.is_file():
            raise RuntimeError(f"Fail closed: registered asset missing: {current_rel}")

        expected_hash = asset.get("sha256")
        expected_size = int(asset.get("size_bytes", -1))
        actual_hash = sha256_file(current)
        actual_size = current.stat().st_size
        if actual_hash != expected_hash or actual_size != expected_size:
            raise RuntimeError(
                f"Fail closed: placed asset mismatch for {asset_id}: "
                f"expected {expected_size}/{expected_hash}; got {actual_size}/{actual_hash}"
            )

        staging = ROOT / asset["source_staging_path"]
        if not staging.is_file():
            raise RuntimeError(f"Fail closed: immutable staging copy missing: {asset['source_staging_path']}")
        staging_hash = sha256_file(staging)
        if staging_hash != expected_hash:
            raise RuntimeError(f"Fail closed: rollback source hash mismatch for {asset_id}")

        original_total += actual_size
        result: dict[str, object] = {
            "id": asset_id,
            "source_path": current_rel,
            "source_bytes": actual_size,
            "source_sha256": actual_hash,
            "staging_rollback_path": asset["source_staging_path"],
            "staging_rollback_sha256": staging_hash,
            "source_version": asset.get("source_version"),
            "asset_kind": asset.get("asset_kind"),
            "archive_format": None,
            "upx_changes": [],
            "method": ["UPX-9-LZMA on eligible executable ELF assets", "7z LZMA2 ultra container"],
        }

        with tempfile.TemporaryDirectory(prefix="cajita-new-assets-") as temp_name:
            temp = Path(temp_name)
            unpacked = temp / "unpacked"
            unpacked.mkdir()
            if zipfile.is_zipfile(current):
                archive_format = "zip-compatible (zip/whl/nupkg)"
                unpack_zip(current, unpacked)
            elif tarfile.is_tarfile(current):
                archive_format = "tar archive"
                unpack_tar(current, unpacked)
            else:
                archive_format = "standalone binary or opaque payload"
                target = unpacked / current.name
                shutil.copy2(current, target)
                if asset_id == "OPA_STATIC_LINUX_AMD64_CANDIDATE":
                    target.chmod(target.stat().st_mode | 0o111)

            result["archive_format"] = archive_format
            upx_changes = []
            if asset_id in eligible_upx_ids:
                for candidate in sorted(unpacked.rglob("*")):
                    if candidate.is_file() and not candidate.is_symlink():
                        packed = try_upx(candidate, {asset_id})
                        if packed:
                            packed["relative_path"] = candidate.relative_to(unpacked).as_posix()
                            upx_changes.append(packed)
            result["upx_changes"] = upx_changes

            candidate_archive = temp / (current.name + ".7z")
            compress_tree_to_7z(unpacked, candidate_archive)

            verified = temp / "roundtrip"
            verified.mkdir()
            extract = subprocess.run(
                ["7z", "x", "-y", f"-o{verified}", str(candidate_archive)],
                capture_output=True, text=True, timeout=600
            )
            if extract.returncode != 0:
                raise RuntimeError(f"7z extraction round-trip failed for {asset_id}: {extract.stdout[-2000:]}")
            before_tree = fingerprint_tree(unpacked)
            after_tree = fingerprint_tree(verified)
            if before_tree != after_tree:
                raise RuntimeError(
                    f"Fail closed: member/hash/execute-bit round-trip mismatch for {asset_id}; "
                    f"before={len(before_tree)} after={len(after_tree)}"
                )

            candidate_size = candidate_archive.stat().st_size
            result["candidate_7z_bytes"] = candidate_size
            result["candidate_7z_sha256"] = sha256_file(candidate_archive)
            result["candidate_roundtrip"] = "PASS"
            result["verified_member_count"] = len(before_tree)
            if candidate_size < actual_size:
                new_rel = current_rel + ".7z"
                new_path = ROOT / new_rel
                if new_path.exists():
                    raise RuntimeError(f"Fail closed: optimized target already exists: {new_rel}")
                shutil.copy2(candidate_archive, new_path)
                candidate_sha = sha256_file(new_path)
                if candidate_sha != result["candidate_7z_sha256"]:
                    raise RuntimeError(f"Post-copy SHA-256 mismatch for {new_rel}")
                current.unlink()
                old_rel = current_rel
                asset.setdefault("upstream_size_bytes", actual_size)
                asset.setdefault("upstream_sha256", actual_hash)
                asset["placed_path"] = new_rel
                asset["size_bytes"] = candidate_size
                asset["sha256"] = candidate_sha
                asset["placement"] = "IN_CAJITA_SOURCE_TREE_COMPRESSED_CONTAINER_REPAIR_PENDING"
                asset["included_in_current_macrodown_manifest"] = False
                asset["optimization"] = {
                    "status": "COMPACTED_TO_7Z_REPAIR_PENDING",
                    "original_placed_path": old_rel,
                    "original_size_bytes": actual_size,
                    "original_sha256": actual_hash,
                    "optimized_path": new_rel,
                    "optimized_size_bytes": candidate_size,
                    "optimized_sha256": candidate_sha,
                    "saved_bytes": actual_size - candidate_size,
                    "methods": result["method"],
                    "upx_changes": upx_changes,
                    "member_roundtrip": "PASS",
                    "runtime_path_repair": "PENDING_NEXT_PHASE",
                }
                asset["notes"] = (
                    str(asset.get("notes", "")).rstrip()
                    + " Repacked into a smaller LZMA2/7z payload; original preserved in staging. "
                    + "Consumer/extraction path repair is explicitly pending."
                ).strip()
                result.update({
                    "status": "COMPACTED_TO_7Z_REPAIR_PENDING",
                    "final_path": new_rel,
                    "final_bytes": candidate_size,
                    "final_sha256": candidate_sha,
                    "saved_bytes": actual_size - candidate_size,
                })
                total_saved += actual_size - candidate_size
                final_total += candidate_size
            else:
                candidate_archive.unlink(missing_ok=True)
                asset["optimization"] = {
                    "status": "ATTEMPTED_NO_STRICT_SIZE_GAIN_ORIGINAL_PRESERVED",
                    "original_placed_path": current_rel,
                    "original_size_bytes": actual_size,
                    "original_sha256": actual_hash,
                    "candidate_7z_bytes": candidate_size,
                    "candidate_7z_sha256": result["candidate_7z_sha256"],
                    "saved_bytes": 0,
                    "methods": result["method"],
                    "upx_changes": upx_changes,
                    "member_roundtrip": "PASS",
                    "reason": "Candidate did not strictly reduce stored bytes; the smaller original is preserved.",
                }
                result.update({
                    "status": "ATTEMPTED_NO_STRICT_SIZE_GAIN_ORIGINAL_PRESERVED",
                    "final_path": current_rel,
                    "final_bytes": actual_size,
                    "final_sha256": actual_hash,
                    "saved_bytes": 0,
                })
                final_total += actual_size
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    projected = materialized_payload_estimate()
    placement["hard_cap_bytes"] = HARD_CAP
    placement["placed_assets_raw_bytes"] = final_total
    placement["projected_raw_payload_bytes_before_new_manifest_growth"] = projected
    placement["projected_over_cap_bytes_before_new_manifest_growth"] = max(0, projected - HARD_CAP)
    placement["status"] = "NEW_ASSET_COMPACTION_COMPLETE_RUNTIME_PATH_REPAIR_PENDING"
    placement["compaction_pass"] = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "algorithm": "FORMAT_AWARE_MAX_COMPRESSION",
        "targeted_assets": 10,
        "old_model_weight_paths_mutated": [],
        "legacy_weight_protection": "PASS",
        "new_asset_original_bytes": original_total,
        "new_asset_final_bytes": final_total,
        "new_asset_saved_bytes": total_saved,
        "per_asset_results": results,
        "sevenzip_version_lines": sevenzip_version_text,
        "upx_version": upx_version or "UNAVAILABLE; eligible binary attempts fall back to LZMA2 container compression",
        "functional_repair": "NOT_PERFORMED_BY_ORDER",
        "certification": "NOT_GRANTED",
    }
    PLACEMENT_PATH.write_text(json.dumps(placement, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    protected_after = current_weight_pointer_hashes()
    if protected_before != protected_after:
        raise RuntimeError("Fail closed: one or more legacy model-weight files changed")
    report = {
        "schema": "CAJITA_NEW_ENGINE_COMPACTION/1.0",
        "audit_id": "CAJITA_NEW_ENGINE_COMPACTION_20261023",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": "Plomillo/luna-linux-bridge",
        "branch": "main",
        "target_hard_cap_bytes": HARD_CAP,
        "ordering": "NEW_ASSET_COMPACTION_FIRST; RUNTIME_REPAIR_DEFERRED",
        "method": {
            "outer_container": "7z LZMA2, maximum compression, 64 MiB dictionary, solid archive",
            "executable_transform": "UPX-9-LZMA only on eligible executable ELF binaries in Dagger/OPA/rqlite; accepted only after UPX test and exact decompression SHA-256 round-trip",
            "retention_rule": "Replace runtime asset only when the optimized container is strictly smaller; preserve source asset in externalized-assets-staging for rollback",
            "roundtrip": "Every generated candidate archive is tested and extracted; member names, file hashes, symlink targets and executable-bit state are compared",
            "scope": "Exactly the ten externalized assets registered in EXTERNALIZED_ASSET_PLACEMENT.json",
            "excluded": PROTECTED_WEIGHT_PATHS,
        },
        "tools": {"7z": sevenzip_version_text, "upx": upx_version},
        "protected_model_pointer_sha256_before_after": {
            path: {"before": protected_before[path], "after": protected_after[path], "unchanged": protected_before[path] == protected_after[path]}
            for path in PROTECTED_WEIGHT_PATHS
        },
        "totals": {
            "new_asset_original_bytes": original_total,
            "new_asset_final_bytes": final_total,
            "new_asset_saved_bytes": total_saved,
            "projected_runtime_input_bytes_excluding_static_manifest_and_with_declared_lfs_weights": projected,
            "projected_over_470000000_bytes": max(0, projected - HARD_CAP),
            "post_manifest_growth_still_to_be_rechecked": True,
        },
        "assets": results,
        "state": "COMPACTION_COMPLETED_REPAIR_PENDING",
        "runtime_validation": "DEFERRED_TO_REPAIR_PHASE",
        "independent_validation": "NOT_RUN",
        "certification": "NOT_GRANTED",
        "rollback_sources": "Original recovered assets retained under externalized-assets-staging; hashes are recorded per item.",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    doc = RUNTIME / "CajitadeLuna.md"
    doc_text = doc.read_text(encoding="utf-8")
    marker = "## Compactación de los diez activos nuevos — 2026-10-23"
    if marker not in doc_text:
        appendix = f"""

## Compactación de los diez activos nuevos — 2026-10-23

Se ejecutó una pasada de compactación máxima de los diez activos incorporados, priorizando reducción de bytes. Los contenedores LZMA2/7z solo sustituyen al original cuando disminuyen estrictamente el tamaño; los originales recuperados continúan preservados en externalized-assets-staging para rollback. Los binarios ELF elegibles de Dagger, OPA y rqlite se sometieron a UPX con comprobación del empaquetado y ronda exacta de descompresión SHA-256. La relación entre ruta lógica y contenedor comprimido queda registrada en EXTERNALIZED_ASSET_PLACEMENT.json.

La reparación de rutas de extracción/consumo queda pendiente para la siguiente fase. No se modificaron los seis artefactos de peso/modelo preexistentes. La proyección usa los tamaños LFS declarados y excluye el manifiesto estático obsoleto; el constructor deberá regenerar el manifiesto tras la reparación y volver a comprobar el límite de 470.000.000 bytes. Certificación no otorgada.

Informe de evidencia: ../docs/cajita-luna/CAJITA_NEW_ENGINE_COMPACTION_20261023.json.
"""
        doc.write_text(doc_text.rstrip() + "\n" + appendix, encoding="utf-8")

    print(json.dumps(report["totals"], ensure_ascii=False))
    print(f"REPORT={REPORT_PATH.relative_to(ROOT).as_posix()}")
    print("LEGACY_WEIGHT_PATHS_UNCHANGED=PASS")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"COMPACTION_ABORTED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
