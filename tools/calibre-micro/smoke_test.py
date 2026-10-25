#!/usr/bin/env python3
"""Acceptance tests for the four narrow conversion paths."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path
from pypdf import PdfReader
MARKER = "CAJITA_MICRO_TEST_MARCADOR_2026"

def run(engine, src, dst, vendor):
    env = os.environ.copy(); env["PYTHONPATH"] = str(vendor)
    return subprocess.run([sys.executable, str(engine), str(src), str(dst)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, env=env, check=False)

def epub_content(path):
    with zipfile.ZipFile(path, "r") as archive:
        assert archive.read("mimetype").strip() == b"application/epub+zip"
        assert archive.testzip() is None
        return "\n".join(archive.read(name).decode("utf-8", "replace") for name in archive.namelist() if name.endswith((".xhtml", ".html", ".opf")))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", type=Path, required=True)
    ap.add_argument("--vendor", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    engine, vendor = args.engine.resolve(strict=True), args.vendor.resolve(strict=True)
    results = []
    def check(name, ok, detail=""):
        results.append({"test": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    with tempfile.TemporaryDirectory(prefix="cajita-micro-test-") as temp:
        root = Path(temp)
        txt = root / "sample.txt"
        txt.write_text("Documento de prueba\n\n" + MARKER + "\nEspañol: acción, información, ñandú.\n", encoding="utf-8")
        txt_pdf, txt_epub = root / "from-text.pdf", root / "from-text.epub"
        p = run(engine, txt, txt_pdf, vendor)
        ok = p.returncode == 0 and txt_pdf.is_file() and txt_pdf.read_bytes().startswith(b"%PDF-")
        check("create_pdf_from_txt", ok, p.stdout[-1000:])
        if ok:
            pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(str(txt_pdf)).pages)
            ok = MARKER in pdf_text and "Español" in pdf_text
        check("pdf_text_roundtrip_and_accents", ok, "Marker and Spanish accents extracted" if ok else "Text marker/accent missing")
        p = run(engine, txt, txt_epub, vendor)
        ok = p.returncode == 0 and txt_epub.is_file()
        if ok:
            content = epub_content(txt_epub); ok = MARKER in content and "Español" in content
        check("create_epub_from_txt", ok, p.stdout[-1000:])
        pdf_epub = root / "from-pdf.epub"
        p = run(engine, txt_pdf, pdf_epub, vendor)
        ok = p.returncode == 0 and pdf_epub.is_file()
        if ok: ok = MARKER in epub_content(pdf_epub)
        check("pdf_to_epub", ok, p.stdout[-1000:])
        epub_pdf = root / "from-epub.pdf"
        p = run(engine, txt_epub, epub_pdf, vendor)
        ok = p.returncode == 0 and epub_pdf.is_file() and epub_pdf.read_bytes().startswith(b"%PDF-")
        if ok:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(str(epub_pdf)).pages)
            ok = MARKER in text and "Español" in text
        check("epub_to_pdf", ok, p.stdout[-1000:])
        html_file = root / "not-allowed.html"; html_file.write_text("<p>out of scope</p>", encoding="utf-8")
        p = run(engine, html_file, root / "not-allowed.pdf", vendor)
        check("reject_html_input", p.returncode == 2 and "FAIL_CLOSED" in p.stdout, p.stdout[-500:])
        p = run(engine, txt, root / "not-allowed.mobi", vendor)
        check("reject_non_pdf_epub_output", p.returncode == 2 and "FAIL_CLOSED" in p.stdout, p.stdout[-500:])
        p = run(engine, root / "missing.docx", root / "not-allowed.docx", vendor)
        check("reject_docx_route", p.returncode == 2 and "FAIL_CLOSED" in p.stdout, p.stdout[-500:])
    passed = sum(item["status"] == "PASS" for item in results)
    report = {
      "schema":"CAJITA_PDF_EPUB_MICRO_SMOKE/1.0",
      "candidate":"CAJITA_PDF_EPUB_MICRO_V1",
      "status":"PASS" if passed == len(results) else "FAIL",
      "passed":passed, "failed":len(results)-passed, "test_count":len(results),
      "scope":["PDF->EPUB","EPUB->PDF","TXT->PDF","TXT->EPUB"],
      "limitations":[
        "Text extraction and reflow only; image-only or encrypted PDFs are rejected.",
        "Complex page layout, embedded images, annotations, OCR and original styling are not preserved.",
        "Requires host CPython 3.9+ and glibc; package does not bundle the interpreter."
      ],
      "tests":results, "certification":"NOT_GRANTED"
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed == len(results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
