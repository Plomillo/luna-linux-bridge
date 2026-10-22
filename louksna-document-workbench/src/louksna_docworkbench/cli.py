from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import inspect_pdf, organize_pdf, reorder_pdf, reflow_pdf, run_ocr, translate_pdf, write_json_new
from .reading_edition import analyze_pdf_order, create_safe_ordered_copy, create_academic_reading_edition


def _path(value: str) -> Path:
    return Path(value).expanduser()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="louksna-docworkbench",
        description="Standalone local-first PDF organization, reflow and document translation.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect", help="Inspect pages, dimensions, text coverage and hashes.")
    inspect.add_argument("input", type=_path)
    inspect.add_argument("--audit", type=_path, help="Write a new JSON inspection report; existing files are not overwritten.")

    reorder = commands.add_parser("reorder", help="Reorder every page using an explicit complete 1-based permutation.")
    reorder.add_argument("input", type=_path)
    reorder.add_argument("output", type=_path)
    reorder.add_argument("--order", required=True, help="Complete comma-separated page order, e.g. 2,1,3.")

    organize = commands.add_parser("organize", help="Add navigation bookmarks while preserving original page order and content.")
    organize.add_argument("input", type=_path)
    organize.add_argument("output", type=_path)
    organize.add_argument("--audit", type=_path, help="Write a new JSON organization report; existing files are not overwritten.")

    ocr = commands.add_parser("ocr", help="Run installed OCRmyPDF locally; no automatic OCR is performed.")
    ocr.add_argument("input", type=_path)
    ocr.add_argument("output", type=_path)
    ocr.add_argument("--language", default="spa", help="OCRmyPDF language code(s), e.g. spa or spa+eng.")
    ocr.add_argument("--timeout", type=int, default=3600, help="Timeout in seconds (default: 3600).")

    reflow = commands.add_parser("reflow", help="Create a text-only reading copy; figures/layout are not preserved.")
    reflow.add_argument("input", type=_path)
    reflow.add_argument("output", type=_path)
    reflow.add_argument("--confirm-text-only", action="store_true", help="Acknowledge that original layout, figures and tables are not preserved.")
    reflow.add_argument("--allow-sparse", action="store_true", help="Allow pages with little/no extractable text after reviewing the inspection report.")

    translate = commands.add_parser("translate", help="Translate PDF text with already-installed local Argos language models.")
    translate.add_argument("input", type=_path)
    translate.add_argument("--output-dir", type=_path, required=True)
    translate.add_argument("--prefix", required=True)
    translate.add_argument("--source", required=True, help="Source language code, e.g. es.")
    translate.add_argument("--target", required=True, help="Target language code, e.g. en.")
    translate.add_argument("--glossary", type=_path, help="Optional JSON object mapping source terms to preferred target terms.")

    order_analysis = commands.add_parser(
        "analyze-order",
        help="Analyse printed folios and chapter anchors; preserve order when evidence is weak.",
    )
    order_analysis.add_argument("input", type=_path)
    order_analysis.add_argument("--audit", type=_path, help="Write a new JSON order analysis.")

    order_apply = commands.add_parser(
        "order-from-folios",
        help="Reorder only when unique, contiguous printed folios establish a complete permutation.",
    )
    order_apply.add_argument("input", type=_path)
    order_apply.add_argument("output", type=_path)
    order_apply.add_argument("--analysis", type=_path, required=True, help="Matching analyze-order JSON.")
    order_apply.add_argument("--audit", type=_path, required=True, help="New JSON application report.")

    academic = commands.add_parser(
        "academic-edition",
        help="Create an academic text reading edition with hierarchy, TOC and source-page markers.",
    )
    academic.add_argument("input", type=_path)
    academic.add_argument("output", type=_path)
    academic.add_argument("--analysis", type=_path, required=True, help="Matching analyze-order JSON.")
    academic.add_argument("--audit", type=_path, required=True, help="New JSON reading-edition report.")
    academic.add_argument("--title", default="Trastornos de personalidad severos")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = inspect_pdf(args.input)
            if args.audit:
                write_json_new(args.audit, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "reorder":
            print(json.dumps(reorder_pdf(args.input, args.output, args.order), ensure_ascii=False, indent=2))
        elif args.command == "organize":
            print(json.dumps(organize_pdf(args.input, args.output, args.audit), ensure_ascii=False, indent=2))
        elif args.command == "ocr":
            print(json.dumps(run_ocr(args.input, args.output, args.language, args.timeout), ensure_ascii=False, indent=2))
        elif args.command == "reflow":
            print(json.dumps(reflow_pdf(
                args.input, args.output,
                confirm_text_only=args.confirm_text_only,
                allow_sparse=args.allow_sparse,
            ), ensure_ascii=False, indent=2))
        elif args.command == "translate":
            print(json.dumps(translate_pdf(
                args.input, args.output_dir, args.prefix,
                args.source, args.target, args.glossary,
            ), ensure_ascii=False, indent=2))
        elif args.command == "analyze-order":
            result = analyze_pdf_order(args.input)
            if args.audit:
                write_json_new(args.audit, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "order-from-folios":
            print(json.dumps(create_safe_ordered_copy(
                args.input, args.output, args.analysis, args.audit,
            ), ensure_ascii=False, indent=2))
        elif args.command == "academic-edition":
            print(json.dumps(create_academic_reading_edition(
                args.input, args.output, args.analysis, args.audit, args.title,
            ), ensure_ascii=False, indent=2))
        else:
            parser.error("Unsupported command.")
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
