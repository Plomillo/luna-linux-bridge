#!/usr/bin/env python3
"""Smoke tests for the exact Calibre PDF/EPUB feature subset."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

MARKER = "CAJITASLIMMARKER2026"
CANDIDATE_ID = "CAJITA_CALIBRE_SLIM_PDF_EPUB_V2_20261024"


def epub_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"EPUB ZIP integrity failure at {bad}")
        if "mimetype" not in zf.namelist():
            raise RuntimeError("EPUB missing mimetype member")
        if zf.read("mimetype").strip() != b"application/epub+zip":
            raise RuntimeError("EPUB has incorrect mimetype")
        return "\n".join(
            zf.read(name).decode("utf-8", "replace")
            for name in zf.namelist()
            if name.lower().endswith((".html", ".htm", ".xhtml", ".xml", ".opf", ".ncx"))
        )


def invoke(entrypoint: Path, source: Path, destination: Path, env: dict[str, str], timeout: int) -> dict:
    start = time.monotonic()
    command = [str(entrypoint), str(source), str(destination)]
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, errors="replace", timeout=timeout, env=env, check=False)
    return {"command": command, "returncode": completed.returncode,
            "elapsed_seconds": round(time.monotonic() - start, 3),
            "output_tail": completed.stdout[-6000:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--converter", type=Path, required=True,
                    help="Official Calibre ebook-convert executable or candidate wrapper")
    ap.add_argument("--work-dir", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--mode", choices=("baseline", "candidate"), default="candidate")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    entry = args.converter.resolve(strict=True)
    work = args.work_dir.resolve()
    if work.exists():
        import shutil
        shutil.rmtree(work)
    work.mkdir(parents=True)
    profile = work / "profile"
    profile.mkdir()
    env = os.environ.copy()
    env["CALIBRE_CONFIG_DIRECTORY"] = str(profile)
    env["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    env["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"
    env.setdefault("QT_QPA_PLATFORM", "xcb")

    txt = work / "source.txt"
    txt.write_text("Cajita Calibre PDF EPUB smoke test.\n" + MARKER +
                   "\nUnicode text: español, acción, café, niño, Ελληνικά, 日本語.\n",
                   encoding="utf-8")
    specifications = [
        ("create_pdf_from_txt", txt, work / "created.pdf", "pdf"),
        ("create_epub_from_txt", txt, work / "created.epub", "epub"),
    ]
    results: list[dict] = []
    outputs: dict[str, Path] = {}
    for name, source, dest, format_name in specifications:
        record = {"test": name, "input": source.name, "output": dest.name}
        try:
            record.update(invoke(entry, source, dest, env, args.timeout))
            if record["returncode"] != 0:
                raise RuntimeError("Calibre returned a non-zero exit code")
            if not dest.is_file() or dest.stat().st_size == 0:
                raise RuntimeError("output is missing or empty")
            if format_name == "pdf":
                if dest.read_bytes()[:5] != b"%PDF-":
                    raise RuntimeError("output lacks PDF magic bytes")
            else:
                body = epub_text(dest)
                record["epub_marker_present"] = MARKER in body
                if MARKER not in body:
                    raise RuntimeError("EPUB output did not preserve the text marker")
            record["status"] = "PASS"
            record["output_size_bytes"] = dest.stat().st_size
            outputs[name] = dest
        except Exception as exc:
            record["status"] = "FAIL"
            record["error"] = str(exc)
        results.append(record)

    roundtrips = [
        ("pdf_to_epub", outputs.get("create_pdf_from_txt"), work / "roundtrip.epub", "epub"),
        ("epub_to_pdf", outputs.get("create_epub_from_txt"), work / "roundtrip.pdf", "pdf"),
    ]
    for name, source, dest, format_name in roundtrips:
        record = {"test": name, "input": source.name if source else None, "output": dest.name}
        try:
            if source is None:
                raise RuntimeError("source artifact was not produced")
            record.update(invoke(entry, source, dest, env, args.timeout))
            if record["returncode"] != 0:
                raise RuntimeError("Calibre returned a non-zero exit code")
            if not dest.is_file() or dest.stat().st_size == 0:
                raise RuntimeError("output is missing or empty")
            if format_name == "pdf":
                if dest.read_bytes()[:5] != b"%PDF-":
                    raise RuntimeError("output lacks PDF magic bytes")
            else:
                body = epub_text(dest)
                record["epub_marker_present"] = MARKER in body
                if MARKER not in body:
                    raise RuntimeError("PDF-to-EPUB output did not preserve the text marker")
            record["status"] = "PASS"
            record["output_size_bytes"] = dest.stat().st_size
        except Exception as exc:
            record["status"] = "FAIL"
            record["error"] = str(exc)
        results.append(record)

    wrapper_checks = []
    if args.mode == "candidate" and entry.name == "calibre-slim-convert":
        html = work / "unsupported.html"
        html.write_text("<html><body>out of scope</body></html>", encoding="utf-8")
        checks = [
            ("reject_html_input", [str(entry), str(html), str(work / "bad.epub")],
             "unsupported input format"),
            ("reject_non_pdf_epub_output", [str(entry), str(txt), str(work / "bad.mobi")],
             "only PDF and EPUB outputs are permitted"),
        ]
        for name, command, expected in checks:
            try:
                proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, errors="replace", timeout=10, env=env, check=False)
                passed = proc.returncode == 2 and "FAIL_CLOSED" in proc.stdout and expected in proc.stdout
                wrapper_checks.append({"test": name, "status": "PASS" if passed else "FAIL",
                                       "returncode": proc.returncode, "output_tail": proc.stdout[-1000:]})
            except Exception as exc:
                wrapper_checks.append({"test": name, "status": "FAIL", "error": str(exc)})

    passed = sum(1 for item in results if item.get("status") == "PASS")
    wrapper_passed = all(item.get("status") == "PASS" for item in wrapper_checks)
    all_passed = passed == len(results) and wrapper_passed
    report = {
        "schema": "CAJITA_CALIBRE_SLIM_SMOKE_REPORT/2.0",
        "mode": args.mode,
        "candidate_id": CANDIDATE_ID,
        "entrypoint": str(entry),
        "marker": MARKER,
        "test_count": len(results) + len(wrapper_checks),
        "passed": passed + sum(1 for item in wrapper_checks if item.get("status") == "PASS"),
        "failed": len(results) + len(wrapper_checks) - passed -
                  sum(1 for item in wrapper_checks if item.get("status") == "PASS"),
        "wrapper_checks": wrapper_checks,
        "status": "PASS" if all_passed else "FAIL",
        "certification": "NOT_GRANTED",
        "tests": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
