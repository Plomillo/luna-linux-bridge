#!/usr/bin/env python3
"""Prune a disposable Calibre tree to Cajita's PDF/EPUB conversion scope.

This is a feature-subset transformation, not a claim that every removed file is
dead code or that every upstream bug is fixed. It preserves the source download.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

UPSTREAM = {
    "repository": "kovidgoyal/calibre",
    "tag": "v9.17.0",
    "commit": "e6b9e09472f6e63f8a12bf376eb54836042f0f5f",
}

CONVERSION_IMPORTS = """# Conversion plugins {{{
from calibre.ebooks.conversion.plugins.docx_input import DOCXInput
from calibre.ebooks.conversion.plugins.epub_input import EPUBInput
from calibre.ebooks.conversion.plugins.epub_output import EPUBOutput
from calibre.ebooks.conversion.plugins.html_input import HTMLInput
from calibre.ebooks.conversion.plugins.oeb_output import OEBOutput
from calibre.ebooks.conversion.plugins.pdf_input import PDFInput
from calibre.ebooks.conversion.plugins.pdf_output import PDFOutput
from calibre.ebooks.conversion.plugins.txt_input import TXTInput

# Keep OEB as an internal pipeline format; only PDF and EPUB are public outputs.
plugins += [
    DOCXInput, EPUBInput, HTMLInput, PDFInput, TXTInput,
    EPUBOutput, PDFOutput, OEBOutput,
]
# }}}
"""

PROFILE_SECTION = """# Profiles {{{
from calibre.customize.profiles import InputProfile, OutputProfile

plugins += [InputProfile, OutputProfile]
# }}}
"""

SUPPORTED_METADATA = {"pdf", "epub", "html", "xhtml", "txt", "text", "docx"}

REMOVE_BUILTIN_SECTIONS = (
    "# To archive plugins {{{",
    "# Catalog plugins {{{",
    "# Device driver plugins {{{",
    "# New metadata download plugins {{{",
    "# Interface Actions {{{",
    "# Preferences Plugins {{{",
    "# Store plugins {{{",
)

OPTIONAL_PACKAGE_PATHS = (
    "calibre/ai",
    "calibre/gui2/actions",
    "calibre/gui2/store",
    "calibre/ebooks/recipes",
    "calibre/ebooks/catalogs",
    "calibre/library/catalogs",
    "calibre/devices",
)

OPTIONAL_RESOURCE_DIRS = {
    "translations",
    "translation",
    "locales",
    "locale",
    "i18n",
    "man-pages",
    "manpages",
}

UNRELATED_LAUNCHERS = {
    "calibre",
    "calibre-server",
    "calibre-smtp",
    "calibre-customize",
    "calibredb",
    "ebook-edit",
    "ebook-viewer",
    "ebook-polish",
    "ebook-meta",
    "fetch-ebook-metadata",
    "web2disk",
    "lrf2lrs",
    "lrs2lrf",
    "lrfviewer",
}

TARGET_PLUGIN_FILES = {
    "__init__.py",
    "docx_input.py",
    "epub_input.py",
    "epub_output.py",
    "html_input.py",
    "oeb_output.py",
    "pdf_input.py",
    "pdf_output.py",
    "txt_input.py",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tree_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            raise
    return total


def tree_digest(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(path.rglob("*"), key=lambda x: x.as_posix()):
        if p.is_file() and not p.is_symlink():
            rel = p.relative_to(path).as_posix().encode("utf-8")
            h.update(rel + b"\0")
            h.update(str(p.stat().st_size).encode("ascii") + b"\0")
            h.update(sha256(p).encode("ascii") + b"\n")
    return h.hexdigest()


def find_builtin(root: Path) -> Path:
    matches = [p for p in root.rglob("builtins.py")
               if p.as_posix().endswith("/calibre/customize/builtins.py")]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one calibre/customize/builtins.py below {root}; "
            f"found {len(matches)}"
        )
    return matches[0]


def replace_section(text: str, marker: str, replacement: str) -> str:
    positions = [i for i in range(len(text)) if text.startswith(marker, i)]
    if len(positions) != 1:
        raise RuntimeError(f"Expected exactly one section marker {marker!r}; found {len(positions)}")
    start = positions[0]
    end_marker = text.find("# }}}", start + len(marker))
    if end_marker < 0:
        raise RuntimeError(f"Section {marker!r} has no closing marker")
    end = text.find("\n", end_marker)
    if end < 0:
        end = len(text)
    else:
        end += 1
    return text[:start] + replacement + text[end:]


def prune_builtin_registry(builtins_path: Path, removed: list[dict[str, Any]]) -> dict[str, str]:
    original = builtins_path.read_text(encoding="utf-8")
    required_markers = (
        "# To archive plugins {{{",
        "# Conversion plugins {{{",
        "# Catalog plugins {{{",
        "# Profiles {{{",
        "# Device driver plugins {{{",
        "# New metadata download plugins {{{",
        "# Interface Actions {{{",
        "# Preferences Plugins {{{",
        "# Store plugins {{{",
    )
    for marker in required_markers:
        if original.count(marker) != 1:
            raise RuntimeError(f"Refusing unknown builtins.py layout: marker count for {marker!r} != 1")

    updated = replace_section(original, "# Conversion plugins {{{", CONVERSION_IMPORTS)
    for marker in REMOVE_BUILTIN_SECTIONS:
        updated = replace_section(updated, marker, "")
    updated = replace_section(updated, "# Profiles {{{", PROFILE_SECTION)
    updated = updated.replace("from calibre.ebooks.html.to_zip import HTML2ZIP\n", "")
    updated = updated.replace(
        "from calibre.ebooks.metadata.archive import ArchiveExtract, KPFExtract, get_comic_metadata\n",
        "from calibre.ebooks.metadata.archive import get_comic_metadata\n",
    )

    # Keep metadata readers/writers needed for supported document types. The
    # classes remain upstream code; this change only narrows registration.
    updated = updated.replace(
        "plugins += [x for x in list(locals().values()) if isinstance(x, type) and x.__name__.endswith('MetadataReader')]",
        "plugins += [x for x in list(locals().values()) if isinstance(x, type) and x.__name__.endswith('MetadataReader') and bool(getattr(x, 'file_types', set()) & {'pdf', 'epub', 'kepub', 'html', 'xhtml', 'txt', 'docx'})]",
    )
    updated = updated.replace(
        "plugins += [x for x in list(locals().values()) if isinstance(x, type) and x.__name__.endswith('MetadataWriter')]",
        "plugins += [x for x in list(locals().values()) if isinstance(x, type) and x.__name__.endswith('MetadataWriter') and bool(getattr(x, 'file_types', set()) & {'pdf', 'epub', 'kepub', 'html', 'xhtml', 'txt', 'docx'})]",
    )
    if "plugins += [x for x in list(locals().values()) if isinstance(x, type) and x.__name__.endswith('MetadataReader') and bool(" not in updated:
        raise RuntimeError("Failed to narrow metadata reader registrations")
    if "plugins += [x for x in list(locals().values()) if isinstance(x, type) and x.__name__.endswith('MetadataWriter') and bool(" not in updated:
        raise RuntimeError("Failed to narrow metadata writer registrations")

    old_hash = hashlib.sha256(original.encode("utf-8")).hexdigest()
    new_hash = hashlib.sha256(updated.encode("utf-8")).hexdigest()
    if old_hash == new_hash:
        raise RuntimeError("Registry transformation made no change")
    builtins_path.write_text(updated, encoding="utf-8", newline="\n")
    removed.append({
        "path": str(builtins_path),
        "action": "narrowed-built-in-registry",
        "sha256_before": old_hash,
        "sha256_after": new_hash,
    })
    return {"before": old_hash, "after": new_hash}


def record_remove(path: Path, root: Path, removed: list[dict[str, Any]], reason: str) -> None:
    rel = path.relative_to(root).as_posix()
    record: dict[str, Any] = {"path": rel, "action": "removed", "reason": reason}
    if path.is_symlink():
        record["symlink_target"] = os.readlink(path)
    elif path.is_file():
        record["size_bytes"] = path.stat().st_size
        record["sha256"] = sha256(path)
    elif path.is_dir():
        record["tree_size_bytes"] = tree_bytes(path)
        record["tree_sha256"] = tree_digest(path)
    removed.append(record)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def remove_conversion_plugins(package_root: Path, root: Path, removed: list[dict[str, Any]]) -> int:
    plugin_dirs = list(package_root.rglob("calibre/ebooks/conversion/plugins"))
    if not plugin_dirs:
        raise RuntimeError("No calibre/ebooks/conversion/plugins directory found")
    count = 0
    for directory in plugin_dirs:
        for path in sorted(directory.iterdir()):
            if path.name in TARGET_PLUGIN_FILES:
                continue
            if path.is_file() or path.is_symlink():
                record_remove(path, root, removed, "non-target conversion plugin outside PDF/EPUB workflow")
                count += 1
            elif path.is_dir():
                record_remove(path, root, removed, "non-target conversion plugin package")
                count += 1
    return count


def remove_optional_package_paths(package_root: Path, root: Path, removed: list[dict[str, Any]]) -> int:
    count = 0
    for relative in OPTIONAL_PACKAGE_PATHS:
        # calibre/devices is retained at interface level because the converter's
        # plugin manager imports DevicePlugin from calibre.devices.interface.
        if relative == "calibre/devices":
            base = package_root / relative
            if not base.exists():
                continue
            for item in sorted(base.iterdir()):
                if item.name in {"__init__.py", "interface.py"}:
                    continue
                record_remove(item, root, removed, "device driver not needed by headless conversion; generic interface retained")
                count += 1
            continue
        path = package_root / relative
        if path.exists() or path.is_symlink():
            record_remove(path, root, removed, "out-of-scope Calibre feature for PDF/EPUB converter")
            count += 1
    return count


def remove_resource_extras(root: Path, removed: list[dict[str, Any]]) -> int:
    count = 0
    # Only remove folders whose ancestry identifies them as UI/share resources;
    # never remove Python localization logic or fonts/dictionaries used by books.
    candidates = sorted(
        (p for p in root.rglob("*") if p.is_dir() and not p.is_symlink()),
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for path in candidates:
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        parts = path.parts
        lower = [x.lower() for x in parts]
        if any(x in {"calibre", "python", "site-packages"} for x in lower[-4:-1]) and path.name.lower() in OPTIONAL_RESOURCE_DIRS:
            # Avoid package/resource folders embedded in Python code paths.
            if "resources" not in lower and "share" not in lower:
                continue
        in_resource_tree = "resources" in lower or "share" in lower
        if in_resource_tree and path.name.lower() in OPTIONAL_RESOURCE_DIRS:
            record_remove(path, root, removed, "non-English UI translation or manual resource directory")
            count += 1
        elif in_resource_tree and path.name.lower() in {"catalog", "content-server", "editor-help", "recipes", "viewer"}:
            record_remove(path, root, removed, "GUI/server/editor/news resource not used by the conversion CLI")
            count += 1
    return count


def remove_non_target_launchers(root: Path, removed: list[dict[str, Any]]) -> int:
    count = 0
    for directory in (root, root / "bin", root / "usr" / "bin"):
        if not directory.exists():
            continue
        for name in sorted(UNRELATED_LAUNCHERS):
            path = directory / name
            if path.is_file() or path.is_symlink():
                record_remove(path, root, removed, "non-conversion launcher outside requested PDF/EPUB scope")
                count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="Extracted source or binary tree; the upstream download is never modified")
    parser.add_argument("--apply", action="store_true", help="Apply removals and narrow the registry")
    parser.add_argument("--source-only", action="store_true", help="Record that this is a source snapshot transformation, not a compiled rebuild")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve(strict=True)
    if not root.is_dir():
        parser.error("--root must be a directory")
    builtin_path = find_builtin(root)
    package_root = builtin_path.parents[2]
    if not (package_root / "calibre").is_dir():
        raise RuntimeError(f"Detected Python package root is unexpected: {package_root}")

    report: dict[str, Any] = {
        "schema": "CAJITA_CALIBRE_SLIM_PRUNE_REPORT/1.0",
        "candidate_id": "CAJITA_CALIBRE_SLIM_V1_20261024",
        "status": "NOT_CERTIFIED",
        "upstream": UPSTREAM,
        "mode": "source-only-pruned-snapshot" if args.source_only else "binary-distribution-pruning",
        "applied": bool(args.apply),
        "certification": "NOT_GRANTED",
        "source_rebuildability": "NOT_ESTABLISHED_BY_THIS_PRUNING_STEP",
        "bug_fix_status": "NO_GENERIC_BUG_FIX_CLAIM; ONLY_TEST-DRIVEN_REPRODUCIBLE_PATCHES_ARE_ADMISSIBLE",
        "language_policy": "REMOVE_UI_TRANSLATIONS_ONLY; PRESERVE_DOCUMENT_LANGUAGE_UNICODE_FONTS_RTL_CJK",
        "target_public_inputs": ["pdf", "epub", "html", "txt", "docx"],
        "target_public_outputs": ["pdf", "epub"],
        "retained_plugins": sorted(TARGET_PLUGIN_FILES),
        "removed": [],
    }
    if not args.apply:
        report["status"] = "DRY_RUN_NOT_APPLIED"
    else:
        before_bytes = tree_bytes(root)
        metadata = prune_builtin_registry(builtin_path, report["removed"])
        report["builtins_registry_sha256"] = metadata
        count_plugins = remove_conversion_plugins(package_root, root, report["removed"])
        count_optional = remove_optional_package_paths(package_root, root, report["removed"])
        count_resources = remove_resource_extras(root, report["removed"])
        count_launchers = remove_non_target_launchers(root, report["removed"])
        report["removal_counts"] = {
            "conversion_plugin_entries": count_plugins,
            "optional_package_paths": count_optional,
            "resource_directories": count_resources,
            "launchers": count_launchers,
        }
        report["raw_bytes_before"] = before_bytes
        report["raw_bytes_after"] = tree_bytes(root)
        report["raw_bytes_saved"] = report["raw_bytes_before"] - report["raw_bytes_after"]
        report["tree_sha256_after"] = tree_digest(root)
        report["status"] = "PRUNED_AWAITING_SMOKE_TESTS"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "source": str(root),
        "builtin": str(builtin_path),
        "package_root": str(package_root),
        "report": str(args.report),
        "raw_bytes_before": report.get("raw_bytes_before"),
        "raw_bytes_after": report.get("raw_bytes_after"),
        "raw_bytes_saved": report.get("raw_bytes_saved"),
        "removed_count": len(report["removed"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
