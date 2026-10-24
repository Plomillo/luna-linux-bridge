#!/usr/bin/env python3
"""Fail-closed Cajita entry point for the Calibre PDF/EPUB overlay candidate."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

INPUTS = {".pdf", ".epub", ".txt"}
OUTPUTS = {".pdf", ".epub"}
COMMAND = "ebook-convert"


def fail(message: str, code: int = 2) -> int:
    print(f"FAIL_CLOSED: {message}", file=sys.stderr)
    return code


def main(argv: list[str]) -> int:
    if argv in (["--help"], ["-h"]):
        print("Usage: python3 calibre-slim-convert.py INPUT.(pdf|epub|txt) OUTPUT.(pdf|epub) [Calibre options]")
        return 0
    if len(argv) < 2 or argv[0].startswith("-") or argv[1].startswith("-"):
        return fail("usage: INPUT OUTPUT [Calibre options]")

    source = Path(argv[0]).expanduser().resolve()
    destination = Path(argv[1]).expanduser().resolve()
    source_ext, output_ext = source.suffix.lower(), destination.suffix.lower()
    if source_ext not in INPUTS:
        return fail(f"unsupported input format: {source_ext or '(no extension)'}")
    if output_ext not in OUTPUTS:
        return fail(f"only PDF and EPUB outputs are permitted: {output_ext or '(no extension)'}")
    if not source.is_file() or not os.access(source, os.R_OK):
        return fail(f"input is missing or unreadable: {source}")
    if source == destination:
        return fail("input and output paths must differ")
    if destination.exists() and destination.is_dir():
        return fail("output path is a directory")

    here = Path(__file__).resolve().parent
    overlay = here / "source"
    registry = overlay / "calibre" / "customize" / "builtins.py"
    if not registry.is_file():
        return fail(f"overlay is not materialized at {overlay}; refusing to run the unrestricted external engine", 78)

    configured = os.environ.get("CALIBRE_EBOOK_CONVERT")
    candidates = [Path(configured)] if configured else []
    candidates.extend([here / COMMAND, here / "bin" / COMMAND, here / "usr" / "bin" / COMMAND])
    converter = next((str(p) for p in candidates if p.is_file() and os.access(p, os.X_OK)), None)
    converter = converter or shutil.which(COMMAND)
    if not converter:
        return fail("official Calibre ebook-convert runtime not found; set CALIBRE_EBOOK_CONVERT", 78)

    env = os.environ.copy()
    env["CALIBRE_DEVELOP_FROM"] = str(overlay)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.run([converter, str(source), str(destination), *argv[2:]], env=env, check=False).returncode
    except OSError as exc:
        return fail(f"unable to launch ebook-convert: {exc}", 78)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
