#!/usr/bin/env python3
"""Read-only forensic census for the BTX source; never mutates or deletes source files."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SUBDIR = Path("cajita-luna-runtime/2. Orquestación/Confesión Eclesial Reformada")
SOURCE_NAME = "Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).7z"
SOURCE_PATH = ROOT / SUBDIR / SOURCE_NAME
DATA_PATH = ROOT / SUBDIR / "data.parquet"
EXPECTED_SOURCE_SHA256 = "be5ec9ee6153a5573a8e491e2f96ea0a4e94c9c6c023d3cb43abd6807f040b36"
EXPECTED_PARQUET_SHA256 = "94f408fabc959e706241e557927c81f1a380b1c51934b60c1f8fde69c0a6d079"
ARCHIVE_EXTS = {".7z", ".zip", ".rar"}

BOOKS_ES = [
    "Génesis", "Éxodo", "Levítico", "Números", "Deuteronomio", "Josué", "Jueces", "Rut",
    "1 Samuel", "2 Samuel", "1 Reyes", "2 Reyes", "1 Crónicas", "2 Crónicas", "Esdras",
    "Nehemías", "Ester", "Job", "Salmos", "Proverbios", "Eclesiastés", "Cantares",
    "Isaías", "Jeremías", "Lamentaciones", "Ezequiel", "Daniel", "Oseas", "Joel", "Amós",
    "Abdías", "Jonás", "Miqueas", "Nahúm", "Habacuc", "Sofonías", "Hageo", "Zacarías",
    "Malaquías", "Mateo", "Marcos", "Lucas", "Juan", "Hechos", "Romanos", "1 Corintios",
    "2 Corintios", "Gálatas", "Efesios", "Filipenses", "Colosenses", "1 Tesalonicenses",
    "2 Tesalonicenses", "1 Timoteo", "2 Timoteo", "Tito", "Filemón", "Hebreos", "Santiago",
    "1 Pedro", "2 Pedro", "1 Juan", "2 Juan", "3 Juan", "Judas", "Apocalipsis",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_tool() -> str:
    for candidate in ("7z", "7zz", "7za"):
        p = shutil.which(candidate)
        if p:
            return p
    raise RuntimeError("No 7z-compatible utility is installed.")


def parse_slt_listing(output: str, archive_path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines() + [""]:
        if not line.strip():
            if current.get("Path"):
                named = current["Path"]
                if named not in {str(archive_path), archive_path.name}:
                    entries.append(current)
            current = {}
        elif " = " in line:
            key, value = line.split(" = ", 1)
            current[key] = value
    return entries


def safe_member_path(entry: dict[str, str]) -> bool:
    raw = entry.get("Path", "")
    normalized = raw.replace("\\", "/")
    posix = PurePosixPath(normalized)
    drive, _ = os.path.splitdrive(normalized)
    if not raw or "\x00" in raw or drive or re.match(r"^[A-Za-z]:", normalized) or posix.is_absolute():
        return False
    if any(part in {"..", ""} for part in posix.parts):
        return False
    if entry.get("Symbolic Link") or entry.get("Hard Link"):
        return False
    attrs = entry.get("Attributes", "")
    if "L" in attrs[:2]:
        return False
    return True


def run_checked(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout)


def list_archive(tool: str, archive: Path) -> list[dict[str, str]]:
    result = run_checked([tool, "l", "-slt", str(archive)], timeout=120)
    entries = parse_slt_listing(result.stdout, archive)
    unsafe = [e.get("Path", "") for e in entries if not safe_member_path(e)]
    if unsafe:
        raise RuntimeError(f"Unsafe or linked archive member path(s): {unsafe[:10]}")
    if not entries:
        raise RuntimeError(f"No member entries found in archive: {archive.name}")
    return entries


def extract_archive(tool: str, archive: Path, dest: Path) -> list[dict[str, str]]:
    entries = list_archive(tool, archive)
    dest.mkdir(parents=True, exist_ok=True)
    run_checked([tool, "x", "-y", f"-o{dest}", str(archive)], timeout=300)
    return entries


def norm_ascii(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))

BOOK_LOOKUP = {norm_ascii(book): book for book in BOOKS_ES}
BOOK_PATTERN = re.compile(r"(?<!\\w)(" + "|".join(re.escape(name) for name in sorted(BOOK_LOOKUP, key=len, reverse=True)) + r")(?!\\w)")


def pdf_audit(pdf: Path, temp_root: Path) -> dict[str, Any]:
    info = run_checked(["pdfinfo", str(pdf)], timeout=60).stdout
    pages_match = re.search(r"(?m)^Pages:\s+(\d+)", info)
    pages = int(pages_match.group(1)) if pages_match else None
    out_txt = temp_root / (hashlib.sha256(str(pdf).encode()).hexdigest()[:12] + ".txt")
    extract = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(out_txt)],
        capture_output=True, text=True, timeout=300
    )
    if extract.returncode != 0:
        return {"path": str(pdf.relative_to(temp_root)), "pages": pages, "text_extraction": "FAILED",
                "error_excerpt": extract.stderr[-400:]}
    text = out_txt.read_text(encoding="utf-8", errors="replace")
    raw_txt = temp_root / (hashlib.sha256((str(pdf) + "-raw").encode()).hexdigest()[:12] + ".txt")
    raw_extract = subprocess.run(
        ["pdftotext", "-raw", "-enc", "UTF-8", str(pdf), str(raw_txt)],
        capture_output=True, text=True, timeout=300
    )
    raw_diagnostics: dict[str, Any] = {"text_extraction": "FAILED"}
    if raw_extract.returncode == 0:
        raw_text = raw_txt.read_text(encoding="utf-8", errors="replace")
        raw_lines = [(i + 1, line.strip()) for i, line in enumerate(raw_text.splitlines()) if line.strip()]
        raw_flat = norm_ascii(raw_text)
        raw_book_hits = sorted({BOOK_LOOKUP[m.group(1)] for m in BOOK_PATTERN.finditer(raw_flat)})
        raw_exact_headings = [
            {"line": i, "book": BOOK_LOOKUP[normalized]}
            for i, line in raw_lines
            if (normalized := norm_ascii(line.strip().rstrip(".:"))) in BOOK_LOOKUP
        ]
        raw_numeric_lines = [
            {"line": i, "numbers": re.findall(r"(?<![A-Za-z])\\d{1,3}(?:[a-z])?(?::\\d{1,3}(?:[a-z])?)?", line)[:12],
             "masked_shape": re.sub(r"\\d+", "N", re.sub(r"[^\\W\\d_]+", "W", line, flags=re.UNICODE))[:150]}
            for i, line in raw_lines
            if len(re.findall(r"(?<![A-Za-z])\\d{1,3}(?:[a-z])?(?::\\d{1,3}(?:[a-z])?)?", line)) >= 3
        ][:40]
        raw_diagnostics = {
            "text_extraction": "PASS",
            "nonempty_lines": len(raw_lines),
            "lines_starting_with_verse_like_number": sum(bool(re.match(r"^\\d{1,3}(?:[a-z])?\\s+\\S", line, re.IGNORECASE)) for _, line in raw_lines),
            "exact_book_heading_line_count": len(raw_exact_headings),
            "exact_book_heading_lines": raw_exact_headings[:100],
            "known_book_names_detected": len(raw_book_hits),
            "known_book_names_missing": sorted(set(BOOKS_ES) - set(raw_book_hits)),
            "masked_numeric_line_examples": raw_numeric_lines,
            "text_content_redacted": True,
        }
    page_texts = [p for p in text.split("\f") if p.strip()]
    nonempty_lines = [(i + 1, line.rstrip()) for i, line in enumerate(text.splitlines()) if line.strip()]
    start_numeric = [line for _, line in nonempty_lines if re.match(r"^\s*\d{1,3}(?:[a-z])?\s+\S", line, re.IGNORECASE)]
    standalone_numbers = [line for _, line in nonempty_lines if re.fullmatch(r"\s*\d{1,3}\s*", line)]
    number_sequences: dict[str, int] = {}
    exact_book_heading_lines: list[dict[str, Any]] = []
    numeric_line_examples: list[dict[str, Any]] = []
    for line_no, line in nonempty_lines:
        nums = re.findall(r"(?<![A-Za-z])\d{1,3}(?:[a-z])?(?::\d{1,3}(?:[a-z])?)?", line, flags=re.IGNORECASE)
        if nums:
            signature = " ".join(nums[:14])
            number_sequences[signature] = number_sequences.get(signature, 0) + 1
            if len(numeric_line_examples) < 40 and len(nums) >= 3:
                masked = re.sub(r"[^\W\d_]+", "W", line, flags=re.UNICODE)
                masked = re.sub(r"\d+", "N", masked)
                numeric_line_examples.append({"line": line_no, "number_tokens": nums[:14], "masked_shape": masked[:180]})
        normalized_line = norm_ascii(line.strip().replace(".", " "))
        heading = BOOK_LOOKUP.get(normalized_line.rstrip("."))
        if heading:
            exact_book_heading_lines.append({"line": line_no, "book": heading})
    line_signatures: dict[str, int] = {}
    for line in nonempty_lines:
        signature = re.sub(r"[^\W\d_]+", "W", line[1], flags=re.UNICODE)
        signature = re.sub(r"\d+", "N", signature)
        signature = re.sub(r"\s+", " ", signature).strip()
        if len(signature) > 100:
            signature = signature[:100]
        line_signatures[signature] = line_signatures.get(signature, 0) + 1
    flat = norm_ascii(text)
    book_hits = sorted({BOOK_LOOKUP[m.group(1)] for m in BOOK_PATTERN.finditer(flat)})
    return {
        "path": str(pdf.name),
        "size_bytes": pdf.stat().st_size,
        "sha256": sha256_file(pdf),
        "pages_pdfinfo": pages,
        "pages_with_extracted_text": len(page_texts),
        "extracted_characters": len(text),
        "extracted_words": len(re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b", text)),
        "text_layer_likely_usable": len(text.strip()) >= max(1000, (pages or 1) * 40),
        "known_spanish_bible_book_names_detected": len(book_hits),
        "known_book_names_detected": book_hits,
        "raw_mode_diagnostics": raw_diagnostics,
        "layout_diagnostics": {
            "nonempty_lines": len(nonempty_lines),
            "lines_starting_with_verse_like_number": len(start_numeric),
            "standalone_number_lines": len(standalone_numbers),
            "exact_book_heading_line_count": len(exact_book_heading_lines),
            "exact_book_heading_lines": exact_book_heading_lines[:100],
            "common_numeric_token_sequences": sorted(number_sequences.items(), key=lambda kv: (-kv[1], kv[0]))[:30],
            "masked_numeric_line_examples": numeric_line_examples,
            "common_redacted_line_signatures": sorted(line_signatures.items(), key=lambda kv: (-kv[1], kv[0]))[:30],
            "text_content_redacted": True,
        },
        "text_extraction": "PASS",
        "full_text_in_report": False,
    }


def dataset_audit() -> dict[str, Any]:
    if not DATA_PATH.is_file():
        return {"present": False, "status": "MISSING"}
    result: dict[str, Any] = {
        "present": True,
        "size_bytes": DATA_PATH.stat().st_size,
        "sha256": sha256_file(DATA_PATH),
        "expected_sha256_matches": sha256_file(DATA_PATH) == EXPECTED_PARQUET_SHA256,
    }
    try:
        import pyarrow.parquet as pq  # type: ignore
        table = pq.read_table(DATA_PATH)
        result["rows"] = table.num_rows
        result["columns"] = table.column_names
        required = {"translation", "translation_id", "language", "book_number", "book", "chapter", "verse", "verse_id", "text"}
        result["required_book_schema_present"] = required.issubset(set(table.column_names))
        def distinct_strings(name: str) -> list[str]:
            if name not in table.column_names:
                return []
            return sorted({str(x) for x in table[name].to_pylist() if x is not None})
        translations = distinct_strings("translation")
        translation_ids = distinct_strings("translation_id")
        result["translation_names"] = translations
        result["translation_ids"] = translation_ids
        result["book_count"] = len(distinct_strings("book"))
        result["btx_translation_identified"] = any("btx" in norm_ascii(t) or "biblia textual" in norm_ascii(t) for t in translations + translation_ids)
        result["text_content_emitted"] = False
        result["classification"] = "BTX" if result["btx_translation_identified"] else "NOT_CONFIRMED_AS_BTX"
    except Exception as exc:  # report the failure without misclassifying
        result["status"] = "UNREADABLE_BY_PYARROW"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("btx-source-audit.json"))
    args = parser.parse_args()
    report: dict[str, Any] = {
        "schema": "CAJITA_BTX_SOURCE_AUDIT/1.0",
        "repository_path": str(SOURCE_PATH.relative_to(ROOT)),
        "source_removal_performed": False,
        "source_removal_allowed": False,
        "conversion_performed": False,
        "certification": "NOT_GRANTED",
        "existing_structured_dataset": None,
        "source_archive": {},
        "extracted_candidates": [],
        "findings": [],
    }
    exit_code = 0
    if not SOURCE_PATH.is_file():
        report["source_archive"] = {"status": "MISSING"}
        report["findings"].append("BTX source archive is missing; conversion cannot proceed.")
        exit_code = 2
    else:
        tool = None
        try:
            tool = archive_tool()
            source_hash = sha256_file(SOURCE_PATH)
            integrity = run_checked([tool, "t", str(SOURCE_PATH)], timeout=120)
            with tempfile.TemporaryDirectory(prefix="btx-audit-") as temp:
                tmp = Path(temp)
                extracted = tmp / "outer"
                members = extract_archive(tool, SOURCE_PATH, extracted)
                member_inventory = []
                for entry in members:
                    rel = entry.get("Path", "")
                    path = extracted / Path(rel.replace("\\", "/"))
                    member_inventory.append({
                        "path": rel,
                        "size_bytes_listed": int(entry.get("Size", "0") or "0"),
                        "is_directory": entry.get("Folder") == "+",
                        "safe_path": True,
                        "extracted_file_found": path.is_file(),
                        "sha256": sha256_file(path) if path.is_file() else None,
                        "extension": path.suffix.lower(),
                    })
                discovered_archives: list[Path] = []
                for candidate in extracted.rglob("*"):
                    if candidate.is_file() and candidate.suffix.lower() in ARCHIVE_EXTS:
                        discovered_archives.append(candidate)
                nested_reports = []
                for index, candidate in enumerate(discovered_archives[:10]):
                    try:
                        child_dir = tmp / f"nested_{index}"
                        nested_members = extract_archive(tool, candidate, child_dir)
                        nested_reports.append({
                            "archive_path": str(candidate.relative_to(extracted)),
                            "members": len(nested_members),
                            "extracted_files": sum(1 for x in child_dir.rglob("*") if x.is_file()),
                            "status": "PASS",
                        })
                    except Exception as exc:
                        nested_reports.append({
                            "archive_path": str(candidate.relative_to(extracted)),
                            "status": "FAILED_OR_UNSAFE",
                            "error": f"{type(exc).__name__}: {exc}",
                        })
                all_files = [p for p in tmp.rglob("*") if p.is_file()]
                pdf_files = [p for p in all_files if p.suffix.lower() == ".pdf"]
                epub_files = [p for p in all_files if p.suffix.lower() == ".epub"]
                other_book_files = [p for p in all_files if p.suffix.lower() in {".mobi", ".azw", ".docx", ".html", ".htm"}]
                pdf_reports = []
                for pdf in pdf_files[:20]:
                    try:
                        pdf_reports.append(pdf_audit(pdf, tmp))
                    except Exception as exc:
                        pdf_reports.append({"path": pdf.name, "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
                report["source_archive"] = {
                    "status": "PASS" if source_hash == EXPECTED_SOURCE_SHA256 and integrity.returncode == 0 else "HASH_MISMATCH_OR_INTEGRITY_FAILURE",
                    "size_bytes": SOURCE_PATH.stat().st_size,
                    "sha256": source_hash,
                    "expected_sha256": EXPECTED_SOURCE_SHA256,
                    "expected_sha256_matches": source_hash == EXPECTED_SOURCE_SHA256,
                    "integrity_test": "PASS",
                    "archive_tool": tool,
                    "member_count": len(members),
                    "member_inventory": member_inventory,
                    "nested_archives": nested_reports,
                    "pdf_count_detected": len(pdf_files),
                    "epub_count_detected": len(epub_files),
                    "other_book_format_count_detected": len(other_book_files),
                    "pdf_audits": pdf_reports,
                }
                if source_hash != EXPECTED_SOURCE_SHA256 or integrity.returncode != 0:
                    report["findings"].append("Source archive integrity/hash gate did not pass.")
                    exit_code = 2
                if not pdf_files and not epub_files and not other_book_files:
                    report["findings"].append("No PDF/EPUB/DOCX/HTML book source was identified in the source archive or its first-level nested archives.")
                if pdf_files and not any(p.get("text_layer_likely_usable") for p in pdf_reports):
                    report["findings"].append("PDF detected but a useful text layer was not established; OCR or another extraction method may be required.")
        except Exception as exc:
            report["source_archive"] = {"status": "AUDIT_FAILED", "error": f"{type(exc).__name__}: {exc}"}
            report["findings"].append("Archive audit failed closed; no conversion or deletion was performed.")
            exit_code = 2

    report["existing_structured_dataset"] = dataset_audit()
    ds = report["existing_structured_dataset"]
    if ds.get("present") and ds.get("required_book_schema_present") and not ds.get("btx_translation_identified"):
        report["findings"].append("data.parquet has a book/chapter/verse schema but is not identified as BTX; it must not be substituted for the BTX text.")
    report["btx_book_conversion_status"] = "NOT_CONVERTED_BY_THIS_AUDIT"
    report["source_removal_decision"] = "DENY_UNTIL_BT X_BOOK_IS_BUILT_AND_INDEPENDENTLY_VALIDATED".replace(" ", "")
    report["final_gate"] = "AUDIT_ONLY_NO_DELETION_NO_CERTIFICATION"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
