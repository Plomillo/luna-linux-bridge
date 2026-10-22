from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import fitz
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus.tableofcontents import TableOfContents

from .engine import normalize_extracted_text, require_input, sha256_file, utc_now, write_json_new


FOLIO_RE = re.compile(r"^\d{1,4}$")
CHAPTER_RE = re.compile(
    r"^(CAP[IÍ]TULO|CHAPTER)\s+(\d{1,3})(?:\s*[:.\-–—]\s*|\s+)?(.*)$",
    re.IGNORECASE,
)
PART_RE = re.compile(
    r"^(PARTE|PART)\s+(?:UNO|DOS|TRES|CUATRO|CINCO|SEIS|SIETE|OCHO|NUEVE|DIEZ|"
    r"ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|[IVXLCDM]{1,8}|\d{1,2})\b.*$",
    re.IGNORECASE,
)
TOC_WORD_RE = re.compile(
    r"^(?:CONTENIDOS?|TABLE OF CONTENTS|CONTENTS|ÍNDICE GENERAL)$",
    re.IGNORECASE,
)
TOC_LEADER_RE = re.compile(r"(?:\.{2,}|…{1,})\s*\d{1,4}\s*$")


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _folio_for_page(page: fitz.Page) -> int | None:
    """Find one unambiguous isolated Arabic folio near the bottom edge."""
    height = page.rect.height
    candidates: set[int] = set()
    for word in page.get_text("words"):
        y0, y1, token = float(word[1]), float(word[3]), str(word[4]).strip()
        if y0 >= height * 0.86 and y1 <= height * 0.995 and FOLIO_RE.fullmatch(token):
            value = int(token)
            if value > 0:
                candidates.add(value)
    return next(iter(candidates)) if len(candidates) == 1 else None


def _page_toc_like(lines: list[str]) -> bool:
    if not lines:
        return False
    if any(TOC_WORD_RE.fullmatch(line.strip(" .:;")) for line in lines[:8]):
        return True
    chapter_like = sum(bool(CHAPTER_RE.match(line)) for line in lines[:24])
    leader_like = sum(bool(TOC_LEADER_RE.search(line)) for line in lines[:30])
    return chapter_like >= 2 or leader_like >= 2


def _trim_chapter_heading(suffix: str) -> str:
    """Trim recognized first-sentence spillover from navigation labels, never from body text."""
    value = re.sub(r"\s+", " ", suffix).strip(" :-–—")
    if re.search(r"\b(?:adaptado de|adapted from|reimpreso de|reprinted from|con permiso de|with permission)\b", value, re.IGNORECASE):
        return ""
    body_cues = (
        r"\s+Mi objetivo principal\b.*$",
        r"\s+Las consideraciones de\b.*$",
        r"\s+en su estudio sociológico\b.*$",
        r"\s+Debido a que\b.*$",
        r"\s+En psicoterapia expresiva\b.*$",
        r"\s+Las tareas fundamentales\b.*$",
        r"\s+En el contexto de comparar\b.*$",
        r"\s+Para las modalidades de tratamiento\b.*$",
        r"\s+en línea con los esfuerzos anteriores\b.*$",
        r"(?<=terminológicos\.)\s+Una\b.*$",
        r"\s+Como ya he mencionado\b.*$",
        r"\s+El$",
    )
    for cue in body_cues:
        value = re.sub(cue, "", value, flags=re.IGNORECASE).strip(" :-–—")
    if re.search(r"\s+(?:el|la|los|las|de|del|para|en|con)$", value, re.IGNORECASE):
        value = re.sub(r"\s+(?:el|la|los|las|de|del|para|en|con)$", "", value, flags=re.IGNORECASE).rstrip()
        if value:
            value += "…"
    return value


def _heading_from_page(lines: list[str], toc_like: bool) -> dict[str, Any] | None:
    if toc_like or not lines:
        return None
    for index, line in enumerate(lines[:6]):
        clean = re.sub(r"\s+", " ", line).strip(" \t\r\n:;")
        if not clean:
            continue
        if index <= 2 and PART_RE.match(clean) and len(clean) <= 180:
            return {"kind": "part", "level": 0, "title": clean, "source_line": clean}
        match = CHAPTER_RE.match(clean)
        if index <= 3 and match and len(clean) <= 240:
            number = int(match.group(2))
            suffix = _trim_chapter_heading(match.group(3))
            if not suffix:
                continue
            title = f"Capítulo {number}: {suffix}" if suffix else f"Capítulo {number}"
            source_line = f"Capítulo {number}: {suffix}" if suffix else f"Capítulo {number}"
            return {
                "kind": "chapter", "level": 1, "chapter_number": number,
                "title": title[:180], "source_line": source_line,
            }
    return None


def analyze_pdf_order(input_path: Path) -> dict[str, Any]:
    """Use printed folios to propose a full order; weak or partial evidence never moves pages."""
    source = require_input(input_path)
    rows: list[dict[str, Any]] = []
    with fitz.open(source) as document:
        if document.is_encrypted:
            raise ValueError("Encrypted PDFs require a separately authorized workflow.")
        for index, page in enumerate(document):
            text = page.get_text("text", sort=True)
            raw_lines = [line for line in text.splitlines() if line.strip()]
            lines = [re.sub(r"\s+", " ", line).strip() for line in raw_lines]
            toc_like = _page_toc_like(lines)
            heading = _heading_from_page(lines, toc_like)
            rows.append({
                "pdf_page": index + 1,
                "printed_folio": _folio_for_page(page),
                "text_characters": len(text.strip()),
                "page_text_sha256": _sha_text(text),
                "toc_like_page": toc_like,
                "heading": heading,
            })

    page_count = len(rows)
    folios = [row["printed_folio"] for row in rows]
    observed = [value for value in folios if value is not None]
    missing_indexes = [index for index, value in enumerate(folios) if value is None]
    coverage = len(observed) / max(page_count, 1)
    unique = len(set(observed)) == len(observed)
    contiguous = bool(observed) and max(observed) - min(observed) + 1 == len(observed)
    edge_only_missing = True
    if missing_indexes and observed:
        first_numbered = min(index for index, value in enumerate(folios) if value is not None)
        last_numbered = max(index for index, value in enumerate(folios) if value is not None)
        edge_only_missing = all(index < first_numbered or index > last_numbered for index in missing_indexes)
    increasing = all(
        folios[i] < folios[i + 1]
        for i in range(page_count - 1)
        if folios[i] is not None and folios[i + 1] is not None
    ) and edge_only_missing

    strong_evidence = (
        unique and contiguous and edge_only_missing
        and (coverage == 1.0 or (coverage >= 0.80 and len(observed) >= 20))
    )
    expected_order = list(range(1, page_count + 1))
    if strong_evidence:
        prefix = [index + 1 for index in range(page_count) if index < min(
            (i for i, value in enumerate(folios) if value is not None), default=page_count
        )]
        suffix_start = max((i for i, value in enumerate(folios) if value is not None), default=-1) + 1
        suffix = [index + 1 for index in range(suffix_start, page_count)]
        numbered_indexes = [
            index for index, value in enumerate(folios) if value is not None
        ]
        numbered_sorted = [index + 1 for index in sorted(numbered_indexes, key=lambda idx: int(folios[idx]))]
        proposed_order = prefix + numbered_sorted + suffix
        if proposed_order == expected_order:
            recommendation = "KEEP_SOURCE_ORDER"
            confidence = "HIGH"
            explanation = (
                "Printed folios are unique, contiguous and increasing; unnumbered pages, if any, "
                "are confined to the front or end. No physical page movement is justified."
            )
        else:
            recommendation = "ORDER_BY_PRINTED_FOLIO"
            confidence = "HIGH"
            explanation = (
                "Printed folios establish a unique, contiguous order. Unnumbered pages are confined "
                "to the front or end and stay in place; numbered pages are sorted by their printed folios."
            )
    else:
        proposed_order = expected_order
        recommendation = "MANUAL_REVIEW_REQUIRED"
        confidence = "INSUFFICIENT"
        reasons = []
        if coverage < 0.80 or len(observed) < min(20, page_count):
            reasons.append(f"only {len(observed)} of {page_count} pages have unambiguous bottom folios")
        if not unique:
            reasons.append("detected folios are duplicated or ambiguous")
        if not contiguous:
            reasons.append("the folio range is not contiguous")
        if not edge_only_missing:
            reasons.append("one or more unnumbered pages occur inside the numbered sequence")
        explanation = (
            "Automatic page movement is blocked because "
            + "; ".join(reasons or ["folio evidence is insufficient"])
            + ". The source sequence is preserved pending human review."
        )

    chapters = []
    for row in rows:
        heading = row["heading"]
        if heading:
            chapters.append({
                "pdf_page": row["pdf_page"],
                "printed_folio": row["printed_folio"],
                **heading,
            })
    chapter_numbers = [item["chapter_number"] for item in chapters if "chapter_number" in item]
    chapter_anomalies = []
    for position in range(1, len(chapter_numbers)):
        previous, current = chapter_numbers[position - 1], chapter_numbers[position]
        if current < previous:
            chapter_anomalies.append({
                "position": position + 1, "previous_chapter": previous,
                "next_chapter": current,
                "note": "Candidate headings decrease numerically; review context before inferring a page move.",
            })

    return {
        "schema": "LOUKSNA_DOCUMENT_WORKBENCH_ORDER_ANALYSIS/2.0",
        "observed_at_utc": utc_now(),
        "input_name": source.name,
        "input_sha256": sha256_file(source),
        "input_size_bytes": source.stat().st_size,
        "page_count": page_count,
        "printed_folio_detection": {
            "detected_pages": len(observed),
            "coverage_ratio": round(coverage, 4),
            "unique": unique,
            "contiguous_range": contiguous,
            "missing_pages": [index + 1 for index in missing_indexes],
            "missing_pages_confined_to_edges": edge_only_missing,
            "minimum": min(observed) if observed else None,
            "maximum": max(observed) if observed else None,
            "increasing_in_physical_order": increasing,
        },
        "recommendation": recommendation,
        "confidence": confidence,
        "explanation": explanation,
        "page_order_would_change": proposed_order != expected_order,
        "recommended_page_order_1_based": proposed_order,
        "chapter_candidates": chapters,
        "chapter_number_anomalies": chapter_anomalies,
        "table_of_contents_like_pages": [row["pdf_page"] for row in rows if row["toc_like_page"]],
        "page_evidence": [
            {key: value for key, value in row.items() if key not in ("heading",)}
            | ({"heading": row["heading"]["title"]} if row["heading"] else {})
            for row in rows
        ],
        "invariants": {
            "input_modified": False,
            "complete_page_permutation": len(proposed_order) == page_count and set(proposed_order) == set(expected_order),
            "auto_order_only_if_folios_unique_contiguous_and_unambiguous": True,
        },
        "status": (
            "PASS_ORDER_CONFIRMED" if recommendation == "KEEP_SOURCE_ORDER"
            else "PASS_ORDER_EVIDENCE_STRONG" if recommendation == "ORDER_BY_PRINTED_FOLIO"
            else "REVIEW_REQUIRED_FAIL_CLOSED"
        ),
    }


def create_safe_ordered_copy(
    input_path: Path, output_path: Path, analysis_path: Path, audit_path: Path,
) -> dict[str, Any]:
    source = require_input(input_path)
    analysis_file = analysis_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    audit_file = audit_path.expanduser().resolve()
    if not analysis_file.is_file():
        raise FileNotFoundError(f"Order analysis not found: {analysis_file}")
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    if analysis.get("input_sha256") != sha256_file(source):
        raise ValueError("Order analysis SHA-256 does not match the exact source.")
    if int(analysis.get("page_count", -1)) < 1:
        raise ValueError("Order analysis lacks a valid page count.")
    if output == source or output in (analysis_file, audit_file) or audit_file in (source, analysis_file):
        raise ValueError("Source, output, analysis and audit paths must all be distinct.")
    if output.exists() or audit_file.exists():
        raise FileExistsError("Refusing to overwrite an existing output PDF or audit.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.stem + ".tmp" + output.suffix)
    if temporary.exists():
        raise FileExistsError(f"Refusing to overwrite temporary output: {temporary}")

    source_hash_before = sha256_file(source)
    page_count = int(analysis["page_count"])
    expected = list(range(1, page_count + 1))
    if analysis.get("recommendation") == "ORDER_BY_PRINTED_FOLIO":
        order = analysis.get("recommended_page_order_1_based")
        if not isinstance(order, list) or len(order) != page_count or set(order) != set(expected):
            raise ValueError("Proposed order is not a complete permutation; no page was moved.")
        order = [int(item) for item in order]
        operation = "REORDER_BY_VERIFIED_PRINTED_FOLIOS"
        page_changed = order != expected
    elif analysis.get("recommendation") == "KEEP_SOURCE_ORDER":
        order, operation, page_changed = expected, "COPY_CONFIRMED_SOURCE_ORDER", False
    else:
        order, operation, page_changed = expected, "COPY_ONLY_ORDER_UNRESOLVED", False

    try:
        if not page_changed:
            with source.open("rb") as src, temporary.open("xb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
        else:
            with fitz.open(source) as document:
                original_text_hashes = [_sha_text(page.get_text("text", sort=True)) for page in document]
                document.select([item - 1 for item in order])
                document.save(str(temporary), garbage=3, deflate=True)
            with fitz.open(temporary) as verify:
                actual = [_sha_text(page.get_text("text", sort=True)) for page in verify]
            wanted = [original_text_hashes[item - 1] for item in order]
            if actual != wanted:
                raise RuntimeError("Post-reorder text sequence does not match the complete proposed permutation.")

        with fitz.open(temporary) as verified:
            if len(verified) != page_count:
                raise RuntimeError("Output page count changed.")
            output_text_hashes = [_sha_text(page.get_text("text", sort=True)) for page in verified]
        if sha256_file(source) != source_hash_before:
            raise RuntimeError("Source SHA-256 changed during processing.")
        if not page_changed:
            with fitz.open(source) as original:
                original_text_hashes = [_sha_text(page.get_text("text", sort=True)) for page in original]
            if output_text_hashes != original_text_hashes:
                raise RuntimeError("Copy-only operation changed extracted page text.")
        temporary.replace(output)
        status = (
            "PASS_PAGES_REORDERED_BY_FOLIOS" if page_changed
            else "PASS_SOURCE_ORDER_CONFIRMED" if operation == "COPY_CONFIRMED_SOURCE_ORDER"
            else "REVIEW_REQUIRED_NO_PAGES_MOVED"
        )
        report = {
            "schema": "LOUKSNA_DOCUMENT_WORKBENCH_ORDER_APPLICATION/2.0",
            "observed_at_utc": utc_now(),
            "operation": operation,
            "status": status,
            "verification": "PASS_STRUCTURAL_SEQUENCE_CHECKS",
            "input_name": source.name,
            "input_sha256": source_hash_before,
            "output_name": output.name,
            "output_sha256": sha256_file(output),
            "source_page_count": page_count,
            "output_page_count": page_count,
            "page_order_changed": page_changed,
            "recommended_page_order_1_based": order if page_changed else None,
            "order_evidence": {
                "recommendation": analysis.get("recommendation"),
                "confidence": analysis.get("confidence"),
                "printed_folio_detection": analysis.get("printed_folio_detection"),
                "explanation": analysis.get("explanation"),
            },
            "source_modified": False,
            "limitations": [
                "Page movement is permitted only when printed folios establish a complete, unique, contiguous sequence.",
                "When evidence is insufficient, the PDF is copied byte-for-byte and no page is moved.",
                "Structural verification does not certify translation accuracy or editorial correctness.",
            ],
        }
        write_json_new(audit_file, report)
        return report
    except Exception:
        temporary.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        raise


def _escape(value: str) -> str:
    import html
    return html.escape(value, quote=False)


class AcademicReadingDoc(SimpleDocTemplate):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._outline_counter = 0
        self._has_part = False

    def beforeDocument(self) -> None:
        # TableOfContents.multiBuild renders multiple passes. Reset outline state on
        # every pass so the first chapter cannot inherit a stale nested outline level.
        self._outline_counter = 0
        self._has_part = False
        super().beforeDocument()

    def afterFlowable(self, flowable: Any) -> None:
        if not isinstance(flowable, Paragraph):
            return
        name = flowable.style.name
        if name not in ("PartHeading", "ChapterHeading"):
            return
        label = flowable.getPlainText().strip()
        if not label:
            return
        if name == "PartHeading":
            level = 0
            toc_level = 0
            self._has_part = True
        else:
            level = 1 if self._has_part and self._outline_counter else 0
            toc_level = 1 if self._has_part else 0
        self._outline_counter += 1
        key = f"louksna-section-{self._outline_counter}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(label[:200], key, level=level, closed=False)
        self.notify("TOCEntry", (toc_level, label, self.page))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    navy = colors.HexColor("#183247")
    muted = colors.HexColor("#657580")
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=24, leading=30, alignment=TA_CENTER, textColor=navy,
            spaceAfter=10 * mm, splitLongWords=True,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=13, leading=19, alignment=TA_CENTER, textColor=muted,
            spaceAfter=8 * mm,
        ),
        "cover_author": ParagraphStyle(
            "CoverAuthor", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=13, leading=18, alignment=TA_CENTER, textColor=navy,
            spaceAfter=3 * mm,
        ),
        "h1": ParagraphStyle(
            "ReaderHeading1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=18, leading=23, textColor=navy, spaceBefore=8 * mm,
            spaceAfter=5 * mm, keepWithNext=True,
        ),
        "part": ParagraphStyle(
            "PartHeading", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=16, leading=21, textColor=navy, spaceBefore=8 * mm,
            spaceAfter=5 * mm, keepWithNext=True,
        ),
        "chapter": ParagraphStyle(
            "ChapterHeading", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, leading=18, textColor=navy, spaceBefore=6 * mm,
            spaceAfter=4 * mm, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReaderBody", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10.3, leading=15.2, alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#222B30"), spaceAfter=7,
            splitLongWords=True, allowWidows=0, allowOrphans=0,
        ),
        "marker": ParagraphStyle(
            "SourcePageMarker", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.5, leading=10, textColor=muted, alignment=TA_LEFT,
            spaceBefore=4 * mm, spaceAfter=3 * mm, keepWithNext=True,
        ),
        "note": ParagraphStyle(
            "EditorialNote", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.5, leading=14, textColor=colors.HexColor("#3C494F"),
            spaceAfter=7, alignment=TA_LEFT,
        ),
        "toc0": ParagraphStyle(
            "ReaderTOC0", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=15, textColor=navy,
            leftIndent=0, firstLineIndent=0, spaceBefore=5,
        ),
        "toc1": ParagraphStyle(
            "ReaderTOC1", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=13, textColor=colors.HexColor("#35454F"),
            leftIndent=12 * mm, firstLineIndent=0, spaceBefore=2,
        ),
    }


def _header_footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    if doc.page > 1:
        width, height = A4
        navy = colors.HexColor("#183247")
        muted = colors.HexColor("#657580")
        canvas.setStrokeColor(colors.HexColor("#D7DDE0"))
        canvas.setLineWidth(0.55)
        canvas.line(doc.leftMargin, height - 13 * mm, width - doc.rightMargin, height - 13 * mm)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(navy)
        canvas.drawString(doc.leftMargin, height - 10.5 * mm, "KERNBERG · EDICIÓN DE LECTURA")
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(width - doc.rightMargin, 9 * mm, str(doc.page))
        canvas.setStrokeColor(colors.HexColor("#D7DDE0"))
        canvas.line(doc.leftMargin, 13 * mm, width - doc.rightMargin, 13 * mm)
    canvas.restoreState()


def create_academic_reading_edition(
    input_path: Path, output_path: Path, analysis_path: Path, audit_path: Path,
    title: str = "Trastornos de personalidad severos",
) -> dict[str, Any]:
    source = require_input(input_path)
    analysis_file = analysis_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    audit_file = audit_path.expanduser().resolve()
    if not analysis_file.is_file():
        raise FileNotFoundError(f"Order analysis not found: {analysis_file}")
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    if analysis.get("input_sha256") != sha256_file(source):
        raise ValueError("Analysis SHA-256 does not match the exact input PDF.")
    if output == source or output in (analysis_file, audit_file) or audit_file in (source, analysis_file):
        raise ValueError("Source, output, analysis and audit paths must all be distinct.")
    if output.exists() or audit_file.exists():
        raise FileExistsError("Refusing to overwrite an existing academic PDF or audit.")
    output.parent.mkdir(parents=True, exist_ok=True)

    source_pages: list[dict[str, Any]] = []
    source_text_characters = 0
    with fitz.open(source) as document:
        if document.is_encrypted:
            raise ValueError("Encrypted PDFs require a separately authorized workflow.")
        for index, page in enumerate(document):
            text = normalize_extracted_text(page.get_text("text", sort=True))
            source_text_characters += len(text)
            source_pages.append({"page": index + 1, "text": text})
    if not any(page["text"] for page in source_pages):
        raise ValueError("No extractable text found; refusing an empty reading edition.")

    headings = {int(item["pdf_page"]): item for item in analysis.get("chapter_candidates", [])}
    styles = _styles()
    toc = TableOfContents()
    toc.levelStyles = [styles["toc0"], styles["toc1"]]
    story: list[Any] = [
        Spacer(1, 42 * mm),
        Paragraph("TRASTORNOS DE PERSONALIDAD<br/>SEVEROS", styles["cover_title"]),
        Paragraph("EDICIÓN TIPOGRÁFICA DE LECTURA", styles["cover_subtitle"]),
        Spacer(1, 8 * mm),
        Paragraph("OTTO F. KERNBERG", styles["cover_author"]),
        Spacer(1, 28 * mm),
        Paragraph(
            "Texto recompuesto para facilitar la lectura académica. Cada página del PDF de origen "
            "mantiene una referencia cruzada para permitir la comprobación con el original.",
            styles["cover_subtitle"],
        ),
        Spacer(1, 10 * mm),
        Paragraph("LOUKSNA DOCUMENT WORKBENCH · COPIA DE ESTUDIO", styles["note"]),
        PageBreak(),
        Paragraph("Nota editorial y criterios de lectura", styles["h1"]),
        Paragraph(
            "Esta edición recompone el texto extraíble con una jerarquía tipográfica uniforme, "
            "márgenes amplios, interlineado legible, marcadores de navegación e índice. Se normalizan "
            "espacios y saltos de línea; los guiones al final de renglón se unen solo cuando el patrón "
            "es inequívoco. No se reescribe el contenido clínico, no se certifica la traducción y no "
            "se corrigen silenciosamente citas, conceptos o referencias.",
            styles["note"],
        ),
        Paragraph(
            "La paginación de esta copia es nueva. Los rótulos «Fuente PDF página N» permiten volver "
            "a la página física correspondiente del archivo de origen. Para verificar diagramación, "
            "figuras, tablas, notas al pie o detalles visuales, consulte el PDF original.",
            styles["note"],
        ),
        Paragraph("Contenido", styles["h1"]),
        toc,
        PageBreak(),
    ]

    nonempty_pages = 0
    for page_data in source_pages:
        page_num = page_data["page"]
        text = page_data["text"]
        heading = headings.get(page_num)
        story.append(Paragraph(f"Fuente PDF página {page_num}", styles["marker"]))
        if not text:
            story.append(Paragraph(
                "No se extrajo texto de esta página. Revise la fuente; puede requerir OCR.",
                styles["note"],
            ))
            continue
        nonempty_pages += 1
        body_text = text
        if heading:
            source_line = str(heading.get("source_line", "")).strip()
            if source_line:
                lines = body_text.splitlines()
                needle = re.sub(r"\s+", " ", source_line).strip().casefold()
                for line_index, line in enumerate(lines[:6]):
                    if re.sub(r"\s+", " ", line).strip().casefold() == needle:
                        del lines[line_index]
                        body_text = "\n".join(lines).strip()
                        break
            style = styles["part"] if heading.get("kind") == "part" else styles["chapter"]
            story.append(Paragraph(_escape(str(heading.get("title", "")),), style))
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body_text) if part.strip()]
        for paragraph in paragraphs:
            story.append(Paragraph(_escape(paragraph).replace("\n", "<br/>"), styles["body"]))

    temporary = output.with_name(output.stem + ".tmp" + output.suffix)
    if temporary.exists():
        raise FileExistsError(f"Refusing to overwrite temporary output: {temporary}")
    try:
        doc = AcademicReadingDoc(
            str(temporary), pagesize=A4,
            rightMargin=23 * mm, leftMargin=23 * mm,
            topMargin=20 * mm, bottomMargin=18 * mm,
            title=title, author="Otto F. Kernberg",
            subject="Academic reading edition; extracted text; human review required",
            keywords="Kernberg, personalidad, edición de lectura, PDF",
        )
        doc.multiBuild(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
        with fitz.open(temporary) as rendered:
            output_page_count = len(rendered)
            output_text = "\n".join(page.get_text("text", sort=True) for page in rendered)
            if output_page_count < 2 or len(output_text.strip()) < 100:
                raise RuntimeError("The reading edition failed post-build text/page validation.")
            markers = set(int(value) for value in re.findall(r"Fuente PDF página\s+(\d+)", output_text))
            missing_markers = [i for i in range(1, len(source_pages) + 1) if i not in markers]
            toc_visible = bool(re.search(r"Contenido", output_text, re.IGNORECASE))
            if missing_markers:
                raise RuntimeError(
                    f"Source-page markers failed for {len(missing_markers)} pages; first missing: {missing_markers[:20]}."
                )
            if not toc_visible:
                raise RuntimeError("Table-of-contents section not found after rendering.")
        temporary.replace(output)
        report = {
            "schema": "LOUKSNA_DOCUMENT_WORKBENCH_ACADEMIC_READING_EDITION/1.0",
            "observed_at_utc": utc_now(),
            "operation": "REFLOW_EXTRACTED_TEXT_WITH_ACADEMIC_TYPOGRAPHY",
            "status": "PASS_STRUCTURAL_CHECKS_HUMAN_REVIEW_REQUIRED",
            "input_name": source.name,
            "input_sha256": sha256_file(source),
            "input_page_count": len(source_pages),
            "input_text_characters": source_text_characters,
            "input_nonempty_pages": nonempty_pages,
            "output_name": output.name,
            "output_sha256": sha256_file(output),
            "output_size_bytes": output.stat().st_size,
            "output_page_count": output_page_count,
            "chapter_and_part_navigation_entries": len(headings),
            "source_page_markers_verified": len(source_pages) - len(missing_markers),
            "source_page_markers_missing": missing_markers,
            "table_of_contents_present": toc_visible,
            "typographic_controls": {
                "page_size": "A4", "body_font": "Helvetica",
                "body_font_size_pt": 10.3, "body_leading_pt": 15.2,
                "alignment": "justified", "running_header_and_page_number": True,
                "dynamic_table_of_contents": True, "pdf_outline_bookmarks": True,
                "source_pdf_page_markers": True,
            },
            "editorial_changes": [
                "Consistent title, part and chapter hierarchy.",
                "Readable line spacing, margins and running folios.",
                "Whitespace and line-break normalization.",
                "Safe line-end hyphenation repair only when unambiguous.",
                "Original PDF page markers retained for cross-reference.",
            ],
            "limitations": [
                "This is a reflowed text reading copy, not a facsimile of original page design.",
                "Machine-translation accuracy and clinical terminology are not certified or substantively rewritten.",
                "Human review is required before academic quotation or clinical use.",
                "Consult the original PDF to verify figures, tables, quotations, citations and visual layout.",
            ],
            "verification": "PASS_SOURCE_PAGE_CROSS_REFERENCE_AND_TEXT_PRESENCE",
        }
        write_json_new(audit_file, report)
        return report
    except Exception:
        temporary.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        raise
