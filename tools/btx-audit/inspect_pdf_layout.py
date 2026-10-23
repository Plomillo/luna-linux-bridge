#!/usr/bin/env python3
"""Analyze BTX PDF layout for a future parser; never emits verse text."""
from __future__ import annotations

import collections
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cajita-luna-runtime/2. Orquestación/Confesión Eclesial Reformada/Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).7z"
EXPECTED_SHA256 = "be5ec9ee6153a5573a8e491e2f96ea0a4e94c9c6c023d3cb43abd6807f040b36"
BOOKS = [
 "Génesis","Éxodo","Levítico","Números","Deuteronomio","Josué","Jueces","Rut","1 Samuel","2 Samuel",
 "1 Reyes","2 Reyes","1 Crónicas","2 Crónicas","Esdras","Nehemías","Ester","Job","Salmos","Proverbios",
 "Eclesiastés","Cantares","Isaías","Jeremías","Lamentaciones","Ezequiel","Daniel","Oseas","Joel","Amós",
 "Abdías","Jonás","Miqueas","Nahúm","Habacuc","Sofonías","Hageo","Zacarías","Malaquías","Mateo","Marcos",
 "Lucas","Juan","Hechos","Romanos","1 Corintios","2 Corintios","Gálatas","Efesios","Filipenses","Colosenses",
 "1 Tesalonicenses","2 Tesalonicenses","1 Timoteo","2 Timoteo","Tito","Filemón","Hebreos","Santiago","1 Pedro",
 "2 Pedro","1 Juan","2 Juan","3 Juan","Judas","Apocalipsis"
]
BOOK_LOOKUP = {re.sub(r"\\s+", " ", book.casefold()).strip(): book for book in BOOKS}

def main() -> int:
    out: dict[str, Any] = {
        "schema": "BTX_PDF_LAYOUT_PROFILE/1.0",
        "source_sha256_expected": EXPECTED_SHA256,
        "source_integrity": "UNVERIFIED",
        "pdf_open": "UNVERIFIED",
        "certification": "NOT_GRANTED",
        "full_text_emitted": False,
    }
    tool = shutil.which("7z") or shutil.which("7zz") or shutil.which("7za")
    if not SOURCE.is_file() or not tool:
        out["error"] = "SOURCE_OR_7Z_TOOL_MISSING"
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2
    import hashlib
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    out["source_sha256"] = digest
    out["source_integrity"] = "PASS" if digest == EXPECTED_SHA256 else "FAIL"
    if digest != EXPECTED_SHA256:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    with tempfile.TemporaryDirectory(prefix="btx-layout-") as t:
        root = Path(t)
        subprocess.run([tool, "t", str(SOURCE)], check=True, capture_output=True, text=True, timeout=120)
        subprocess.run([tool, "x", "-y", f"-o{root}", str(SOURCE)], check=True, capture_output=True, text=True, timeout=180)
        pdfs = list(root.rglob("*.pdf"))
        if len(pdfs) != 1:
            out["pdf_count"] = len(pdfs)
            out["pdf_open"] = "FAIL"
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 2
        doc = fitz.open(pdfs[0])
        font_counter = collections.Counter()
        numeric_span_fonts = collections.Counter()
        body_chars_by_font = collections.Counter()
        exact_heading_spans: list[dict[str, Any]] = []
        exact_heading_lines: list[dict[str, Any]] = []
        numeric_span_samples: list[dict[str, Any]] = []
        numeric_line_count = 0
        text_char_count = 0
        text_word_count = 0
        for pno, page in enumerate(doc, start=1):
            page_dict = page.get_text("dict", sort=False)
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                block_lines = []
                for line in block.get("lines", []):
                    line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                    if line_text:
                        block_lines.append(line_text)
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        size = round(float(span.get("size", 0.0)), 1)
                        font = str(span.get("font", "unknown"))
                        font_counter[(font, size)] += 1
                        text_char_count += len(text)
                        text_word_count += len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))
                        if len(text) > 3:
                            body_chars_by_font[size] += len(text)
                        if re.fullmatch(r"\d{1,3}[a-z]?", text, flags=re.IGNORECASE):
                            numeric_span_fonts[(size, font)] += 1
                            if len(numeric_span_samples) < 60:
                                numeric_span_samples.append({
                                    "page": pno, "font_size_pt": size, "font": font,
                                    "bbox_rounded": [round(float(x), 1) for x in span.get("bbox", [])],
                                    "numeric_token": text,
                                })
                for line_text in block_lines:
                    normalized = re.sub(r"[\s.:]+", " ", line_text.casefold()).strip()
                    for book in BOOKS:
                        if normalized == re.sub(r"[\s.:]+", " ", book.casefold()).strip():
                            exact_heading_lines.append({"page": pno, "book": book})
                            break
                block_text = " ".join(block_lines)
                if re.fullmatch(r"\s*\d{1,3}\s*", block_text):
                    numeric_line_count += 1
                for book in BOOKS:
                    if re.fullmatch(r"\s*" + re.escape(book) + r"[.:]?\s*", block_text, flags=re.IGNORECASE):
                        exact_heading_spans.append({"page": pno, "book": book})
                        break
        doc.close()
        out.update({
            "pdf_open": "PASS",
            "pdf_pages": len(fitz.open(pdfs[0])),
            "text_char_count_from_spans": text_char_count,
            "text_word_count_from_spans": text_word_count,
            "font_styles": [
                {"font": font, "size_pt": size, "span_count": count}
                for (font, size), count in font_counter.most_common(60)
            ],
            "numeric_only_span_font_distribution": [
                {"size_pt": size, "font": font, "count": count}
                for (size, font), count in numeric_span_fonts.most_common(60)
            ],
            "numeric_only_span_sample_coordinates": numeric_span_samples,
            "exact_book_heading_lines": exact_heading_lines,
            "exact_book_heading_blocks": exact_heading_spans,
            "numeric_only_block_count": numeric_line_count,
            "body_char_distribution_by_font_size_pt": [
                {"size_pt": size, "characters": count}
                for size, count in body_chars_by_font.most_common(30)
            ],
            "layout_only": True,
            "verse_text_emitted": False,
            "conversion_performed": False,
            "source_removed": False,
            "status": "LAYOUT_PROFILE_READY_PARSER_STILL_UNVALIDATED",
        })
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
