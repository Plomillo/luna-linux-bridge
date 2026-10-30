#!/usr/bin/env python3
"""Run one isolated, source-bound Granite Docling invoice-image acceptance case."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    root = args.runtime_root.resolve(strict=True)
    image = args.image.resolve(strict=True)
    if image.is_symlink() or not image.is_file() or image.stat().st_size < 1000:
        raise SystemExit("DOCLING_FIXTURE_MISSING_OR_SUSPICIOUS")
    sys.path.insert(0, str(root / "LOUKSNAPG2_RUNTIME"))
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from louksnapg2_engine import LouksnapG2Runtime
    from louksnapg2_functional_eval import run_case, normalized, final_answer

    runtime = LouksnapG2Runtime(root, threads=1)
    preflight = runtime.preflight()
    predicate = lambda output: (
        "invoice" in normalized(final_answer(output)).split()
        and "4821" in normalized(final_answer(output)).split()
        and "37" in normalized(final_answer(output)).split()
        and "50" in normalized(final_answer(output)).split()
    )
    case = run_case(
        runtime,
        "DOCLING_INVOICE_IMAGE_01",
        "D05_INTELIGENCIA_DOCUMENTAL",
        "extract_document_image",
        {
            "image_path": str(image),
            "prompt": "Extract the invoice number and total. Return the visible fields.",
            "max_new_tokens": 96,
        },
        predicate,
        "Granite Docling must extract INVOICE 4821 and TOTAL 37.50 from a high-contrast large-type invoice image.",
    )
    evidence = {
        "schema": "LOUKSNAPG2_DOCLING_ISOLATED_FUNCTIONAL_EVIDENCE/1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        "runtime_root": str(root),
        "local_offline_only": True,
        "external_model_fetch_performed": False,
        "model_inference_performed": case.get("execution_status") == "PASS_EXECUTION",
        "source_model_identity_status": preflight.get("status"),
        "source_model_identity_domains": sorted(preflight.get("models", {}).keys()),
        "fixture": {
            "path_name": image.name,
            "bytes": image.stat().st_size,
            "sha256": sha256(image),
            "fixture_design": "1400x900 RGB; high-contrast; 84px title; 64px fields; separator line",
            "expected_fields": {"invoice_number": "4821", "total": "37.50"},
        },
        "case": case,
        "functional_status": "PASS" if case.get("status") == "PASS" else "FAIL",
        "global_certification": "NOT_GRANTED_BY_ISOLATED_DOCLING_PROBE",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "functional_status": evidence["functional_status"],
        "model_inference_performed": evidence["model_inference_performed"],
        "execution_status": case.get("execution_status"),
        "quality_criterion_passed": case.get("quality_criterion_passed"),
        "reason": case.get("reason"),
        "actual_output": case.get("actual_output"),
        "elapsed_seconds": case.get("elapsed_seconds"),
        "fixture_sha256": evidence["fixture"]["sha256"],
        "source_model_identity_status": evidence["source_model_identity_status"],
        "global_certification": evidence["global_certification"],
        "output": str(args.output),
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
