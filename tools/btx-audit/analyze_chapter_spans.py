#!/usr/bin/env python3
"""Measure large numeric spans against the canonical 66-book chapter sequence.
Never emits the Bible's verse text; output is structural metadata only.
"""
from __future__ import annotations

import collections
import hashlib
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
BOOKS_CHAPTERS = [
 ("Génesis",50),("Éxodo",40),("Levítico",27),("Números",36),("Deuteronomio",34),
 ("Josué",24),("Jueces",21),("Rut",4),("1 Samuel",31),("2 Samuel",24),
 ("1 Reyes",22),("2 Reyes",25),("1 Crónicas",29),("2 Crónicas",36),("Esdras",10),
 ("Nehemías",13),("Ester",10),("Job",42),("Salmos",150),("Proverbios",31),
 ("Eclesiastés",12),("Cantares",8),("Isaías",66),("Jeremías",52),("Lamentaciones",5),
 ("Ezequiel",48),("Daniel",12),("Oseas",14),("Joel",3),("Amós",9),("Abdías",1),
 ("Jonás",4),("Miqueas",7),("Nahúm",3),("Habacuc",3),("Sofonías",3),("Hageo",2),
 ("Zacarías",14),("Malaquías",4),("Mateo",28),("Marcos",16),("Lucas",24),("Juan",21),
 ("Hechos",28),("Romanos",16),("1 Corintios",16),("2 Corintios",13),("Gálatas",6),
 ("Efesios",6),("Filipenses",4),("Colosenses",4),("1 Tesalonicenses",5),
 ("2 Tesalonicenses",3),("1 Timoteo",6),("2 Timoteo",4),("Tito",3),("Filemón",1),
 ("Hebreos",13),("Santiago",5),("1 Pedro",5),("2 Pedro",3),("1 Juan",5),("2 Juan",1),
 ("3 Juan",1),("Judas",1),("Apocalipsis",22)
]
EXPECTED = [(book, ch) for book, n in BOOKS_CHAPTERS for ch in range(1, n + 1)]
ALTERNATE_CHAPTER_MARKERS = {"Salmos", "Abdías", "Filemón", "2 Juan", "3 Juan", "Judas"}
EXPECTED_LARGE = [(book, ch) for book, ch in EXPECTED if book not in ALTERNATE_CHAPTER_MARKERS]


def find_7z() -> str:
    tool = shutil.which("7z") or shutil.which("7zz") or shutil.which("7za")
    if not tool:
        raise RuntimeError("7Z_TOOL_MISSING")
    return tool


def lcs_match(expected: list[int], observed: list[dict[str, Any]]) -> tuple[list[tuple[int,int]], int]:
    # Each observation can match an expected chapter if the printed number agrees.
    # LCS provides an upper bound on sequence alignment; it does not certify text segmentation.
    n, m = len(expected), len(observed)
    prev = [0] * (m + 1)
    trace = [bytearray(m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        for j in range(1, m + 1):
            if expected[i - 1] == observed[j - 1]["value"]:
                cur[j] = prev[j - 1] + 1
                trace[i][j] = 1
            elif prev[j] >= cur[j - 1]:
                cur[j] = prev[j]
                trace[i][j] = 2
            else:
                cur[j] = cur[j - 1]
                trace[i][j] = 3
        prev = cur
    pairs: list[tuple[int, int]] = []
    i, j = n, m
    while i and j:
        d = trace[i][j]
        if d == 1 and expected[i - 1] == observed[j - 1]["value"]:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif d == 2:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs, prev[m]


def main() -> int:
    report: dict[str, Any] = {
        "schema": "BTX_CHAPTER_SPAN_ALIGNMENT/1.0",
        "source_removal_performed": False,
        "conversion_performed": False,
        "certification": "NOT_GRANTED",
        "verse_text_emitted": False,
        "expected_standard_protestant_chapters": len(EXPECTED),
    }
    if not SOURCE.is_file():
        report["status"] = "SOURCE_MISSING"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    report["source_sha256"] = digest
    report["source_sha256_matches_registry"] = digest == EXPECTED_SHA256
    if digest != EXPECTED_SHA256:
        report["status"] = "SOURCE_HASH_MISMATCH"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    tool = find_7z()
    with tempfile.TemporaryDirectory(prefix="btx-chapter-audit-") as t:
        tmp = Path(t)
        subprocess.run([tool, "t", str(SOURCE)], check=True, capture_output=True, text=True, timeout=120)
        subprocess.run([tool, "x", "-y", f"-o{tmp}", str(SOURCE)], check=True, capture_output=True, text=True, timeout=180)
        pdfs = list(tmp.rglob("*.pdf"))
        if len(pdfs) != 1:
            report["status"] = "PDF_COUNT_UNEXPECTED"
            report["pdf_count"] = len(pdfs)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
        pdf = fitz.open(pdfs[0])
        candidates: list[dict[str, Any]] = []
        style_counts: collections.Counter[str] = collections.Counter()
        verse_style_counts: collections.Counter[str] = collections.Counter()
        verse_suffix_counts: collections.Counter[str] = collections.Counter()
        small_number_by_value: collections.Counter[str] = collections.Counter()
        small_number_pages: dict[int, collections.Counter[str]] = collections.defaultdict(collections.Counter)
        all_numeric_style_counts: collections.Counter[str] = collections.Counter()
        large_noninteger_counts: collections.Counter[str] = collections.Counter()
        large_noninteger_samples: list[dict[str, Any]] = []
        page_size_counts: dict[int, int] = collections.Counter()
        salmo_heading_candidates: list[dict[str, Any]] = []
        for pno, page in enumerate(pdf, start=1):
            pw = float(page.rect.width)
            page_spans = []
            data = page.get_text("dict", sort=False)
            for block_no, block in enumerate(data.get("blocks", [])):
                if block.get("type") != 0:
                    continue
                for line_no, line in enumerate(block.get("lines", [])):
                    line_spans = line.get("spans", [])
                    line_text = "".join(str(span.get("text", "")) for span in line_spans)
                    if 515 <= pno <= 675 and re.search(r"salmo", line_text, flags=re.IGNORECASE):
                        numeric_tokens = []
                        for span in line_spans:
                            token = str(span.get("text", "")).strip()
                            if re.fullmatch(r"\d{1,3}[a-z]?", token, flags=re.IGNORECASE):
                                box = span.get("bbox", [0,0,0,0])
                                numeric_tokens.append({
                                    "token": token,
                                    "font": str(span.get("font", "")),
                                    "size": round(float(span.get("size", 0)), 1),
                                    "x": round(float(box[0]), 1),
                                    "y": round(float(box[1]), 1),
                                })
                        salmo_heading_candidates.append({
                            "page": pno,
                            "block": block_no,
                            "line": line_no,
                            "contains_salmo_label": True,
                            "line_char_count": len(line_text),
                            "line_max_font_size": max([round(float(sp.get("size",0)),1) for sp in line_spans] or [0]),
                            "numeric_tokens": numeric_tokens,
                            "line_text_emitted": False,
                        })
                    for span in line_spans:
                        value_text = span.get("text", "").strip()
                        if not value_text:
                            continue
                        font = str(span.get("font", ""))
                        size = round(float(span.get("size", 0)), 1)
                        box = span.get("bbox", [0,0,0,0])
                        if re.fullmatch(r"\d{1,3}[a-z]?", value_text, flags=re.IGNORECASE) and 8.5 <= size <= 12.0:
                            all_numeric_style_counts[f"{font}|{size:g}"] += 1
                            small_number_by_value[value_text.casefold()] += 1
                            small_number_pages[pno][value_text.casefold()] += 1
                            if 9.0 <= size <= 11.5 and ("Heavy" in font or "Bold" in font):
                                verse_suffix_counts[f"{font}|{size:g}|{value_text[-1].isalpha()}"] += 1
                        if size >= 18.0 and not re.fullmatch(r"\d{1,3}", value_text):
                            if re.fullmatch(r"[\d]{1,3}[a-zA-Z*†‡.,:;]?", value_text):
                                large_noninteger_counts[f"{font}|{size:g}|{value_text}"] += 1
                                if len(large_noninteger_samples) < 100:
                                    large_noninteger_samples.append({"page": pno, "x": round(float(box[0]),1), "y": round(float(box[1]),1), "font": font, "size": size, "token": value_text})
                            continue
                        if not re.fullmatch(r"\d{1,3}", value_text):
                            continue
                        item = {
                            "value": int(value_text),
                            "page": pno,
                            "x": round(float(box[0]),1),
                            "y": round(float(box[1]),1),
                            "font": font,
                            "size": size,
                            "column": "left" if float(box[0]) < pw * 0.40 else "right",
                        }
                        if size >= 18.0:
                            page_spans.append(item)
                            style_counts[f"{font}|{size:g}"] += 1
                        if size >= 9.0 and size <= 11.5 and ("Heavy" in font or "Bold" in font):
                            verse_style_counts[f"{font}|{size:g}"] += 1
            # Reading order is column-major for a standard two-column page.
            page_spans.sort(key=lambda x:(0 if x["column"]=="left" else 1, x["y"], x["x"]))
            page_size_counts[pno] = len(page_spans)
            candidates.extend(page_spans)
        pdf.close()
        observed_values = [x["value"] for x in candidates]
        expected_values = [ch for _, ch in EXPECTED]
        all_pairs, all_matched = lcs_match(expected_values, candidates)
        all_matched_by_expected = {i:j for i,j in all_pairs}
        all_unmatched_expected = [
            {"index":i,"book":book,"chapter":ch}
            for i,(book,ch) in enumerate(EXPECTED) if i not in all_matched_by_expected
        ]
        expected_large_values = [ch for _, ch in EXPECTED_LARGE]
        pairs, matched = lcs_match(expected_large_values, candidates)
        matched_by_expected = {i:j for i,j in pairs}
        unmatched_expected = [
            {"index":i,"book":book,"chapter":ch}
            for i,(book,ch) in enumerate(EXPECTED_LARGE) if i not in matched_by_expected
        ]
        matched_observed = {j:i for i,j in pairs}
        unmatched_observed = [c for j,c in enumerate(candidates) if j not in matched_observed]
        expected_by_book: dict[str,dict[str,int]] = {}
        chapter_page_ranges: dict[str,dict[str,Any]] = {}
        for i,(book,ch) in enumerate(EXPECTED_LARGE):
            row = expected_by_book.setdefault(book, {"expected_large_markers":0,"matched_large_markers":0})
            row["expected_large_markers"] += 1
            if i in matched_by_expected:
                row["matched_large_markers"] += 1
                candidate = candidates[matched_by_expected[i]]
                bounds = chapter_page_ranges.setdefault(book, {"first_matched_chapter":ch,"first_page":candidate["page"],"last_matched_chapter":ch,"last_page":candidate["page"]})
                bounds["last_matched_chapter"] = ch
                bounds["last_page"] = candidate["page"]
        report.update({
            "pdf_pages": len(page_size_counts),
            "large_numeric_span_count": len(candidates),
            "salmo_heading_candidate_count": len(salmo_heading_candidates),
            "salmo_heading_candidates": salmo_heading_candidates,
            "large_numeric_span_style_counts": style_counts.most_common(100),
            "small_bold_numeric_span_style_counts": verse_style_counts.most_common(60),
            "small_bold_numeric_span_suffix_counts": verse_suffix_counts.most_common(100),
            "all_small_numeric_span_style_counts": all_numeric_style_counts.most_common(100),
            "small_numeric_tokens_by_value": small_number_by_value.most_common(100),
            "small_numeric_one_pages": [{"page":p,"ones":counts["1"],"twos":counts["2"],"threes":counts["3"]} for p,counts in sorted(small_number_pages.items()) if counts["1"]],
            "large_noninteger_numeric_style_counts": large_noninteger_counts.most_common(100),
            "large_noninteger_numeric_samples": large_noninteger_samples,
            "expected_sequence_lcs_matches": all_matched,
            "expected_sequence_coverage_percent": round(all_matched / len(EXPECTED) * 100, 2),
            "expected_large_marker_chapters": len(EXPECTED_LARGE),
            "large_marker_sequence_lcs_matches": matched,
            "large_marker_coverage_percent": round(matched / len(EXPECTED_LARGE) * 100, 2),
            "large_marker_unmatched_expected_count": len(unmatched_expected),
            "large_marker_unmatched_expected_first_100": unmatched_expected[:100],
            "large_marker_unmatched_observed_count": len(unmatched_observed),
            "large_marker_unmatched_observed_first_100": unmatched_observed[:100],
            "all_canon_unmatched_expected_count": len(all_unmatched_expected),
            "all_canon_unmatched_expected_first_150": all_unmatched_expected[:150],
            "alternate_chapter_marker_books": sorted(ALTERNATE_CHAPTER_MARKERS),
            "chapter_page_ranges_by_book": chapter_page_ranges,
            "book_chapter_alignment": [
                {"book":book, **row, "large_marker_coverage_percent":round(100*row["matched_large_markers"]/row["expected_large_markers"],2)}
                for book,row in expected_by_book.items()
            ],
            "large_numeric_candidates_first_100": candidates[:100],
            "large_numeric_candidates_last_100": candidates[-100:],
            "candidate_counts_by_page_sample": {
                str(p): page_size_counts[p] for p in sorted(page_size_counts)
                if p in {1,2,3,20,40,80,100,200,300,400,500,600,700,800,900,1000,1100,1200,1300,1350,1360}
            },
            "status": "STRUCTURAL_ALIGNMENT_DIAGNOSTIC_ONLY",
        })
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
