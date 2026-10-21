#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import fitz


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def run_cli(executable: str, *args: str) -> dict:
    result = subprocess.run(
        [executable, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"CLI command failed ({result.returncode}): {args[0]}\n"
            f"stdout={result.stdout[-2000:]}\nstderr={result.stderr[-2000:]}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as first_exc:
        decoder = json.JSONDecoder()
        for index, character in enumerate(result.stdout):
            if character != "{":
                continue
            try:
                value, end = decoder.raw_decode(result.stdout[index:])
            except json.JSONDecodeError:
                continue
            if not result.stdout[index + end:].strip():
                return value
        raise RuntimeError(
            f"CLI emitted invalid JSON for {args[0]}; "
            f"stdout_prefix={result.stdout[:1000]!r}; stderr_prefix={result.stderr[:1000]!r}"
        ) from first_exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = out / "synthetic-source.pdf"
    reordered = out / "synthetic-reordered.pdf"
    reading_copy = out / "synthetic-reading-copy.pdf"
    inspection = out / "inspection.json"

    doc = fitz.open()
    texts = [
        "WORKBENCH_SYNTHETIC_PAGE_1. " + ("This is reproducible fixture text for document integrity validation. " * 4),
        "WORKBENCH_SYNTHETIC_PAGE_2. " + ("Clinical terminology requires contextual review. " * 5),
        "WORKBENCH_SYNTHETIC_PAGE_3. " + ("The source PDF is immutable and its content is audited. " * 5),
    ]
    for text in texts:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(54, 64, 540, 760), text, fontsize=11)
    doc.save(source)
    doc.close()
    original_hash = sha256(source)

    inspected = run_cli(args.cli, "inspect", str(source), "--audit", str(inspection))
    assert inspected["page_count"] == 3, inspected
    assert inspected["input_sha256"] == original_hash, inspected

    reorder = run_cli(args.cli, "reorder", str(source), str(reordered), "--order", "3,1,2")
    assert reorder["verification"] == "PASS", reorder
    assert reorder["page_count"] == 3, reorder
    with fitz.open(reordered) as check:
        got = [page.get_text() for page in check]
    assert "WORKBENCH_SYNTHETIC_PAGE_3" in got[0]
    assert "WORKBENCH_SYNTHETIC_PAGE_1" in got[1]
    assert "WORKBENCH_SYNTHETIC_PAGE_2" in got[2]

    reflow = run_cli(
        args.cli, "reflow", str(source), str(reading_copy), "--confirm-text-only"
    )
    assert reflow["verification"] == "PASS_STRUCTURAL_CHECKS_REVIEW_REQUIRED", reflow
    assert reflow["source_page_count"] == 3, reflow
    assert reflow["output_text_characters"] > 0, reflow
    assert reflow["human_visual_review_required"] is True, reflow
    assert sha256(source) == original_hash, "Input PDF changed during smoke test."

    summary = {
        "schema": "LOUKSNA_DOCUMENT_WORKBENCH_CONTINUOUS_SMOKE/1.0",
        "observed_at_utc": utc_now(),
        "status": "PASS",
        "scope": "SYNTHETIC_FIXTURE_ONLY_NO_USER_DOCUMENTS",
        "checks": {
            "installable_cli_inspection": "PASS",
            "inspection_audit_written": inspection.is_file(),
            "explicit_page_permutation": "PASS",
            "page_order_content_verified": "PASS",
            "text_only_reflow": "PASS_STRUCTURAL_CHECKS_REVIEW_REQUIRED",
            "source_sha256_unchanged": True,
            "visual_review": "NOT_PERFORMED",
            "translation_backend": "NOT_RUN_NO_LOCAL_MODEL_ASSUMED",
            "ocr_backend": "NOT_RUN_OPTIONAL_SYSTEM_DEPENDENCY",
        },
        "source": {"sha256": original_hash, "size_bytes": source.stat().st_size},
        "outputs": {
            "inspection": {"path": str(inspection), "sha256": sha256(inspection)},
            "reordered_pdf": {"path": str(reordered), "sha256": sha256(reordered)},
            "reading_copy_pdf": {"path": str(reading_copy), "sha256": sha256(reading_copy)},
            "reflow_audit": {
                "path": str(reading_copy) + ".audit.json",
                "sha256": sha256(reading_copy.with_suffix(reading_copy.suffix + ".audit.json")),
            },
        },
        "limits": [
            "Synthetic fixture only; no personal or copyrighted source PDF was processed.",
            "PASS confirms structural smoke checks, not editorial fidelity or translation quality.",
            "No certification or production activation is implied."
        ],
    }
    (out / "continuous-smoke-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({
            "schema": "LOUKSNA_DOCUMENT_WORKBENCH_CONTINUOUS_SMOKE/1.0",
            "observed_at_utc": utc_now(),
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
