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
    parser.add_argument("--academic-pdf", required=True, type=Path)
    parser.add_argument("--academic-report", required=True, type=Path)
    parser.add_argument("--order-analysis-source", required=True, type=Path)
    parser.add_argument("--order-application", required=True, type=Path)
    parser.add_argument("--order-analysis-final", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    pdf, report_path, inspection_path, academic_pdf, academic_report_path, source_analysis_path, order_application_path, final_analysis_path, output = (
        args.pdf.resolve(), args.organization_report.resolve(), args.source_inspection.resolve(),
        args.academic_pdf.resolve(), args.academic_report.resolve(), args.order_analysis_source.resolve(),
        args.order_application.resolve(), args.order_analysis_final.resolve(), args.output.resolve()
    )
    required = (pdf, report_path, inspection_path, academic_pdf, academic_report_path,
                source_analysis_path, order_application_path, final_analysis_path)
    if any(not item.is_file() for item in required):
        raise FileNotFoundError("All PDFs, analysis reports and audit records must exist before packaging.")
    output_tmp = output.with_name(output.name + ".tmp")
    if output.exists() or output_tmp.exists():
        raise FileExistsError("Refusing to overwrite an existing ZIP package or temporary package.")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    academic_report = json.loads(academic_report_path.read_text(encoding="utf-8"))
    source_analysis = json.loads(source_analysis_path.read_text(encoding="utf-8"))
    order_application = json.loads(order_application_path.read_text(encoding="utf-8"))
    final_analysis = json.loads(final_analysis_path.read_text(encoding="utf-8"))
    if report.get("verification") != "PASS_STRUCTURAL_CONTENT_INVARIANCE":
        raise ValueError("Organization report does not contain passing structural/content verification.")
    if order_application.get("input_sha256") != inspection.get("input_sha256"):
        raise ValueError("Original source SHA-256 mismatch between inspection and order application.")
    if report.get("input_sha256") != order_application.get("output_sha256"):
        raise ValueError("Organized PDF does not descend from the verified order-application output.")
    if source_analysis.get("input_sha256") != inspection.get("input_sha256"):
        raise ValueError("Initial page-order analysis does not match the original source PDF.")
    if final_analysis.get("input_sha256") != order_application.get("output_sha256"):
        raise ValueError("Final page-order analysis does not match the post-order PDF.")
    if academic_report.get("input_sha256") != order_application.get("output_sha256"):
        raise ValueError("Academic edition input hash does not match the post-order PDF.")
    if academic_report.get("output_sha256") != sha256(academic_pdf):
        raise ValueError("Academic reading PDF hash does not match its audit.")
    if report.get("output_sha256") != sha256(pdf):
        raise ValueError("Bookmarked PDF SHA-256 does not match its organization report.")
    if report.get("source_page_count") != report.get("output_page_count"):
        raise ValueError("Page count changed; refusing to package output.")
    if order_application.get("source_page_count") != order_application.get("output_page_count"):
        raise ValueError("Page count changed during the order operation.")
    if order_application.get("source_modified") is not False or report.get("source_modified") is not False:
        raise ValueError("Source immutability invariant failed; refusing to package output.")
    if academic_report.get("verification") != "PASS_SOURCE_PAGE_CROSS_REFERENCE_AND_TEXT_PRESENCE":
        raise ValueError("Academic reading edition did not pass source-page cross-reference checks.")

    readme = (
        "Louksna Document Workbench — reading package\n\nContents:\n"
        "- Trastornos_de_personalidad_severos_organizado.pdf: source layout with inferred navigation bookmarks.\n"
        "- Trastornos_de_personalidad_severos_edicion_lectura.pdf: reflowed academic reading copy with contents, legible typography and source-page references.\n"
        "- source-inspection.json: original page inventory and SHA-256.\n"
        "- order-analysis-source.json, order-application-report.json and order-analysis-final.json: evidence behind page-order handling.\n"
        "- organization-report.json and academic-edition-report.json: output checks and editorial limitations.\n"
        "- SHA256SUMS.txt: SHA-256 checksums for payload files.\n\n"
        "The original PDF remains on the source branch and is not overwritten. Pages move only when folios establish a complete, unique, contiguous order; otherwise the report requires manual review and no page is moved.\n"
        "The reading copy changes pagination and is not a facsimile. Translation accuracy and clinical terminology are not certified; human review remains necessary.\n"
    )
    files = [
        (pdf, "Trastornos_de_personalidad_severos_organizado.pdf"),
        (academic_pdf, "Trastornos_de_personalidad_severos_edicion_lectura.pdf"),
        (report_path, "organization-report.json"),
        (inspection_path, "source-inspection.json"),
        (source_analysis_path, "order-analysis-source.json"),
        (order_application_path, "order-application-report.json"),
        (final_analysis_path, "order-analysis-final.json"),
        (academic_report_path, "academic-edition-report.json"),
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
                "Trastornos_de_personalidad_severos_edicion_lectura.pdf",
                "organization-report.json", "source-inspection.json",
                "order-analysis-source.json", "order-application-report.json",
                "order-analysis-final.json", "academic-edition-report.json",
                "README.txt", "SHA256SUMS.txt",
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
        "source_sha256": order_application["input_sha256"],
        "organized_pdf_sha256": report["output_sha256"],
        "page_count": report["output_page_count"],
        "bookmark_count": report["bookmark_count"],
        "order_status": order_application["status"],
        "page_order_changed": order_application["page_order_changed"],
        "order_confidence": order_application["order_evidence"]["confidence"],
        "academic_pdf_sha256": academic_report["output_sha256"],
        "academic_pdf_page_count": academic_report["output_page_count"],
        "source_order_review_required": order_application["status"] == "REVIEW_REQUIRED_NO_PAGES_MOVED",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
