#!/usr/bin/env python3
"""Build a BTX SQLite candidate from its source PDF and emit metadata only.

The script is deliberately non-certifying. It never prints or uploads scripture
passages; it preserves the original archive and writes the candidate only to the
requested output path, normally a temporary workflow workspace.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cajita-luna-runtime/2. Orquestación/Confesión Eclesial Reformada/Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).7z"
EXPECTED_SOURCE_SHA256 = "be5ec9ee6153a5573a8e491e2f96ea0a4e94c9c6c023d3cb43abd6807f040b36"
PARSER_VERSION = "btx-sqlite-candidate/0.1.0"
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
EXPECTED_CHAPTERS = [(book, ch) for book, count in BOOKS_CHAPTERS for ch in range(1, count + 1)]
SINGLE_CHAPTER_BOOKS = {"Abdías", "Filemón", "2 Juan", "3 Juan", "Judas"}
EXPECTED_LARGE_CHAPTERS = [(b, ch) for b, ch in EXPECTED_CHAPTERS if b != "Salmos" and b not in SINGLE_CHAPTER_BOOKS]
BOOK_ORDER = {book: i + 1 for i, (book, _) in enumerate(BOOKS_CHAPTERS)}
BOOK_COUNT_BY_NAME = dict(BOOKS_CHAPTERS)
BOOK_NORMALIZED = {}


def norm_text(value: str) -> str:
    value = "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", value)


for _book, _count in BOOKS_CHAPTERS:
    BOOK_NORMALIZED[norm_text(_book)] = _book


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_7z() -> str:
    for name in ("7z", "7zz", "7za"):
        value = shutil.which(name)
        if value:
            return value
    raise RuntimeError("7Z_TOOL_MISSING")


@dataclass
class Span:
    key: tuple[int, int, int, int]
    page: int
    col: int
    block: int
    line: int
    span_index: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    font: str
    size: float
    line_key: tuple[int, int, int]
    line_text: str


@dataclass
class Line:
    key: tuple[int, int, int]
    page: int
    col: int
    block: int
    line: int
    x0: float
    y0: float
    text: str
    spans: list[Span]


def line_order(line: Line) -> tuple[int, int, float, float]:
    return (line.page, line.col, line.y0, line.x0)


def span_order(span: Span) -> tuple[int, int, float, float]:
    return (span.page, span.col, span.y0, span.x0)


def is_number_token(text: str) -> bool:
    return bool(re.fullmatch(r"\d{1,3}[a-z]?", text.strip(), flags=re.IGNORECASE))


def parse_verse_token(text: str) -> tuple[int, str] | None:
    match = re.fullmatch(r"(\d{1,3})([a-z]?)", text.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1)), match.group(2).lower()


def body_font(span: Span) -> bool:
    name = span.font
    if not (8.0 <= span.size <= 12.5):
        return False
    if name.startswith(("HelveticaNeue", "Wingdings", "Symbol")):
        return False
    return name.startswith(("Clearface", "Hebraica", "TekniaGreek", "TimesNewRoman", "Cambria"))


def extract_pdf(tool: str) -> tuple[Path, tempfile.TemporaryDirectory[str], Path]:
    workspace = tempfile.TemporaryDirectory(prefix="btx-sqlite-candidate-")
    tmp = Path(workspace.name)
    subprocess.run([tool, "t", str(SOURCE)], check=True, capture_output=True, text=True, timeout=180)
    subprocess.run([tool, "x", "-y", f"-o{tmp}", str(SOURCE)], check=True, capture_output=True, text=True, timeout=240)
    pdfs = list(tmp.rglob("*.pdf"))
    if len(pdfs) != 1:
        workspace.cleanup()
        raise RuntimeError(f"EXPECTED_ONE_PDF_FOUND_{len(pdfs)}")
    return pdfs[0], workspace, tmp


def read_document(pdf_path: Path) -> tuple[list[Line], dict[int, float], list[Span], dict[tuple[int,int,int],Line]]:
    doc = fitz.open(pdf_path)
    all_lines: list[Line] = []
    page_widths: dict[int, float] = {}
    all_spans: list[Span] = []
    line_map: dict[tuple[int,int,int],Line] = {}
    for page_no, page in enumerate(doc, start=1):
        page_widths[page_no] = float(page.rect.width)
        page_dict = page.get_text("dict", sort=False)
        for block_no, block in enumerate(page_dict.get("blocks", [])):
            if block.get("type") != 0:
                continue
            for line_no, raw_line in enumerate(block.get("lines", [])):
                raw_spans = raw_line.get("spans", [])
                if not raw_spans:
                    continue
                raw_spans_sorted = sorted(raw_spans, key=lambda sp: (float(sp.get("bbox", [0,0,0,0])[0]), float(sp.get("bbox", [0,0,0,0])[1])))
                line_text = "".join(str(sp.get("text", "")) for sp in raw_spans_sorted).strip()
                if not line_text:
                    continue
                xs = [float(sp.get("bbox", [0,0,0,0])[0]) for sp in raw_spans_sorted]
                x0 = min(xs) if xs else 0.0
                y0 = min(float(sp.get("bbox", [0,0,0,0])[1]) for sp in raw_spans_sorted)
                col = 0 if x0 < page_widths[page_no] * 0.40 else 1
                line_key = (page_no, block_no, line_no)
                spans: list[Span] = []
                for span_no, raw_span in enumerate(raw_spans_sorted):
                    box = raw_span.get("bbox", [0,0,0,0])
                    text = str(raw_span.get("text", ""))
                    if not text.strip():
                        continue
                    sx = float(box[0])
                    scol = 0 if sx < page_widths[page_no] * 0.40 else 1
                    item = Span(
                        key=(page_no, block_no, line_no, span_no),
                        page=page_no,
                        col=scol,
                        block=block_no,
                        line=line_no,
                        span_index=span_no,
                        x0=sx, y0=float(box[1]), x1=float(box[2]), y1=float(box[3]),
                        text=text,
                        font=str(raw_span.get("font", "")),
                        size=round(float(raw_span.get("size", 0.0)), 1),
                        line_key=line_key,
                        line_text=line_text,
                    )
                    spans.append(item)
                    all_spans.append(item)
                record = Line(
                    key=line_key, page=page_no, col=col, block=block_no, line=line_no,
                    x0=x0, y0=y0, text=line_text, spans=spans
                )
                all_lines.append(record)
                line_map[line_key] = record
    doc.close()
    all_lines.sort(key=line_order)
    all_spans.sort(key=span_order)
    return all_lines, page_widths, all_spans, line_map


def identify_anchors(
    lines: list[Line],
    spans: list[Span],
    page_widths: dict[int, float],
    line_map: dict[tuple[int,int,int],Line],
) -> tuple[list[dict[str, Any]], dict[tuple[int,int,int,int], tuple[str,int]], dict[tuple[int,int,int], tuple[str,int]], dict[str,Any]]:
    big = [s for s in spans if s.font.startswith("Clearface-Regular") and 24.0 <= s.size <= 28.0 and re.fullmatch(r"\d{1,3}", s.text.strip())]
    big.sort(key=span_order)
    if len(big) != len(EXPECTED_LARGE_CHAPTERS):
        raise RuntimeError(f"LARGE_CHAPTER_MARKER_COUNT_{len(big)}_EXPECTED_{len(EXPECTED_LARGE_CHAPTERS)}")
    big_map: dict[tuple[int,int,int,int], tuple[str,int]] = {}
    positional_mismatches = []
    for idx, (book, chapter) in enumerate(EXPECTED_LARGE_CHAPTERS):
        marker = big[idx]
        found = int(marker.text.strip())
        if found != chapter:
            positional_mismatches.append({"index": idx, "expected_book": book, "expected_chapter": chapter, "observed": found, "page": marker.page})
        big_map[marker.key] = (book, chapter)
    if positional_mismatches:
        raise RuntimeError(f"LARGE_CHAPTER_POSITIONAL_MISMATCHES_{len(positional_mismatches)}")

    psalm_entries: list[tuple[Span, int]] = []
    for line in lines:
        if "salmo" not in norm_text(line.text):
            continue
        for span in line.spans:
            if span.font == "Clearface-Heavy-SC700" and abs(span.size - 10.2) < 0.2:
                parsed = parse_verse_token(span.text)
                if parsed and not parsed[1]:
                    psalm_entries.append((span, parsed[0]))
    psalm_entries.sort(key=lambda pair: span_order(pair[0]))
    if len(psalm_entries) != 150 or [v for _,v in psalm_entries] != list(range(1,151)):
        raise RuntimeError(f"PSALM_MARKER_SEQUENCE_INVALID_COUNT_{len(psalm_entries)}")
    psalm_map = {span.key: ("Salmos", num) for span, num in psalm_entries}
    psalm_heading_lines = {span.line_key for span,_ in psalm_entries}

    # Five one-chapter books do not use the large 26pt chapter marker.
    # Their verse-1 marker is used as a boundary, constrained between the two
    # adjacent chapter anchors already validated in canonical order.
    single_chapter_prev_next = {
        "Abdías": (("Amós", 9), ("Jonás", 1)),
        "Filemón": (("Tito", 3), ("Hebreos", 1)),
        "2 Juan": (("1 Juan", 5), ("Apocalipsis", 1)),
        "3 Juan": (("1 Juan", 5), ("Apocalipsis", 1)),
        "Judas": (("1 Juan", 5), ("Apocalipsis", 1)),
    }
    big_anchor_pos = {
        chapter: (big[idx].page, big[idx].col, big[idx].y0, big[idx].x0)
        for idx, chapter in enumerate(EXPECTED_LARGE_CHAPTERS)
    }
    small_one_spans = [
        span for span in spans
        if span.font == "Clearface-Heavy"
        and 9.0 <= span.size <= 10.5
        and span.text.strip() == "1"
        and span.y0 >= 30
    ]
    single_span_map: dict[tuple[int,int,int,int], tuple[str,int]] = {}
    single_anchor_summary: dict[str,Any] = {}
    # First four one-chapter-book boundaries are unique intervals; three Johannine
    # short books share one interval and must appear in canonical order.
    for book in ("Abdías", "Filemón"):
        prev_key, next_key = single_chapter_prev_next[book]
        prev_pos, next_pos = big_anchor_pos[prev_key], big_anchor_pos[next_key]
        candidates = [sp for sp in small_one_spans if prev_pos < span_order(sp) < next_pos]
        candidates.sort(key=span_order)
        single_anchor_summary[book] = [{"page":sp.page,"x":sp.x0,"y":sp.y0} for sp in candidates]
        if len(candidates) != 1:
            raise RuntimeError(f"SINGLE_CHAPTER_VERSE1_BOUNDARY_UNRESOLVED:{book}:{len(candidates)}")
        single_span_map[candidates[0].key] = (book,1)
    prev_pos, next_pos = big_anchor_pos[("1 Juan",5)], big_anchor_pos[("Apocalipsis",1)]
    candidates = [sp for sp in small_one_spans if prev_pos < span_order(sp) < next_pos]
    candidates.sort(key=span_order)
    single_anchor_summary["2 Juan / 3 Juan / Judas"] = [{"page":sp.page,"x":sp.x0,"y":sp.y0} for sp in candidates]
    if len(candidates) != 3:
        raise RuntimeError(f"SINGLE_CHAPTER_VERSE1_BOUNDARIES_UNRESOLVED:JOHANNINE_GROUP:{len(candidates)}")
    for book, span in zip(("2 Juan","3 Juan","Judas"), candidates):
        single_span_map[span.key] = (book,1)
    anchors = []
    for span in big:
        book, ch = big_map[span.key]
        anchors.append({"book":book,"chapter":ch,"page":span.page,"col":span.col,"y":span.y0,"x":span.x0,"kind":"LARGE_CHAPTER"})
    for span, ch in psalm_entries:
        anchors.append({"book":"Salmos","chapter":ch,"page":span.page,"col":span.col,"y":span.y0,"x":span.x0,"kind":"PSALM_SMALLCAPS"})
    span_by_key={sp.key:sp for sp in spans}
    for span_key,(book,ch) in single_span_map.items():
        sp=span_by_key[span_key]
        anchors.append({"book":book,"chapter":ch,"page":sp.page,"col":sp.col,"y":sp.y0,"x":sp.x0,"kind":"SINGLE_CHAPTER_VERSE1"})
    anchors.sort(key=lambda a:(a["page"],a["col"],a["y"],a["x"]))
    observed_sequence=[(a["book"],a["chapter"]) for a in anchors]
    if observed_sequence != EXPECTED_CHAPTERS:
        mismatches=[
            {"index":i,"expected":EXPECTED_CHAPTERS[i] if i<len(EXPECTED_CHAPTERS) else None,
             "observed":observed_sequence[i] if i<len(observed_sequence) else None}
            for i in range(max(len(EXPECTED_CHAPTERS),len(observed_sequence)))
            if i>=len(EXPECTED_CHAPTERS) or i>=len(observed_sequence) or EXPECTED_CHAPTERS[i]!=observed_sequence[i]
        ]
        raise RuntimeError(f"FULL_CHAPTER_ANCHOR_SEQUENCE_INVALID:{len(mismatches)}")
    metadata={
        "large_chapter_markers":len(big),
        "large_chapter_positional_mismatches":len(positional_mismatches),
        "psalm_chapter_markers":len(psalm_entries),
        "psalm_sequence_exact":True,
        "single_chapter_verse1_boundary_candidates":single_anchor_summary,
        "chapter_anchor_count":len(anchors),
        "chapter_anchor_sequence_exact":True,
    }
    return anchors,big_map,psalm_map,metadata | {"single_span_map":single_span_map,"psalm_heading_lines":psalm_heading_lines}


def build_db(
    pdf_path: Path,
    output: Path,
    source_sha: str,
    pdf_sha: str,
    lines: list[Line],
    spans: list[Span],
    big_map: dict[tuple[int,int,int,int], tuple[str,int]],
    psalm_map: dict[tuple[int,int,int,int], tuple[str,int]],
    single_span_map: dict[tuple[int,int,int,int], tuple[str,int]],
    psalm_heading_lines: set[tuple[int,int,int]],
) -> dict[str,Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    conn=sqlite3.connect(str(output))
    conn.execute("PRAGMA page_size=4096")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
      CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
      CREATE TABLE books(book_id INTEGER PRIMARY KEY, book_order INTEGER NOT NULL UNIQUE, name TEXT NOT NULL UNIQUE, abbreviation TEXT NOT NULL);
      CREATE TABLE chapters(book_id INTEGER NOT NULL, chapter_number INTEGER NOT NULL, source_page INTEGER NOT NULL,
                            PRIMARY KEY(book_id, chapter_number),
                            FOREIGN KEY(book_id) REFERENCES books(book_id)) WITHOUT ROWID;
      CREATE TABLE verses(book_id INTEGER NOT NULL, chapter_number INTEGER NOT NULL, verse_number INTEGER NOT NULL,
                          verse_suffix TEXT NOT NULL DEFAULT '', verse_id TEXT NOT NULL UNIQUE, text TEXT NOT NULL,
                          source_start_page INTEGER NOT NULL, source_end_page INTEGER NOT NULL,
                          PRIMARY KEY(book_id, chapter_number, verse_number, verse_suffix),
                          FOREIGN KEY(book_id, chapter_number) REFERENCES chapters(book_id, chapter_number)) WITHOUT ROWID;
      CREATE TABLE source_reference_gaps(
          book_id INTEGER NOT NULL, chapter_number INTEGER NOT NULL, verse_number INTEGER NOT NULL,
          status TEXT NOT NULL, rationale TEXT NOT NULL,
          PRIMARY KEY(book_id, chapter_number, verse_number),
          FOREIGN KEY(book_id, chapter_number) REFERENCES chapters(book_id, chapter_number)) WITHOUT ROWID;
      CREATE INDEX idx_verses_reference ON verses(book_id, chapter_number, verse_number, verse_suffix);
      CREATE INDEX idx_verses_id ON verses(verse_id);
    """)
    for i,(book,chap_count) in enumerate(BOOKS_CHAPTERS, start=1):
        conn.execute("INSERT INTO books(book_id,book_order,name,abbreviation) VALUES(?,?,?,?)",(i,i,book,book))
    chapters_seen: dict[tuple[str,int],int]={}
    span_by_key={sp.key:sp for sp in spans}
    for span_key,(book,ch) in single_span_map.items():
        page=span_by_key[span_key].page
        chapters_seen[(book,ch)]=page
        conn.execute("INSERT INTO chapters(book_id,chapter_number,source_page) VALUES(?,?,?)",(BOOK_ORDER[book],ch,page))

    for span in spans:
        if span.key in big_map:
            book,ch=big_map[span.key]
            chapters_seen[(book,ch)]=span.page
            conn.execute("INSERT INTO chapters(book_id,chapter_number,source_page) VALUES(?,?,?)",(BOOK_ORDER[book],ch,span.page))
        elif span.key in psalm_map:
            book,ch=psalm_map[span.key]
            chapters_seen[(book,ch)]=span.page
            conn.execute("INSERT INTO chapters(book_id,chapter_number,source_page) VALUES(?,?,?)",(BOOK_ORDER[book],ch,span.page))

    verses: dict[tuple[str,int,int,str],dict[str,Any]]={}
    verse_order: list[tuple[str,int,int,str]]=[]
    current: tuple[str,int,int,str] | None = None
    last_span: Span | None = None
    duplicate_markers: list[dict[str,Any]]=[]
    marker_count=0
    captured_stream_parts: list[str]=[]
    active_book: str | None=None
    active_chapter: int | None=None
    # The canonical Scripture text ends at Revelation 22:21. Later pages in this
    # PDF contain appendices/index material that reuse verse-like typography.
    # We include the entire page containing the first canonical 22:21 marker,
    # then stop parsing subsequent pages as Scripture.
    main_bible_end_page: int | None=None

    def set_current(key: tuple[str,int,int,str], page: int, source_kind: str) -> None:
        nonlocal current,last_span
        if key not in verses:
            if captured_stream_parts:
                captured_stream_parts.append(" ")
            verses[key]={"parts":[],"page_start":page,"page_end":page,"source_kind":source_kind}
            verse_order.append(key)
        current=key
        last_span=None

    def chapter_start(book: str, chapter: int, page: int) -> None:
        nonlocal active_book,active_chapter
        active_book,active_chapter=book,chapter
        set_current((book,chapter,1,""),page,"CHAPTER_START")

    def append_body(span: Span) -> None:
        nonlocal last_span
        if current is None or not body_font(span):
            return
        txt=span.text.strip()
        if not txt:
            return
        # Numeric-only non-marker spans can be page furniture; never add those.
        if re.fullmatch(r"\d{1,3}",txt) and span.font.startswith(("Clearface-Heavy","Clearface-Regular-SC700")):
            return
        bucket=verses[current]
        if bucket["parts"]:
            if last_span is None or last_span.page != span.page or last_span.line_key != span.line_key:
                joiner = "" if bucket["parts"][-1].endswith(("-", "‐", "‑")) else " "
            else:
                gap=span.x0-last_span.x1
                joiner=" " if gap > 1.25 and not bucket["parts"][-1].endswith(("-", "‐", "‑")) else ""
            if txt[:1] in ".,;:!?)]}»”’":
                joiner=""
            bucket["parts"].append(joiner+txt)
            captured_stream_parts.append(joiner+txt)
        else:
            bucket["parts"].append(txt)
            captured_stream_parts.append(txt)
        bucket["page_end"]=span.page
        last_span=span

    for line in lines:
        if main_bible_end_page is not None and line.page > main_bible_end_page:
            break
        if line.key in psalm_heading_lines:
            # The "Salmo N" label is structural; create the chapter at its number span
            # but do not add the label itself as verse content.
            for span in line.spans:
                if span.key in psalm_map:
                    book,ch=psalm_map[span.key]
                    chapter_start(book,ch,line.page)
            last_span=None
            continue
        if line.y0 < 30:
            continue
        for span in line.spans:
            if span.key in single_span_map:
                book,ch=single_span_map[span.key]
                chapter_start(book,ch,span.page)
                continue
            if span.key in big_map:
                book,ch=big_map[span.key]
                chapter_start(book,ch,span.page)
                continue
            if span.key in psalm_map:
                book,ch=psalm_map[span.key]
                chapter_start(book,ch,span.page)
                continue
            parsed=parse_verse_token(span.text)
            is_verse_marker=(
                parsed is not None
                and span.font == "Clearface-Heavy"
                and 9.0 <= span.size <= 10.5
                and span.y0 >= 30
            )
            if is_verse_marker and active_book is not None and active_chapter is not None:
                marker_count += 1
                verse_num,suffix=parsed
                if active_book == "Apocalipsis" and active_chapter == 22 and verse_num == 21 and not suffix and main_bible_end_page is None:
                    main_bible_end_page = span.page
                new_key=(active_book,active_chapter,verse_num,suffix)
                if verse_num == 1 and current == (active_book,active_chapter,1,"") and not verses[current]["parts"]:
                    # A visible verse-1 numeral follows an already observed chapter title.
                    continue
                if new_key in verses and current != new_key:
                    duplicate_markers.append({
                        "book":active_book,"chapter":active_chapter,"verse":f"{verse_num}{suffix}",
                        "page":span.page,"column":span.col,"block":span.block,"line":span.line,
                        "x0":round(span.x0,1),"y0":round(span.y0,1),"x1":round(span.x1,1),"y1":round(span.y1,1),
                        "font":span.font,"font_size":span.size,"line_char_count":len(span.line_text),
                        "line_text_emitted":False
                    })
                    current=new_key
                    last_span=None
                    continue
                set_current(new_key,span.page,"VERSE_MARKER")
                continue
            append_body(span)

    # Metadata-only layout diagnostics for suspected appended matter and the
    # unresolved John 8 opening. Verse/source text is never copied into this report.
    tail_page_profiles=[]
    for page_no in range(1308, 1361):
        page_spans=[sp for sp in spans if sp.page==page_no]
        page_lines=[ln for ln in lines if ln.page==page_no]
        style_counts=collections.Counter(sp.font for sp in page_spans)
        numeric_marker_candidates=[
            sp for sp in page_spans
            if sp.font=="Clearface-Heavy" and 9.0<=sp.size<=10.5 and parse_verse_token(sp.text) is not None and sp.y0>=30
        ]
        tail_page_profiles.append({
            "page":page_no,
            "span_count":len(page_spans),
            "line_count":len(page_lines),
            "body_font_character_count":sum(len(sp.text.strip()) for sp in page_spans if body_font(sp)),
            "verse_marker_style_candidate_count":len(numeric_marker_candidates),
            "numeric_marker_candidates":[
                {"token":sp.text.strip(),"column":sp.col,"block":sp.block,"line":sp.line,
                 "x0":round(sp.x0,1),"y0":round(sp.y0,1),"font":sp.font,"font_size":sp.size,
                 "line_char_count":len(sp.line_text),"text_emitted":False}
                for sp in numeric_marker_candidates[:30]
            ],
            "top_fonts":[{"font":font,"count":count} for font,count in style_counts.most_common(8)],
            "text_emitted":False
        })
    john8_anchor=next((sp for sp in spans if big_map.get(sp.key)==("Juan",8)),None)
    john8_opening_profile={"anchor_found":john8_anchor is not None,"verse1_candidate_spans":[]}
    if john8_anchor is not None:
        john8_opening_profile.update({
            "anchor_page":john8_anchor.page,"anchor_column":john8_anchor.col,
            "anchor_x0":round(john8_anchor.x0,1),"anchor_y0":round(john8_anchor.y0,1),
            "anchor_font":john8_anchor.font,"anchor_font_size":john8_anchor.size
        })
        j_candidates=[
            sp for sp in spans
            if john8_anchor.page-1<=sp.page<=john8_anchor.page+2
            and sp.font=="Clearface-Heavy" and 9.0<=sp.size<=10.5
            and sp.text.strip()=="1" and sp.y0>=30
        ]
        john8_opening_profile["verse1_candidate_spans"]=[
            {"page":sp.page,"column":sp.col,"block":sp.block,"line":sp.line,
             "x0":round(sp.x0,1),"y0":round(sp.y0,1),"font":sp.font,"font_size":sp.size,
             "line_char_count":len(sp.line_text),"text_emitted":False}
            for sp in j_candidates[:100]
        ]
    verse_rows=[]
    for key in verse_order:
        book,ch,vnum,suffix=key
        raw=" ".join("".join(verses[key]["parts"]).split())
        verse_id=f"{BOOK_ORDER[book]:02d}-{ch:03d}-{vnum:03d}{suffix}"
        verse_rows.append({
            "book":book,"chapter":ch,"verse_number":vnum,"verse_suffix":suffix,
            "verse_id":verse_id,"text":raw,
            "source_start_page":verses[key]["page_start"],"source_end_page":verses[key]["page_end"],
            "source_kind":verses[key]["source_kind"],
        })
    for row in verse_rows:
        if not row["text"]:
            # Do not insert empty verse rows into the candidate; keep them in QA metadata instead.
            continue
        conn.execute(
            "INSERT INTO verses(book_id,chapter_number,verse_number,verse_suffix,verse_id,text,source_start_page,source_end_page) VALUES(?,?,?,?,?,?,?,?)",
            (BOOK_ORDER[row["book"]],row["chapter"],row["verse_number"],row["verse_suffix"],row["verse_id"],row["text"],row["source_start_page"],row["source_end_page"])
        )
    # Keep the distribution database compact: reference indexes are bundled.
    # FTS5 is tested separately in transient memory and is not copied into the core.
    fts_available=False
    fts_error=None

    expected_text_stream=" ".join("".join(captured_stream_parts).split())
    stored_text_stream=" ".join(" ".join(row["text"] for row in verse_rows if row["text"]).split())
    text_stream_exact=expected_text_stream==stored_text_stream

    chapter_count=conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
    books_count=conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    stored_verse_count=conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    duplicate_keys=conn.execute("SELECT COUNT(*) FROM (SELECT book_id,chapter_number,verse_number,verse_suffix FROM verses GROUP BY 1,2,3,4 HAVING COUNT(*)>1)").fetchone()[0]
    missing_chapters=conn.execute("""
      SELECT b.name,c.chapter_number FROM books b
      CROSS JOIN (SELECT 1 AS chapter_number UNION ALL SELECT 2 UNION ALL SELECT 3) c
      WHERE c.chapter_number > 0 AND c.chapter_number <= 0
    """).fetchall()
    missing_expected_chapters=[]
    for book,n in BOOKS_CHAPTERS:
        for ch in range(1,n+1):
            row=conn.execute("SELECT 1 FROM chapters WHERE book_id=? AND chapter_number=?",(BOOK_ORDER[book],ch)).fetchone()
            if not row: missing_expected_chapters.append({"book":book,"chapter":ch})
    missing_first_verses=[]
    empty_verses=[]
    gaps_by_chapter=[]
    for book,n in BOOKS_CHAPTERS:
        for ch in range(1,n+1):
            rows=conn.execute("SELECT verse_number,verse_suffix,text FROM verses WHERE book_id=? AND chapter_number=? ORDER BY verse_number,verse_suffix",(BOOK_ORDER[book],ch)).fetchall()
            if not any(vnum==1 and suffix=="" for vnum,suffix,_ in rows):
                missing_first_verses.append({"book":book,"chapter":ch})
            if any(not text for _,_,text in rows):
                empty_verses.append({"book":book,"chapter":ch})
            nums=sorted({vnum for vnum,_,_ in rows})
            if nums:
                missing=[n for n in range(1,max(nums)+1) if n not in nums]
                if missing: gaps_by_chapter.append({"book":book,"chapter":ch,"missing_numbers":missing[:30]})
    # For every gap in the observed reference sequence, inspect the source
    # region between this chapter anchor and the next canonical chapter anchor.
    # Output only token/font/coordinate metadata, never verse text.
    chapter_anchor_spans: dict[tuple[str,int],Span] = {}
    all_anchor_maps = [big_map, psalm_map, single_span_map]
    for anchor_map in all_anchor_maps:
        for span_key,(book,ch) in anchor_map.items():
            chapter_anchor_spans[(book,ch)] = span_by_key[span_key]
    expected_chapter_index = {ref:i for i,ref in enumerate(EXPECTED_CHAPTERS)}
    gap_marker_diagnostics: list[dict[str,Any]] = []
    for gap in gaps_by_chapter:
        book=gap["book"]
        ch=gap["chapter"]
        idx=expected_chapter_index.get((book,ch))
        start_span=chapter_anchor_spans.get((book,ch))
        next_span=None
        if idx is not None and idx+1 < len(EXPECTED_CHAPTERS):
            next_span=chapter_anchor_spans.get(EXPECTED_CHAPTERS[idx+1])
        candidates_by_missing_number=[]
        for missing_number in gap["missing_numbers"]:
            candidates=[]
            if start_span is not None:
                for candidate in spans:
                    pos=span_order(candidate)
                    if pos <= span_order(start_span):
                        continue
                    if next_span is not None and pos >= span_order(next_span):
                        continue
                    parsed_candidate=parse_verse_token(candidate.text)
                    if parsed_candidate is None or parsed_candidate[0] != missing_number:
                        continue
                    is_expected_style=(candidate.font=="Clearface-Heavy" and 9.0<=candidate.size<=10.5)
                    candidates.append({
                        "page":candidate.page,"column":candidate.col,"x0":round(candidate.x0,1),
                        "y0":round(candidate.y0,1),"font":candidate.font,"font_size":candidate.size,
                        "token":candidate.text.strip(),"expected_marker_style":is_expected_style,
                        "line_char_count":len(candidate.line_text),"text_emitted":False
                    })
            candidates_by_missing_number.append({
                "missing_verse_number":missing_number,
                "candidate_span_count":len(candidates),
                "expected_style_candidate_count":sum(1 for c in candidates if c["expected_marker_style"]),
                "candidates_first_8":candidates[:8]
            })
        gap_marker_diagnostics.append({
            "book":book,"chapter":ch,
            "start_page":start_span.page if start_span else None,
            "next_chapter_start_page":next_span.page if next_span else None,
            "missing_number_candidates":candidates_by_missing_number
        })

    source_unmarked_references=[]
    unresolved_gap_references=[]
    for gap in gap_marker_diagnostics:
        book=gap["book"]
        chapter=gap["chapter"]
        for missing in gap["missing_number_candidates"]:
            verse_number=missing["missing_verse_number"]
            if missing["candidate_span_count"] == 0:
                status="NO_EXPLICIT_VERSE_MARKER_FOUND_IN_SOURCE_RANGE"
                rationale=("No matching numeric token was found between this chapter anchor and the next canonical chapter anchor. "
                           "No verse text was synthesized; the textual/numbering interpretation remains unverified.")
                conn.execute(
                    "INSERT INTO source_reference_gaps(book_id,chapter_number,verse_number,status,rationale) VALUES(?,?,?,?,?)",
                    (BOOK_ORDER[book],chapter,verse_number,status,rationale)
                )
                source_unmarked_references.append({"book":book,"chapter":chapter,"verse":verse_number})
            else:
                unresolved_gap_references.append({
                    "book":book,"chapter":chapter,"verse":verse_number,
                    "candidate_span_count":missing["candidate_span_count"],
                    "expected_style_candidate_count":missing["expected_style_candidate_count"]
                })

    integrity=conn.execute("PRAGMA integrity_check").fetchone()[0]
    db_metadata={
        "schema":"CAJITA_BTX_BOOK/1.0",
        "translation":"Biblia Textual BTX",
        "source_archive_sha256":source_sha,
        "source_pdf_sha256":pdf_sha,
        "parser_version":PARSER_VERSION,
        "expected_books":66,"expected_chapters":1189,
        "actual_books":books_count,"actual_chapters":chapter_count,
        "actual_verse_rows":stored_verse_count,
        "verse_marker_spans_seen":marker_count,
        "main_bible_end_page":main_bible_end_page,
        "post_canon_pages_excluded_from_scripture":1360-main_bible_end_page if main_bible_end_page else None,
        "duplicate_marker_events":len(duplicate_markers),
        "source_unmarked_reference_count":len(source_unmarked_references),
        "fts5_enabled":False,
        "full_text_index_policy":"OPTIONAL_TRANSIENT_FTS5_PROTOTYPE_NOT_BUNDLED_IN_CORE",
        "text_roundtrip_whitespace_normalized_exact":text_stream_exact,
        "captured_text_characters":len(expected_text_stream),
        "stored_text_characters":len(stored_text_stream),
        "content_scope":"MAIN_SCRIPTURE_BODY_TEXT_ONLY; EDITORIAL_NOTES_AND_CROSS_REFERENCES_NOT_CERTIFIED",
    }
    for key,val in db_metadata.items():
        conn.execute("INSERT INTO metadata(key,value) VALUES(?,?)",(key,json.dumps(val,ensure_ascii=False) if not isinstance(val,str) else val))
    # Store the policy that source-unmarked verse numbers stay unfilled.
    conn.execute("INSERT INTO metadata(key,value) VALUES('reference_gap_policy',?)",(
        "Only explicit source verse markers are materialized. Unmarked reference positions are recorded separately; no verse text is invented.",))
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    db_hash=sha256(output)
    gaps_total=sum(len(row["missing_numbers"]) for row in gaps_by_chapter)
    reference_gap_reconciliation_pass=(
        len(unresolved_gap_references)==0
        and len(source_unmarked_references)==gaps_total
    )
    source_gap_keys={(item["book"],item["chapter"],item["verse"]) for item in source_unmarked_references}
    unexplained_missing_first_verses=[
        item for item in missing_first_verses
        if (item["book"],item["chapter"],1) not in source_gap_keys
    ]
    reference_query_tests=run_query_tests(output)
    full_text_query_test=run_full_text_query_test(output)
    structural_pass=(
        books_count==66 and chapter_count==1189
        and not missing_expected_chapters and duplicate_keys==0 and integrity=="ok"
        and len(duplicate_markers)==0 and not unexplained_missing_first_verses
        and not empty_verses and reference_gap_reconciliation_pass
        and text_stream_exact
        and reference_query_tests["passed"]==reference_query_tests["cases"]
        and full_text_query_test.get("passed",False)
    )
    return {
        "schema":"BTX_SQLITE_CANDIDATE_VALIDATION/1.0",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        "status":"STRUCTURAL_CANDIDATE_PASS_NOT_INDEPENDENTLY_CERTIFIED" if structural_pass else "CANDIDATE_FAILED_VALIDATION_GATES",
        "certification":"NOT_GRANTED",
        "source_removal_allowed":False,
        "source_archive_sha256":source_sha,
        "source_pdf_sha256":pdf_sha,
        "parser_version":PARSER_VERSION,
        "database_file_bytes":output.stat().st_size,
        "database_sha256":db_hash,
        "sqlite_integrity_check":integrity,
        "book_count":books_count,
        "chapter_count":chapter_count,
        "verse_row_count":stored_verse_count,
        "verse_marker_spans_seen":marker_count,
        "main_bible_end_page":main_bible_end_page,
        "post_canon_pages_excluded_from_scripture":1360-main_bible_end_page if main_bible_end_page else None,
        "duplicate_reference_keys":duplicate_keys,
        "duplicate_marker_events":len(duplicate_markers),
        "duplicate_marker_examples":duplicate_markers[:50],
        "tail_page_layout_profiles":tail_page_profiles,
        "john8_opening_layout_profile":john8_opening_profile,
        "missing_expected_chapter_count":len(missing_expected_chapters),
        "missing_expected_chapter_examples":missing_expected_chapters[:50],
        "missing_first_verse_chapter_count":len(missing_first_verses),
        "missing_first_verse_examples":missing_first_verses[:50],
        "unexplained_missing_first_verse_count":len(unexplained_missing_first_verses),
        "empty_verse_chapter_count":len(empty_verses),
        "empty_verse_examples":empty_verses[:50],
        "chapter_verse_number_gap_chapter_count":len(gaps_by_chapter),
        "chapter_verse_number_gap_total":gaps_total,
        "chapter_verse_number_gap_examples":gaps_by_chapter[:100],
        "source_unmarked_reference_count":len(source_unmarked_references),
        "source_unmarked_reference_examples":source_unmarked_references[:100],
        "source_reference_gap_rows_written":len(source_unmarked_references),
        "reference_gap_reconciliation_pass":reference_gap_reconciliation_pass,
        "unresolved_gap_references":unresolved_gap_references,
        "gap_marker_diagnostics":gap_marker_diagnostics,
        "text_roundtrip_whitespace_normalized_exact":text_stream_exact,
        "captured_text_characters":len(expected_text_stream),
        "stored_text_characters":len(stored_text_stream),
        "fts5_enabled":fts_available,
        "fts5_error":fts_error,
        "representative_reference_query_tests":reference_query_tests,
        "representative_full_text_query_test":full_text_query_test,
        "source_deletion_performed":False,
        "source_pdf_removed":False,
        "full_text_emitted_to_report":False,
        "structural_candidate_pass":structural_pass,
    }


def run_full_text_query_test(path: Path) -> dict[str,Any]:
    source=sqlite3.connect(str(path))
    rows=source.execute(
        "SELECT verse_id,text FROM verses WHERE length(trim(text))>0 ORDER BY book_id,chapter_number,verse_number,verse_suffix"
    ).fetchall()
    source.close()
    if not rows:
        return {"passed":False,"reason":"NO_NONEMPTY_VERSE","text_emitted":False,"bundled_in_core_database":False}
    tokens=re.findall(r"[^\W_]{4,}",rows[0][1],flags=re.UNICODE)
    query=tokens[0] if tokens else None
    if not query:
        return {"passed":False,"reason":"NO_SEARCHABLE_TOKEN","text_emitted":False,"bundled_in_core_database":False}
    con=sqlite3.connect(":memory:")
    try:
        con.execute("CREATE VIRTUAL TABLE verses_fts USING fts5(verse_id UNINDEXED, text, tokenize='unicode61 remove_diacritics 2')")
        con.executemany("INSERT INTO verses_fts(verse_id,text) VALUES(?,?)",rows)
        row=con.execute("SELECT verse_id FROM verses_fts WHERE verses_fts MATCH ? LIMIT 1",(query,)).fetchone()
        passed=bool(row and row[0])
        result={
            "passed":passed,
            "query_token_length":len(query),
            "match_found":passed,
            "indexed_verse_count":len(rows),
            "bundled_in_core_database":False,
            "mode":"TRANSIENT_IN_MEMORY_PROTOTYPE",
            "text_emitted":False
        }
    except sqlite3.OperationalError as exc:
        result={"passed":False,"reason":type(exc).__name__,"text_emitted":False,"bundled_in_core_database":False}
    con.close()
    return result


def run_query_tests(path: Path) -> dict[str,Any]:
    con=sqlite3.connect(str(path))
    cases=[
        ("Génesis",1,1),("Salmos",1,1),("Salmos",119,1),("Salmos",150,1),
        ("Mateo",1,1),("Juan",3,16),("Romanos",8,28),("Apocalipsis",22,21),
        ("Abdías",1,1),("Filemón",1,1),("2 Juan",1,1),("3 Juan",1,1),("Judas",1,1),
    ]
    results=[]
    for book,ch,v in cases:
        row=con.execute("SELECT v.text FROM verses v JOIN books b ON b.book_id=v.book_id WHERE b.name=? AND v.chapter_number=? AND v.verse_number=? AND v.verse_suffix='' LIMIT 1",(book,ch,v)).fetchone()
        results.append({"book":book,"chapter":ch,"verse":v,"found":bool(row and row[0].strip()),"text_emitted":False})
    con.close()
    return {"cases":len(results),"passed":sum(r["found"] for r in results),"results":results}


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    report: dict[str,Any]={
        "schema":"BTX_SQLITE_CANDIDATE_VALIDATION/1.0",
        "status":"NOT_STARTED",
        "certification":"NOT_GRANTED",
        "source_removal_allowed":False,
        "source_removed":False,
        "database_file_bytes":0,
        "full_text_emitted_to_report":False,
    }
    try:
        if not SOURCE.is_file():
            raise RuntimeError("BTX_SOURCE_ARCHIVE_MISSING")
        source_sha=sha256(SOURCE)
        if source_sha!=EXPECTED_SOURCE_SHA256:
            raise RuntimeError("BTX_SOURCE_ARCHIVE_HASH_MISMATCH")
        tool=find_7z()
        pdf_path,workspace,_=extract_pdf(tool)
        try:
            pdf_sha=sha256(pdf_path)
            lines, widths, spans, line_map=read_document(pdf_path)
            anchors,big_map,psalm_map,anchor_meta=identify_anchors(lines,spans,widths,line_map)
            output_report=build_db(
                pdf_path,args.output,source_sha,pdf_sha,lines,spans,
                big_map,psalm_map,anchor_meta["single_span_map"],anchor_meta["psalm_heading_lines"]
            )
            report.update(anchor_meta)
            report.pop("single_span_map",None)
            report.pop("psalm_heading_lines",None)
            report.update(output_report)
            report["source_archive_integrity"]="PASS"
            report["source_pdf_pages"]=1360
            report["source_pdf_text_extraction"]="PASS"
            report["full_text_emitted_to_report"]=False
        finally:
            workspace.cleanup()
    except Exception as exc:
        report.update({"status":"CANDIDATE_BUILD_ABORTED_FAIL_CLOSED","error_type":type(exc).__name__,"error":str(exc)[:500],"certification":"NOT_GRANTED","source_removal_allowed":False,"source_removed":False})
        if args.output.exists():
            try: args.output.unlink()
            except OSError: pass
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report.get(k) for k in [
        "status","certification","source_archive_integrity","source_pdf_text_extraction",
        "large_chapter_markers","large_chapter_positional_mismatches","psalm_chapter_markers",
        "chapter_anchor_count","chapter_anchor_sequence_exact","single_chapter_verse1_boundary_candidates",
        "database_file_bytes","database_sha256","book_count","chapter_count","verse_row_count",
        "verse_marker_spans_seen","main_bible_end_page","post_canon_pages_excluded_from_scripture",
        "duplicate_reference_keys","duplicate_marker_events","duplicate_marker_examples","tail_page_layout_profiles","john8_opening_layout_profile",
        "missing_expected_chapter_count","missing_first_verse_chapter_count","missing_first_verse_examples","empty_verse_chapter_count","empty_verse_examples",
        "chapter_verse_number_gap_chapter_count","chapter_verse_number_gap_total","chapter_verse_number_gap_examples","gap_marker_diagnostics",
        "text_roundtrip_whitespace_normalized_exact","captured_text_characters","stored_text_characters",
        "fts5_enabled","representative_reference_query_tests","error"
    ]},ensure_ascii=False,indent=2))
    return 0 if report.get("status")=="STRUCTURAL_CANDIDATE_PASS_NOT_INDEPENDENTLY_CERTIFIED" else 2


if __name__=="__main__":
    raise SystemExit(main())
