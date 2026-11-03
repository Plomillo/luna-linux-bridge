#!/usr/bin/env python3
"""Prune an extracted official Calibre Linux bundle to a headless PDF/EPUB scope.

Only explicit, documented out-of-scope resources and launchers are removed.
The program fails closed unless required PDF-rendering and language-content
resources remain. It records file hashes and before/after sizes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

UPSTREAM = {
    "repository": "kovidgoyal/calibre",
    "tag": "v9.17.0",
    "commit": "e6b9e09472f6e63f8a12bf376eb54836042f0f5f",
}

NON_CONVERSION_LAUNCHERS = {
    "calibre",
    "calibre-server",
    "calibre-smtp",
    "calibre-customize",
    "calibre-debug",
    "calibredb",
    "ebook-edit",
    "ebook-viewer",
    "ebook-meta",
    "ebook-polish",
    "fetch-ebook-metadata",
    "web2disk",
    "lrf2lrs",
    "lrs2lrf",
    "lrfviewer",
    "calibre-complete",
    "ebook-device",
}

UNUSED_NATIVE_EXTENSIONS = {
    # Qt GUI modules not used by headless document conversion.
    "PyQt6.QtQuick.so",
    "PyQt6.QtQuickWidgets.so",
    "PyQt6.QtQml.so",
    "PyQt6.QtSensors.so",
    "PyQt6.QtPositioning.so",
    "PyQt6.QtMultimedia.so",
    "PyQt6.QtMultimediaWidgets.so",
    "PyQt6.QtSpatialAudio.so",
    "PyQt6.QtTextToSpeech.so",
    "PyQt6.QtTest.so",
    "PyQt6.QtSql.so",
    "PyQt6.QtSvgWidgets.so",
    # Test-only / language-specific format modules outside the target inputs.
    "_ctypes_test.so",
    "_testbuffer.so",
    "_testcapi.so",
    "_testclinic.so",
    "_testclinic_limited.so",
    "_testimportmultiple.so",
    "_testinternalcapi.so",
    "_testlimitedcapi.so",
    "_testmultiphase.so",
    "_testsinglephase.so",
    "_xxtestfuzz.so",
    "xxlimited.so",
    "xxlimited_35.so",
    "xxsubtype.so",
    # Device transfer / unrelated ebook input features.
    "libmtp.so",
    "libusb.so",
    "pictureflow.so",
    "cPalmdoc.so",
    "chm._chmlib.so",
    "lzx.so",
    "unrardll.unrar.so",
    "pyppmd.c._ppmd.so",
    "inflate64._inflate64.so",
    "bcj._bcj.so",
    "html_syntax_highlighter.so",
}

REQUIRED_PATHS = (
    "ebook-convert",
    "lib/calibre-extensions/python-lib.bypy.frozen",
    "lib/calibre-extensions/PyQt6.QtCore.so",
    "lib/calibre-extensions/PyQt6.QtGui.so",
    "lib/calibre-extensions/PyQt6.QtWidgets.so",
    "lib/calibre-extensions/PyQt6.QtWebEngineCore.so",
    "lib/calibre-extensions/PyQt6.QtWebEngineWidgets.so",
    "lib/calibre-extensions/PyQt6.QtPrintSupport.so",
    "lib/calibre-extensions/podofo.so",
    "resources/hyphenation/locales.json",
    "resources/dictionaries",
)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def tree_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
    return total

def tree_digest(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(path.rglob("*"), key=lambda q: q.as_posix()):
        if p.is_file() and not p.is_symlink():
            rel = p.relative_to(path).as_posix().encode("utf-8")
            h.update(rel + b"\0" + str(p.stat().st_size).encode("ascii") + b"\0")
            h.update(sha256_file(p).encode("ascii") + b"\n")
    return h.hexdigest()

def record_and_remove(path: Path, root: Path, report: list[dict[str, Any]], reason: str) -> None:
    if not (path.exists() or path.is_symlink()):
        return
    item: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "reason": reason,
        "action": "removed",
    }
    if path.is_symlink():
        item["symlink_target"] = str(path.readlink())
    elif path.is_file():
        item["size_bytes"] = path.stat().st_size
        item["sha256"] = sha256_file(path)
    elif path.is_dir():
        item["size_bytes"] = tree_bytes(path)
        item["tree_sha256"] = tree_digest(path)
    report.append(item)
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="Extracted official Calibre v9.17.0 Linux x86-64 bundle")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--upstream-raw-bytes", type=int, required=True,
                        help="Raw bytes of the extracted official runtime, measured before adding the source overlay")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve(strict=True)
    if not root.is_dir():
        parser.error("--root must be a directory")
    for rel in REQUIRED_PATHS:
        if not (root / rel).exists():
            raise RuntimeError(f"Required PDF/EPUB runtime component is absent: {rel}")
    if not (root / "source" / "calibre").is_dir():
        raise RuntimeError("The pruned source overlay must be attached at <root>/source/calibre before binary pruning")

    report: dict[str, Any] = {
        "schema": "CAJITA_CALIBRE_SLIM_BINARY_PRUNE_REPORT/1.0",
        "candidate_id": "CAJITA_CALIBRE_SLIM_PDF_EPUB_V2_20261024",
        "status": "DRY_RUN_NOT_APPLIED",
        "upstream": UPSTREAM,
        "applied": bool(args.apply),
        "certification": "NOT_GRANTED",
        "policy": "EXPLICIT_FEATURE_SUBSET; NO_GENERIC_DEAD_CODE_OR_BUG_FIX_CLAIM",
        "language_policy": "REMOVE_UI_TRANSLATION_CATALOGS; KEEP_RUNTIME_RESOURCES_REQUIRED_BY_UPSTREAM_RENDERER; NOT_A_SELF_CONTAINED_16MB_RUNTIME",
        "required_components": list(REQUIRED_PATHS),
        "removed": [],
    }
    if args.apply:
        before = tree_bytes(root)

        # Non-conversion launchers; never delete the PDF/EPUB conversion binary.
        for directory in (root, root / "bin"):
            if not directory.is_dir():
                continue
            for name in sorted(NON_CONVERSION_LAUNCHERS):
                record_and_remove(directory / name, root, report["removed"],
                                  "launcher for GUI, server, library management, editing, stores or non-target formats")

        # Features wholly unrelated to PDF/EPUB conversion.
        record_and_remove(root / "resources" / "builtin_recipes.zip", root, report["removed"],
                          "built-in news recipe database")
        record_and_remove(root / "resources" / "content-server", root, report["removed"],
                          "content-server web UI and translations")
        record_and_remove(root / "resources" / "localization" / "locales.zip", root, report["removed"],
                          "Calibre UI translation catalogs")
        record_and_remove(root / "resources" / "ebook-convert-complete.calibre_msgpack", root, report["removed"],
                          "shell tab-completion database; not needed for conversion")
        record_and_remove(root / "man-pages", root, report["removed"],
                          "localized command manual pages")

        # QtWebEngine needs a locale package; retain the deterministic English default only.
        locale_dir = root / "translations" / "qtwebengine_locales"
        if locale_dir.is_dir():
            for p in sorted(locale_dir.iterdir()):
                if p.is_file() and p.name.lower() != "en-us.pak":
                    record_and_remove(p, root, report["removed"],
                                      "QtWebEngine UI locale excluded; en-US retained as runtime fallback")
            remaining = sorted(p.name for p in locale_dir.iterdir() if p.is_file())
            if "en-US.pak" not in remaining:
                raise RuntimeError("Refusing locale pruning: required en-US.pak not present")

        # Remove only exact, reviewed native extensions unrelated to conversion.
        extension_dir = root / "lib" / "calibre-extensions"
        for name in sorted(UNUSED_NATIVE_EXTENSIONS):
            record_and_remove(extension_dir / name, root, report["removed"],
                              "explicitly out-of-scope Qt GUI, test, device-transfer or ebook-format module")

        report["raw_bytes_before"] = before
        report["removed_count"] = len(report["removed"])
        report["removed_bytes"] = sum(
            item.get("size_bytes", 0) for item in report["removed"]
        )
        report["source_overlay_raw_bytes"] = tree_bytes(root / "source")
        report["upstream_binary_raw_bytes"] = args.upstream_raw_bytes
        report["raw_bytes_after"] = tree_bytes(root)
        report["raw_bytes_saved"] = report["raw_bytes_before"] - report["raw_bytes_after"]
        report["net_raw_bytes_saved_vs_upstream"] = args.upstream_raw_bytes - report["raw_bytes_after"]
        report["tree_sha256_after"] = tree_digest(root)
        report["status"] = "PRUNED_AWAITING_CONVERSION_SMOKE_TESTS"

        for rel in REQUIRED_PATHS:
            if not (root / rel).exists():
                raise RuntimeError(f"Pruning removed a required component: {rel}")
        if not (root / "resources" / "dictionaries").is_dir():
            raise RuntimeError("Document language dictionaries were removed")
        if not (root / "translations" / "qtwebengine_locales" / "en-US.pak").is_file():
            raise RuntimeError("English QtWebEngine locale was removed")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "root": str(root),
        "report": str(args.report),
        "raw_bytes_before": report.get("raw_bytes_before"),
        "raw_bytes_after": report.get("raw_bytes_after"),
        "raw_bytes_saved": report.get("raw_bytes_saved"),
        "removed_count": len(report["removed"]),
        "removed_bytes": report.get("removed_bytes"),
        "tree_sha256_after": report.get("tree_sha256_after"),
    }, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
