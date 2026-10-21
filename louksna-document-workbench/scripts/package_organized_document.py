#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and verify an auditable organized-PDF ZIP package.")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--organization-report", required=True, type=Path)
    parser.add_argument("--source-inspection", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    pdf, report_path, inspection_path, output = (
        args.pdf.resolve(), args.organization_report.resolve(),
        args.source_inspection.resolve(), args.output.resolve()
    )
    if any(not item.is_file() for item in (pdf, report_path, inspection_path)):
        raise FileNotFoundError("PDF, organization report and source inspection must all exist.")
    output_tmp = output.with_name(output.name + ".tmp")
    if output.exists() or output_tmp.exists():
        raise FileExistsError("Refusing to overwrite an existing ZIP package or temporary package.")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    if report.get("verification") != "PASS_STRUCTURAL_CONTENT_INVARIANCE":
        raise ValueError("Organization report does not contain passing structural/content verification.")
    if report.get("input_sha256") != inspection.get("input_sha256"):
        raise ValueError("Source PDF SHA-256 mismatch between the organization report and inspection.")
    if report.get("output_sha256") != sha256(pdf):
        raise ValueError("Organized PDF SHA-256 does not match the organization report.")
    if report.get("source_page_count") != report.get("output_page_count"):
        raise ValueError("Page count changed; refusing to package output.")
    if report.get("page_order_changed") is not False or report.get("source_modified") is not False:
        raise ValueError("Safety invariants failed; refusing to package output.")

    readme = (
        "Louksna Document Workbench — organized PDF package\n\nContents:\n"
        "- Trastornos_de_personalidad_severos_organizado.pdf: source pages retained in original order, with navigation bookmarks.\n"
        "- organization-report.json: provenance and structural/content invariance evidence.\n"
        "- source-inspection.json: source page inventory and SHA-256.\n"
        "- SHA256SUMS.txt: SHA-256 checksums for packaged files.\n\n"
        "The original PDF is not included as a second duplicate. Page order, geometry and extracted page text were checked.\n"
        "Bookmarks are inferred heuristically and should be reviewed. Existing machine-translation quality is not certified.\n"
    )
    files = [
        (pdf, "Trastornos_de_personalidad_severos_organizado.pdf"),
        (report_path, "organization-report.json"),
        (inspection_path, "source-inspection.json"),
    ]
    sums = "".join(f"{sha256(path)}  {name}\n" for path, name in files)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(output_tmp, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path, name in files:
                archive.write(path, arcname=name)
            archive.writestr("README.txt", readme)
            archive.writestr("SHA256SUMS.txt", sums)
        with zipfile.ZipFile(output_tmp, "r") as archive:
            bad = archive.testzip()
            expected = {
                "Trastornos_de_personalidad_severos_organizado.pdf",
                "organization-report.json", "source-inspection.json", "README.txt", "SHA256SUMS.txt",
            }
            if bad is not None:
                raise RuntimeError(f"ZIP integrity check failed on {bad}.")
            if set(archive.namelist()) != expected:
                raise RuntimeError(f"Unexpected ZIP members: {sorted(archive.namelist())}")
        output_tmp.replace(output)
    except Exception:
        output_tmp.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        raise

    with zipfile.ZipFile(output, "r") as archive:
        members = [{"name": name, "size_bytes": len(archive.read(name))} for name in sorted(archive.namelist())]
    summary = {
        "schema": "LOUKSNA_DOCUMENT_WORKBENCH_PACKAGE/1.0",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "PASS_PACKAGE_INTEGRITY",
        "package_name": output.name,
        "package_size_bytes": output.stat().st_size,
        "package_sha256": sha256(output),
        "members": members,
        "source_sha256": report["input_sha256"],
        "organized_pdf_sha256": report["output_sha256"],
        "page_count": report["output_page_count"],
        "bookmark_count": report["bookmark_count"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
