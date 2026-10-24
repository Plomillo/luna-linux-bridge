#!/usr/bin/env python3
"""Run inside Calibre's embedded Python with calibre-debug -e.

Dumps the runtime's authoritative frozen-module path -> offset/size index.
The host-side scrubber uses it to zero selected out-of-scope payloads while
preserving every offset and the original native import index.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from bypy_frozen_importer import index_for_name, offsets_for_index


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    importer = next(
        (
            item
            for item in sys.meta_path
            if item.__class__.__name__ == "BypyFrozenImporter"
        ),
        None,
    )
    if importer is None:
        raise RuntimeError("Calibre's BypyFrozenImporter is not installed in sys.meta_path")

    archive = Path(importer.dataloc).resolve(strict=True)
    tree = importer.filesystem_tree
    entries: list[dict[str, int | str]] = []

    def visit(node: dict, prefix: str = "") -> None:
        for part, child in node.items():
            name = f"{prefix}/{part}" if prefix else part
            idx = int(index_for_name(name))
            if idx >= 0:
                offset, size = offsets_for_index(idx)
                offset, size = int(offset), int(size)
                if offset < 0 or size < 0 or offset + size > archive.stat().st_size:
                    raise RuntimeError(
                        f"Invalid frozen index range for {name!r}: offset={offset}, size={size}"
                    )
                entries.append({
                    "name": name,
                    "index": idx,
                    "offset": offset,
                    "size": size,
                })
            if isinstance(child, dict) and child:
                visit(child, name)

    visit(tree)
    entries.sort(key=lambda entry: (int(entry["offset"]), str(entry["name"])))
    if len(entries) < 100:
        raise RuntimeError(f"Frozen index unexpectedly small: only {len(entries)} entries")

    output_path = Path(sys.argv[-1]).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "CAJITA_CALIBRE_FROZEN_INDEX/1.0",
        "upstream_tag": "v9.17.0",
        "archive_path": str(archive),
        "archive_size_bytes": archive.stat().st_size,
        "archive_sha256": sha256(archive),
        "entry_count": len(entries),
        "entries": entries,
        "index_source": "official embedded BypyFrozenImporter; offsets are not guessed",
    }
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PASS",
        "archive_size_bytes": report["archive_size_bytes"],
        "archive_sha256": report["archive_sha256"],
        "entry_count": len(entries),
        "report": str(output_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
