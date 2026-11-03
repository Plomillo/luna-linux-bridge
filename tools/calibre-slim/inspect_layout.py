#!/usr/bin/env python3
"""Inspect an extracted Calibre binary layout without modifying it."""
from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
all_files = [p for p in root.rglob("*") if p.is_file()]
relevant = []
for p in all_files:
    rel = p.relative_to(root).as_posix()
    low = rel.lower()
    if any(token in low for token in (
        "builtins", "calibre-extensions", "calibre/customize", "conversion/plugins",
        "ebook-convert", "python", "translations", "locale", "share/calibre",
    )) or p.suffix.lower() in {".zip", ".egg", ".pyz"}:
        relevant.append({
            "path": rel,
            "size_bytes": p.stat().st_size,
            "suffix": p.suffix.lower(),
        })
archive_hits = []
for p in all_files:
    if p.suffix.lower() not in {".zip", ".egg", ".pyz"}:
        continue
    try:
        with zipfile.ZipFile(p) as z:
            members = z.namelist()
            hits = [n for n in members if any(key in n.lower() for key in (
                "calibre/customize/builtins", "calibre/ebooks/conversion/plugins",
            ))]
            if hits:
                archive_hits.append({
                    "archive": p.relative_to(root).as_posix(),
                    "member_count": len(members),
                    "matches": hits[:100],
                })
    except Exception:
        pass
so_matches = [
    x for x in relevant
    if x["suffix"] == ".so" and any(term in x["path"].lower() for term in (
        "calibre/customize", "conversion/plugins", "calibre-extensions",
    ))
]
print(json.dumps({
    "schema": "CAJITA_CALIBRE_BINARY_LAYOUT_INSPECTION/1.0",
    "root": str(root),
    "total_files": len(all_files),
    "relevant_file_count": len(relevant),
    "relevant_files": relevant[:1000],
    "archive_hits": archive_hits,
    "relevant_shared_objects": so_matches[:1000],
}, indent=2, sort_keys=True))
