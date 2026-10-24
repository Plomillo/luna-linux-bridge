#!/usr/bin/env python3
"""Smoke tests for a Calibre-compatible converter; writes machine-readable evidence."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


MARKER = "CAJITASLIMMARKER2026"


def make_docx(path: Path) -> None:
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>' + MARKER + '</w:t></w:r></w:p>'
        '<w:sectPr/></w:body></w:document>'
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document)


def epub_text(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"EPUB ZIP integrity failure at {bad}")
        names = zf.namelist()
        if "mimetype" not in names:
            raise RuntimeError("EPUB missing mimetype member")
        if zf.read("mimetype").strip() != b"application/epub+zip":
            raise RuntimeError("EPUB has incorrect mimetype")
        texts = []
        for name in names:
            if name.lower().endswith((".html", ".htm", ".xhtml", ".xml", ".opf", ".ncx")):
                try:
                    texts.append(zf.read(name).decode("utf-8", "replace"))
                except KeyError:
                    pass
        return "\n".join(texts)


def invoke(entrypoint: Path, source: Path, destination: Path, env: dict[str, str], timeout: int) -> dict:
    start = time.monotonic()
    command = [str(entrypoint), str(source), str(destination)]
    completed = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", timeout=timeout, env=env, check=False
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "output_tail": completed.stdout[-6000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--converter", type=Path, required=True, help="Upstream ebook-convert executable or Cajita wrapper")
    ap.add_argument("--work-dir", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--mode", choices=("baseline", "candidate"), default="candidate")
    ap.add_argument("--timeout", type=int, default=90)
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

    html = work / "source.html"
    html.write_text(
        '<!doctype html><html><head><meta charset="utf-8"><title>Cajita Slim Smoke</title>'
        '<style>body{font-family:sans-serif;font-size:12pt}</style></head><body>'
        '<h1>Cajita conversion smoke test</h1><p>' + MARKER +
        '</p><p>Text fidelity, Unicode: español, acción, café, niño, Ελληνικά, 日本語.</p>'
        '</body></html>', encoding="utf-8"
    )
    txt = work / "source.txt"
    txt.write_text("Cajita PDF EPUB smoke test.\n" + MARKER + "\nEspañol: acción, café, niño.\n", encoding="utf-8")
    docx = work / "source.docx"
    make_docx(docx)

    specifications = [
        ("html_to_epub", html, work / "html.epub", "epub", True),
        ("html_to_pdf", html, work / "html.pdf", "pdf", False),
        ("txt_to_epub", txt, work / "txt.epub", "epub", True),
        ("txt_to_pdf", txt, work / "txt.pdf", "pdf", False),
        ("docx_to_epub", docx, work / "docx.epub", "epub", True),
        ("docx_to_pdf", docx, work / "docx.pdf", "pdf", False),
    ]
    results: list[dict] = []
    outputs: dict[str, Path] = {}
    for name, source, dest, format_name, must_contain_marker in specifications:
        record = {"test": name, "input": source.name, "output": dest.name}
        try:
            record.update(invoke(entry, source, dest, env, args.timeout))
            if record["returncode"] != 0:
                raise RuntimeError("converter returned non-zero exit code")
            if not dest.is_file() or dest.stat().st_size == 0:
                raise RuntimeError("output is missing or empty")
            if format_name == "pdf":
                if dest.read_bytes()[:5] != b"%PDF-":
                    raise RuntimeError("output lacks PDF magic bytes")
            else:
                body = epub_text(dest)
                record["epub_marker_present"] = MARKER in body
                if must_contain_marker and MARKER not in body:
                    raise RuntimeError("EPUB did not preserve text marker")
            record["status"] = "PASS"
            record["output_size_bytes"] = dest.stat().st_size
            outputs[name] = dest
        except Exception as exc:
            record["status"] = "FAIL"
            record["error"] = str(exc)
        results.append(record)

    # Validate both required directions from real output generated above.
    for name, source, dest, format_name in [
        ("pdf_to_epub", outputs.get("html_to_pdf"), work / "pdf-roundtrip.epub", "epub"),
        ("epub_to_pdf", outputs.get("html_to_epub"), work / "epub-roundtrip.pdf", "pdf"),
    ]:
        record = {"test": name, "input": source.name if source else None, "output": dest.name}
        try:
            if source is None:
                raise RuntimeError("required source artifact was not produced by an earlier smoke test")
            record.update(invoke(entry, source, dest, env, args.timeout))
            if record["returncode"] != 0:
                raise RuntimeError("converter returned non-zero exit code")
            if not dest.is_file() or dest.stat().st_size == 0:
                raise RuntimeError("output is missing or empty")
            if format_name == "pdf":
                if dest.read_bytes()[:5] != b"%PDF-":
                    raise RuntimeError("output lacks PDF magic bytes")
            else:
                body = epub_text(dest)
                record["epub_marker_present"] = MARKER in body
                if MARKER not in body:
                    raise RuntimeError("PDF-to-EPUB did not preserve text marker")
            record["status"] = "PASS"
            record["output_size_bytes"] = dest.stat().st_size
        except Exception as exc:
            record["status"] = "FAIL"
            record["error"] = str(exc)
        results.append(record)

    wrapper_checks = []
    if args.mode == "candidate" and entry.name == "calibre-slim-convert":
        bad = work / "unsupported.mobi"
        try:
            proc = subprocess.run(
                [str(entry), str(html), str(bad)], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=10, env=env, check=False
            )
            blocked = proc.returncode == 2 and "FAIL_CLOSED" in proc.stdout
            wrapper_checks.append({
                "test": "reject_non_pdf_epub_output",
                "status": "PASS" if blocked else "FAIL",
                "returncode": proc.returncode,
                "output_tail": proc.stdout[-1000:],
            })
            if not blocked:
                results.append({"test": "wrapper_guard", "status": "FAIL", "error": "unsupported output was not rejected"})
        except Exception as exc:
            wrapper_checks.append({"test": "reject_non_pdf_epub_output", "status": "FAIL", "error": str(exc)})

    passed = sum(1 for item in results if item.get("status") == "PASS")
    total = len(results)
    all_passed = passed == total and all(item.get("status") == "PASS" for item in wrapper_checks)
    report = {
        "schema": "CAJITA_CALIBRE_SLIM_SMOKE_REPORT/1.0",
        "mode": args.mode,
        "candidate_id": "CAJITA_CALIBRE_SLIM_V1_20261024",
        "entrypoint": str(entry),
        "marker": MARKER,
        "test_count": total,
        "passed": passed,
        "failed": total - passed,
        "wrapper_checks": wrapper_checks,
        "status": "PASS" if all_passed else "FAIL",
        "certification": "NOT_GRANTED",
        "tests": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "mode": args.mode,
        "status": report["status"],
        "passed": passed,
        "failed": total - passed,
        "report": str(args.report),
    }, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
