#!/usr/bin/env python3
"""Execute the five registered compact model adapters directly; no auxiliary fallback."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from cajita_task_e2e import MODEL_CASES, make_audio, run_case, task_execution_and_quality_pass, utc_now


def bounded_case_timeout(global_cap: int, record: dict) -> int:
    """Treat the CLI timeout as a hard ceiling, never as a per-case minimum."""
    if isinstance(global_cap, bool) or not isinstance(global_cap, int) or not 1 <= global_cap <= 1800:
        raise ValueError("GLOBAL_TIMEOUT_CAP_OUT_OF_RANGE")
    limits = record.get("limits", {})
    declared = limits.get("timeout_seconds", 900) if isinstance(limits, dict) else 900
    if isinstance(declared, bool) or not isinstance(declared, int) or not 1 <= declared <= 1800:
        raise ValueError("MODEL_CASE_TIMEOUT_OUT_OF_RANGE")
    return min(global_cap, declared)

def make_docling_fixture(path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (512, 512), "white")
    draw = ImageDraw.Draw(image)
    title = ImageFont.load_default(size=48)
    body = ImageFont.load_default(size=40)
    draw.text((40, 64), "INVOICE 4821", fill="black", font=title, stroke_width=1)
    draw.line((38, 150, 474, 150), fill="black", width=4)
    draw.text((40, 260), "TOTAL 37.50", fill="black", font=body, stroke_width=1)
    image.save(path, format="PNG", optimize=False)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args(argv)

    runtime_root = args.runtime_root.resolve(strict=True)
    if not runtime_root.is_dir() or not (runtime_root / "cajita_runtime.py").is_file():
        raise SystemExit("CAJITA_RUNTIME_ROOT_INVALID")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "whisper-hello-world.wav"
    image_path = output_dir / "docling-invoice.png"
    make_audio(audio_path)
    make_docling_fixture(image_path)

    rows = []
    for source in MODEL_CASES:
        record = json.loads(json.dumps(source))
        record["schema"] = "CAJITA_TASK_REQUEST/1.0"
        record["input"] = dict(record["input"])
        if record["input"].get("audio_path") == "@AUDIO@":
            record["input"]["audio_path"] = str(audio_path)
        if record["input"].get("image_path") == "@IMAGE@":
            record["input"]["image_path"] = str(image_path)
        timeout = bounded_case_timeout(args.timeout, record)
        rows.append(run_case(runtime_root, output_dir, record, timeout))

    passed = [row for row in rows if task_execution_and_quality_pass(row)]
    report = {
        "schema": "LOUKSNAPG2_PRIMARY_FIVE_MODEL_E2E/1.0",
        "generated_at_utc": utc_now(),
        "source_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        "runtime_root": str(runtime_root),
        "execution_mode": "DIRECT_REGISTERED_LOCAL_MODEL_ADAPTERS_ONLY",
        "local_offline_only": True,
        "hugging_face_platform_used": False,
        "auxiliary_engine_execution_performed": False,
        "fallback_engine_execution_performed": False,
        "model_inference_performed": any(row.get("status") == "PASS_FUNCTIONAL_EXECUTION" for row in rows),
        "required_model_count": 5,
        "passed_model_count": len(passed),
        "failed_model_count": len(rows) - len(passed),
        "models": rows,
        "global_certification": "NOT_GRANTED",
        "canonical_promotion": "NOT_AUTHORIZED",
        "original_weights_mutated": False,
        "semantic_quality_equivalence_to_full_size_original": "NOT_ESTABLISHED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": report["schema"],
        "status": "PASS_FIXED_SYNTHETIC_MODEL_CASES_ONLY" if len(passed) == 5 else "FAIL",
        "passed_model_count": len(passed),
        "failed_model_count": len(rows) - len(passed),
        "models": {
            row.get("domain_id", "UNKNOWN"): {
                "execution_status": row.get("status"),
                "quality_status": row.get("quality_acceptance", {}).get("status"),
                "failure_reason": row.get("failure_reason"),
            } for row in rows
        },
        "auxiliary_engine_execution_performed": False,
        "global_certification": report["global_certification"],
        "evidence": str(args.output),
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if len(passed) == 5 else 3


if __name__ == "__main__":
    raise SystemExit(main())
