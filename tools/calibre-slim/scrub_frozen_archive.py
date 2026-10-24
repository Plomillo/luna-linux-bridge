#!/usr/bin/env python3
"""Scrub explicitly out-of-scope modules from Calibre's frozen payload.

The archive is concatenated code/resources with offsets embedded in the official
native launcher. This tool does NOT shift entries or rebuild the launcher:
it zeroes only indexed payload ranges listed by dump_frozen_index.py, preserving
the file length and every original offset. Any unclassified module stays intact.
Post-scrub conversion smoke tests are a mandatory release gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Any

UPSTREAM = {
    "repository": "kovidgoyal/calibre",
    "tag": "v9.17.0",
    "commit": "e6b9e09472f6e63f8a12bf376eb54836042f0f5f",
}

TARGET_PREFIXES = {
    "calibre/ai/": "AI provider modules outside the conversion scope",
    "calibre/gui2/actions/": "GUI action modules",
    "calibre/gui2/store/": "ebook-store modules",
    "calibre/ebooks/recipes/": "conversion/news recipe support outside the requested formats",
    "calibre/web/feeds/recipes/": "news recipe modules",
    "calibre/ebooks/catalogs/": "catalog generation modules",
    "calibre/library/catalogs/": "library catalog generation modules",
    "calibre/translations/": "Calibre UI translation catalogs",
}

ALLOWED_DEVICE_MODULES = {
    "calibre/devices/__init__.py",
    "calibre/devices/__init__.pyc",
    "calibre/devices/interface.py",
    "calibre/devices/interface.pyc",
}

TARGET_PLUGIN_STEMS = {
    "__init__",
    "docx_input",
    "epub_input",
    "epub_output",
    "html_input",
    "archive_input",
    "oeb_output",
    "pdf_input",
    "pdf_output",
    "txt_input",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_region(handle, offset: int, size: int) -> str:
    handle.seek(offset)
    h = hashlib.sha256()
    left = size
    while left:
        chunk = handle.read(min(left, 1024 * 1024))
        if not chunk:
            raise RuntimeError("Unexpected end of frozen archive while hashing indexed range")
        h.update(chunk)
        left -= len(chunk)
    return h.hexdigest()


def category_for(name: str) -> str | None:
    normalized = name.replace("\\", "/").lstrip("./")

    for prefix, category in TARGET_PREFIXES.items():
        if normalized.startswith(prefix):
            return category

    if normalized.startswith("calibre/devices/"):
        if normalized not in ALLOWED_DEVICE_MODULES:
            return "device drivers outside the generic device interface"

    plugin_prefix = "calibre/ebooks/conversion/plugins/"
    if normalized.startswith(plugin_prefix):
        leaf = PurePosixPath(normalized).name
        stem = leaf
        for suffix in (".pyc", ".py", ".pyo"):
            if stem.endswith(suffix):
                stem = stem[:-len(suffix)]
                break
        if stem not in TARGET_PLUGIN_STEMS:
            return "non-target conversion plugin outside PDF/EPUB and the retained source formats"

    return None


def zero_range(handle, offset: int, size: int) -> None:
    handle.seek(offset)
    zero = b"\0" * min(1024 * 1024, max(1, size))
    remaining = size
    while remaining:
        chunk_size = min(remaining, len(zero))
        written = handle.write(zero[:chunk_size])
        if written != chunk_size:
            raise RuntimeError("Short write while scrubbing frozen module payload")
        remaining -= written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="Extracted official Calibre distribution root")
    parser.add_argument("--index", type=Path, required=True, help="Index produced by dump_frozen_index.py under calibre-debug")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve(strict=True)
    index_path = args.index.resolve(strict=True)
    archive = root / "lib" / "calibre-extensions" / "python-lib.bypy.frozen"
    if not archive.is_file():
        raise RuntimeError(f"Frozen archive not found: {archive}")

    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("schema") != "CAJITA_CALIBRE_FROZEN_INDEX/1.0":
        raise RuntimeError("Frozen index schema is not recognized")
    if index.get("upstream_tag") != UPSTREAM["tag"]:
        raise RuntimeError("Frozen index upstream tag differs from the pinned Calibre tag")
    if archive.stat().st_size != int(index["archive_size_bytes"]):
        raise RuntimeError("Frozen archive size differs from embedded-runtime index evidence")
    if sha256_file(archive) != index["archive_sha256"]:
        raise RuntimeError("Frozen archive hash differs from embedded-runtime index evidence")

    entries = index["entries"]
    if not isinstance(entries, list) or len(entries) < 100:
        raise RuntimeError("Frozen index entries are missing or unexpectedly small")

    selected: list[dict[str, Any]] = []
    previous_end = 0
    ordered = sorted(entries, key=lambda item: (int(item["offset"]), int(item["size"])))
    for item in ordered:
        name = str(item["name"])
        offset = int(item["offset"])
        size = int(item["size"])
        if offset < 0 or size < 0 or offset + size > archive.stat().st_size:
            raise RuntimeError(f"Out-of-bounds module range in manifest: {name}")
        if offset < previous_end and size:
            raise RuntimeError(f"Overlapping frozen payload ranges detected at {name}")
        previous_end = max(previous_end, offset + size)
        category = category_for(name)
        if category and size:
            selected.append({
                "name": name,
                "offset": offset,
                "size": size,
                "category": category,
            })

    if len(selected) < 100:
        raise RuntimeError(
            f"Refusing scrub: only {len(selected)} out-of-scope payload entries matched"
        )

    report: dict[str, Any] = {
        "schema": "CAJITA_CALIBRE_FROZEN_SCRUB_REPORT/1.0",
        "candidate_id": "CAJITA_CALIBRE_SLIM_V1_20261024",
        "upstream": UPSTREAM,
        "status": "DRY_RUN_NOT_APPLIED",
        "applied": bool(args.apply),
        "archive_path": str(archive),
        "archive_sha256_before": sha256_file(archive),
        "archive_size_bytes_before": archive.stat().st_size,
        "index_sha256": sha256_file(index_path),
        "source_index_entry_count": len(entries),
        "selected_entry_count": len(selected),
        "selected_payload_bytes": sum(item["size"] for item in selected),
        "policy": "ZERO_EXPLICITLY_OUT_OF_SCOPE_MODULE_PAYLOADS_IN_PLACE; PRESERVE_NATIVE_INDEX_OFFSETS",
        "limitations": [
            "Archive length and native offsets do not change; unclassified modules remain intact.",
            "This does not prove all dead code has been removed.",
            "A failed post-scrub conversion canary blocks the candidate package.",
        ],
        "categories": {},
        "removed_payloads": [],
        "certification": "NOT_GRANTED",
    }

    for item in selected:
        category = item["category"]
        bucket = report["categories"].setdefault(category, {"entry_count": 0, "payload_bytes": 0})
        bucket["entry_count"] += 1
        bucket["payload_bytes"] += item["size"]

    if args.apply:
        with archive.open("r+b") as handle:
            # Reject overlapping entries and recheck the exact pre-scrub hash
            # before any write; all ranges come from the runtime's native index.
            for item in selected:
                offset = int(item["offset"])
                size = int(item["size"])
                item["sha256_before"] = sha256_region(handle, offset, size)
            if sha256_file(archive) != report["archive_sha256_before"]:
                raise RuntimeError("Frozen archive changed while validating payload hashes")
            for item in selected:
                zero_range(handle, int(item["offset"]), int(item["size"]))
            handle.flush()
            os.fsync(handle.fileno())

        report["removed_payloads"] = selected
        report["archive_size_bytes_after"] = archive.stat().st_size
        report["archive_sha256_after"] = sha256_file(archive)
        report["payload_bytes_zeroed"] = sum(item["size"] for item in selected)
        report["archive_size_preserved"] = (
            report["archive_size_bytes_before"] == report["archive_size_bytes_after"]
        )
        if not report["archive_size_preserved"]:
            raise RuntimeError("Frozen archive length changed; native offsets are no longer valid")
        if report["archive_sha256_before"] == report["archive_sha256_after"]:
            raise RuntimeError("Frozen archive hash did not change after scrub")
        report["status"] = "SCRUBBED_AWAITING_CONVERSION_SMOKE_TESTS"

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "selected_entry_count": report["selected_entry_count"],
        "selected_payload_bytes": report["selected_payload_bytes"],
        "archive_size_bytes": archive.stat().st_size,
        "archive_sha256": sha256_file(archive),
        "report": str(args.report),
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
