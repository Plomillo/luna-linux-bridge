from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_input(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf input: {path}")
    return path


def require_new_output(source: Path, output: Path) -> Path:
    output = output.expanduser().resolve()
    if output == source.resolve():
        raise ValueError("Input and output paths must differ; input is immutable.")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def write_json_new(path: Path, value: Any) -> None:
    path = path.expanduser().resolve()
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite audit output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def normalize_extracted_text(text: str) -> str:
    """Normalize whitespace conservatively while retaining paragraph breaks."""
    text = text.replace("\ufeff", "").replace("\u00a0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])-\n\s*(?=[a-záéíóúüñ])", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_page_order(order_text: str, page_count: int) -> list[int]:
    """Return zero-based page indexes from a complete 1-based permutation."""
    parts = order_text.split(",")
    if page_count < 1:
        raise ValueError("PDF must contain at least one page.")
    if not order_text.strip() or any(not part.strip() for part in parts):
        raise ValueError("Page order contains an empty item; use comma-separated integers such as 2,1,3.")
    try:
        nums = [int(part.strip()) for part in parts]
    except ValueError as exc:
        raise ValueError("Page order must be comma-separated integers, e.g. 2,1,3.") from exc
    expected = set(range(1, page_count + 1))
    if len(nums) != page_count or set(nums) != expected or len(set(nums)) != len(nums):
        raise ValueError(
            f"Order must contain every page exactly once (expected 1..{page_count})."
        )
    return [num - 1 for num in nums]


def inspect_pdf(input_path: Path) -> dict[str, Any]:
    source = require_input(input_path)
    reader = PdfReader(str(source), strict=False)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported without an explicit decryption workflow.")
    page_rows: list[dict[str, Any]] = []
    with fitz.open(source) as document:
        for index, page in enumerate(document):
            text = page.get_text("text", sort=True)
            page_rows.append({
                "page": index + 1,
                "width_points": round(page.rect.width, 2),
                "height_points": round(page.rect.height, 2),
                "rotation_degrees": page.rotation,
                "text_characters": len(text.strip()),
                "image_count": len(page.get_images(full=True)),
                "text_sparse": len(text.strip()) < 20,
            })
    sparse = [row["page"] for row in page_rows if row["text_sparse"]]
    return {
        "schema": "LOUKSNA_DOCUMENT_WORKBENCH_INSPECTION/1.0",
        "observed_at_utc": utc_now(),
        "input": str(source),
        "input_size_bytes": source.stat().st_size,
        "input_sha256": sha256_file(source),
        "page_count": len(reader.pages),
        "metadata": {str(k): str(v) for k, v in (reader.metadata or {}).items() if v is not None},
        "sparse_text_pages": sparse,
        "pages": page_rows,
        "interpretation": (
            "Sparse text can indicate scanned pages, unusual encoding, or a genuinely low-text page; "
            "it is a diagnostic signal, not proof that OCR is required."
        ),
    }


def reorder_pdf(input_path: Path, output_path: Path, order_text: str) -> dict[str, Any]:
    source = require_input(input_path)
    output = require_new_output(source, output_path)
    reader = PdfReader(str(source), strict=False)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported without an explicit decryption workflow.")
    indexes = parse_page_order(order_text, len(reader.pages))
    writer = PdfWriter()
    for index in indexes:
        writer.add_page(reader.pages[index])
    if reader.metadata:
        metadata = {str(k): str(v) for k, v in reader.metadata.items() if v is not None}
        if metadata:
            writer.add_metadata(metadata)
    try:
        with output.open("xb") as stream:
            writer.write(stream)
        check = PdfReader(str(output), strict=True)
        if len(check.pages) != len(reader.pages):
            raise RuntimeError("Post-write page-count check failed.")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {
        "schema": "LOUKSNA_DOCUMENT_WORKBENCH_REORDER/1.0",
        "observed_at_utc": utc_now(),
        "input": str(source),
        "input_sha256": sha256_file(source),
        "output": str(output),
        "output_sha256": sha256_file(output),
        "page_count": len(check.pages),
        "page_order_1_based": [index + 1 for index in indexes],
        "verification": "PASS",
    }


def run_ocr(input_path: Path, output_path: Path, language: str, timeout_seconds: int = 3600) -> dict[str, Any]:
    source = require_input(input_path)
    output = require_new_output(source, output_path)
    executable = shutil.which("ocrmypdf")
    if not executable:
        raise RuntimeError("OCRmyPDF is not installed; no OCR was attempted.")
    if timeout_seconds < 1 or timeout_seconds > 24 * 60 * 60:
        raise ValueError("OCR timeout must be between 1 second and 24 hours.")
    command = [
        executable, "--deskew", "--rotate-pages", "--language", language,
        "--output-type", "pdf", str(source), str(output),
    ]
    started = utc_now()
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True,
            timeout=timeout_seconds, shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        output.unlink(missing_ok=True)
        raise TimeoutError(f"OCRmyPDF exceeded the {timeout_seconds}s timeout.") from exc
    if result.returncode != 0:
        output.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "no diagnostic output")[-4000:]
        raise RuntimeError(f"OCRmyPDF failed with exit {result.returncode}: {detail}")
    try:
        verified = PdfReader(str(output), strict=True)
        if not verified.pages:
            raise RuntimeError("OCR output contains no pages.")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {
        "schema": "LOUKSNA_DOCUMENT_WORKBENCH_OCR/1.0",
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "input": str(source),
        "input_sha256": sha256_file(source),
        "output": str(output),
        "output_sha256": sha256_file(output),
        "language": language,
        "command_executable": Path(executable).name,
        "timeout_seconds": timeout_seconds,
        "verification": "PASS",
        "stderr_tail": (result.stderr or "")[-1000:],
    }


def _text_blocks(source: Path) -> tuple[list[dict[str, Any]], list[int]]:
    pages: list[dict[str, Any]] = []
    sparse_pages: list[int] = []
    with fitz.open(source) as document:
        for page_index, page in enumerate(document):
            blocks_out: list[str] = []
            for block in page.get_text("blocks", sort=True):
                if len(block) < 7 or int(block[6]) != 0:
                    continue
                block_text = normalize_extracted_text(str(block[4]))
                if block_text:
                    blocks_out.append(block_text)
            combined = "\n\n".join(blocks_out)
            if len(combined.strip()) < 20:
                sparse_pages.append(page_index + 1)
            pages.append({
                "page": page_index + 1,
                "blocks": blocks_out,
                "text": combined,
                "text_characters": len(combined),
            })
    return pages, sparse_pages


def _paragraph_style() -> ParagraphStyle:
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        "WorkbenchBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        spaceAfter=7,
        alignment=TA_LEFT,
        splitLongWords=True,
        allowWidows=0,
        allowOrphans=0,
    )


def _render_sections_pdf(output: Path, title: str, sections: list[tuple[str, str]]) -> None:
    styles = getSampleStyleSheet()
    body_style = _paragraph_style()
    page_style = ParagraphStyle(
        "WorkbenchPageMarker", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=colors.HexColor("#444444"), spaceBefore=5, spaceAfter=9,
    )
    title_style = ParagraphStyle(
        "WorkbenchTitle", parent=styles["Title"], alignment=TA_CENTER,
        fontName="Helvetica-Bold", fontSize=16, leading=21, spaceAfter=16,
    )
    story: list[Any] = [Paragraph(html.escape(title), title_style), Spacer(1, 3 * mm)]
    for section_title, body in sections:
        if section_title:
            story.append(Paragraph(html.escape(section_title), page_style))
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
        for paragraph in paragraphs:
            escaped = html.escape(paragraph).replace("\n", "<br/>")
            story.append(Paragraph(escaped, body_style))
    doc = SimpleDocTemplate(
        str(output), pagesize=A4,
        rightMargin=22 * mm, leftMargin=22 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=title, author="Louksna Document Workbench",
    )
    doc.build(story)


def reflow_pdf(
    input_path: Path,
    output_path: Path,
    *,
    confirm_text_only: bool,
    allow_sparse: bool = False,
) -> dict[str, Any]:
    source = require_input(input_path)
    output = require_new_output(source, output_path)
    audit_path = output.with_suffix(output.suffix + ".audit.json")
    if audit_path.exists():
        raise FileExistsError(f"Refusing to overwrite audit output: {audit_path}")
    if not confirm_text_only:
        raise ValueError("Text-only reflow is lossy by design; pass --confirm-text-only explicitly.")
    pages, sparse_pages = _text_blocks(source)
    if sparse_pages and not allow_sparse:
        raise ValueError(
            f"Sparse/no-text pages detected: {sparse_pages[:30]}. Run OCR explicitly and inspect "
            "the result, or pass --allow-sparse after reviewing the inspection report."
        )
    sections = [
        (f"Extracted from source page {page['page']}", page["text"])
        for page in pages if page["text"].strip()
    ]
    if not sections:
        raise ValueError("No extractable text found; refusing to create an empty reading copy.")
    try:
        _render_sections_pdf(output, f"Reading copy — {source.stem}", sections)
        result_reader = PdfReader(str(output), strict=True)
        with fitz.open(output) as check_doc:
            output_chars = sum(len(page.get_text().strip()) for page in check_doc)
        if len(result_reader.pages) < 1 or output_chars < 1:
            raise RuntimeError("Post-build PDF verification found no readable text.")
        audit = {
            "schema": "LOUKSNA_DOCUMENT_WORKBENCH_REFLOW/1.0",
            "observed_at_utc": utc_now(),
            "operation": "TEXT_ONLY_REFLOW",
            "input": str(source),
            "input_sha256": sha256_file(source),
            "output": str(output),
            "output_sha256": sha256_file(output),
            "source_page_count": len(pages),
            "output_page_count": len(result_reader.pages),
            "source_text_characters": sum(page["text_characters"] for page in pages),
            "output_text_characters": output_chars,
            "sparse_pages": sparse_pages,
            "figures_tables_and_original_layout_preserved": False,
            "human_visual_review_required": True,
            "verification": "PASS_STRUCTURAL_CHECKS_REVIEW_REQUIRED",
        }
        write_json_new(audit_path, audit)
        return audit
    except Exception:
        output.unlink(missing_ok=True)
        raise


def _load_glossary(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if not path.is_file():
        raise FileNotFoundError(f"Glossary JSON not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and key.strip() and isinstance(value, str) and value.strip()
        for key, value in payload.items()
    ):
        raise ValueError("Glossary must be a JSON object mapping non-empty source terms to target terms.")
    return payload


def _protect_glossary(text: str, glossary: dict[str, str]) -> tuple[str, dict[str, str], dict[str, int]]:
    if not glossary:
        return text, {}, {}
    terms = sorted(glossary, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(term) for term in terms), flags=re.IGNORECASE)
    tokens: dict[str, str] = {}
    counts = {term: 0 for term in glossary}
    pieces: list[str] = []
    cursor = 0
    occurrence = 0
    for match in pattern.finditer(text):
        pieces.append(text[cursor:match.start()])
        source_term = match.group(0)
        canonical_key = next(key for key in terms if key.casefold() == source_term.casefold())
        token = f"ZXQGLOSSARY{occurrence:06d}QXZ"
        pieces.append(token)
        tokens[token] = glossary[canonical_key]
        counts[canonical_key] += 1
        occurrence += 1
        cursor = match.end()
    pieces.append(text[cursor:])
    return "".join(pieces), tokens, {key: value for key, value in counts.items() if value}


def _translate_chunks(text: str, translation: Any, glossary: dict[str, str], max_chars: int = 2500) -> str:
    protected, tokens, _ = _protect_glossary(text, glossary)
    chunks: list[str] = []
    current = ""
    for paragraph in re.split(r"(\n\s*\n)", protected):
        if not paragraph:
            continue
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(paragraph[start:start + max_chars] for start in range(0, len(paragraph), max_chars))
            continue
        if current and len(current) + len(paragraph) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current += paragraph
    if current:
        chunks.append(current)
    translated = "".join(translation.translate(chunk) for chunk in chunks)
    for token, target_term in tokens.items():
        if token not in translated:
            raise RuntimeError(
                f"Translation backend altered glossary token {token}; refusing output to avoid silent terminology loss."
            )
        translated = translated.replace(token, target_term)
    return translated


def translate_pdf(
    input_path: Path,
    output_dir: Path,
    prefix: str,
    source_language: str,
    target_language: str,
    glossary_path: Path | None = None,
) -> dict[str, Any]:
    source = require_input(input_path)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", prefix):
        raise ValueError("Output prefix must be 1–80 safe filename characters.")
    if source_language == target_language:
        raise ValueError("Source and target languages must differ.")
    try:
        import argostranslate.translate as argos_translate
    except ImportError as exc:
        raise RuntimeError(
            "Argos Translate is not installed. Install the optional translate extra and preinstall "
            "the required local language package; no network download is attempted."
        ) from exc
    try:
        translation = argos_translate.get_translation_from_codes(source_language, target_language)
    except Exception as exc:
        raise RuntimeError(
            f"Unable to load a local Argos translation model for {source_language}->{target_language}."
        ) from exc
    if translation is None:
        raise RuntimeError(f"No local Argos model is installed for {source_language}->{target_language}.")
    glossary = _load_glossary(glossary_path)
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{prefix}.md"
    pdf_path = output_dir / f"{prefix}.pdf"
    audit_path = output_dir / f"{prefix}.audit.json"
    for path in (md_path, pdf_path, audit_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing output: {path}")

    pages: list[dict[str, Any]] = []
    with fitz.open(source) as document:
        for index, page in enumerate(document):
            extracted = normalize_extracted_text(page.get_text("text", sort=True))
            if not extracted:
                pages.append({
                    "page": index + 1, "source_characters": 0,
                    "translated_characters": 0, "status": "SKIPPED_NO_TEXT",
                    "source_text": "", "translated_text": "",
                })
                continue
            translated = _translate_chunks(extracted, translation, glossary)
            pages.append({
                "page": index + 1,
                "source_characters": len(extracted),
                "translated_characters": len(translated),
                "status": "TRANSLATED",
                "source_text": extracted,
                "translated_text": translated,
            })

    if not any(page["translated_text"].strip() for page in pages):
        raise ValueError("No extractable text found; refusing to create an empty translation.")

    md_lines = [
        f"# Machine-translated reading draft: {source.stem}",
        "",
        f"- Source language: {source_language}",
        f"- Target language: {target_language}",
        "- Backend: Argos Translate (local model)",
        "- Review status: HUMAN_REVIEW_REQUIRED",
        "",
        "This is an unreviewed machine-translation draft. Verify clinical terminology, quotations, footnotes, references, and context against the source.",
        "",
    ]
    sections: list[tuple[str, str]] = []
    for page in pages:
        if not page["translated_text"].strip():
            continue
        marker = f"Source PDF page {page['page']}"
        md_lines.extend([f"## {marker}", "", page["translated_text"], ""])
        sections.append((marker, page["translated_text"]))
    md_text = "\n".join(md_lines).rstrip() + "\n"
    created: list[Path] = []
    try:
        md_path.write_text(md_text, encoding="utf-8")
        created.append(md_path)
        created.append(pdf_path)
        _render_sections_pdf(pdf_path, f"Machine-translated reading draft — {source.stem}", sections)
        pdf_reader = PdfReader(str(pdf_path), strict=True)
        with fitz.open(pdf_path) as translated_document:
            output_text_characters = sum(len(page.get_text().strip()) for page in translated_document)
        if not pdf_reader.pages or output_text_characters == 0:
            raise RuntimeError("Translated PDF failed post-build text verification.")
        audit = {
            "schema": "LOUKSNA_DOCUMENT_WORKBENCH_TRANSLATION/1.0",
            "observed_at_utc": utc_now(),
            "operation": "LOCAL_MACHINE_TRANSLATION",
            "input": str(source),
            "input_sha256": sha256_file(source),
            "source_language": source_language,
            "target_language": target_language,
            "backend": "Argos Translate local model",
            "glossary_path": str(glossary_path.resolve()) if glossary_path else None,
            "glossary_source_terms": len(glossary),
            "page_count": len(pages),
            "translated_pages": sum(page["status"] == "TRANSLATED" for page in pages),
            "skipped_no_text_pages": [page["page"] for page in pages if page["status"] != "TRANSLATED"],
            "markdown_output": str(md_path),
            "markdown_sha256": sha256_file(md_path),
            "pdf_output": str(pdf_path),
            "pdf_sha256": sha256_file(pdf_path),
            "pdf_page_count": len(pdf_reader.pages),
            "pdf_extractable_text_characters": output_text_characters,
            "translation_review": "REQUIRED",
            "network_service_used": False,
            "pages": [
                {key: value for key, value in page.items() if key not in ("source_text", "translated_text")}
                for page in pages
            ],
        }
        write_json_new(audit_path, audit)
        return audit
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def _trim_heading_body(suffix: str) -> str:
    """Keep a navigation label concise when extracted title and first body sentence share a line."""
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


def _organization_outline(document: fitz.Document) -> list[list[Any]]:
    """Infer bookmarks while excluding contents/attribution lines and trimming body-text spillover."""
    toc: list[list[Any]] = []
    seen: set[tuple[int, str]] = set()
    active_part = False
    part_pattern = re.compile(
        r"^(?:PARTE|PART)\s+(?:UNO|DOS|TRES|CUATRO|CINCO|SEIS|SIETE|OCHO|NUEVE|DIEZ|"
        r"ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|[IVX]{1,6})\b.*$",
        re.IGNORECASE,
    )
    chapter_pattern = re.compile(
        r"^(?:CAP[IÍ]TULO|CHAPTER)\s+(\d{1,2})(?:\s*[:.\-–—]\s*|\s+)?(.*)$",
        re.IGNORECASE,
    )
    front_pattern = re.compile(
        r"^(?:PREFACIO|PREFACE|AGRADECIMIENTOS|ACKNOWLEDGEMENTS?|"
        r"CONTENIDOS|CONTENIDO|CONTENTS|TABLE OF CONTENTS|"
        r"BIBLIOGRAF[IÍ]A|BIBLIOGRAPHY|[ÍI]NDICE|INDEX)(?:\s+[IVXLCDM]+)?$",
        re.IGNORECASE,
    )
    toc_pattern = re.compile(
        r"^(?:CONTENIDOS|CONTENIDO|CONTENTS|TABLE OF CONTENTS|[ÍI]NDICE)\b",
        re.IGNORECASE,
    )
    leader_pattern = re.compile(r"(?:\.{2,}|…{1,})\s*\d{1,4}\s*$")
    for page_index, page in enumerate(document):
        raw_text = page.get_text("text", sort=True)
        lines = [
            re.sub(r"\s+", " ", line).strip(" \t\r\n:;")
            for line in raw_text.splitlines() if line.strip()
        ]
        physical_page = page_index + 1
        if page_index == 0:
            title = lines[0][:100] if lines else "Documento"
            toc.append([1, f"Portada — {title}", physical_page])
            seen.add((physical_page, title.casefold()))
            continue
        if not lines:
            continue
        chapter_entries = sum(bool(chapter_pattern.match(line)) for line in lines[:30])
        leader_entries = sum(bool(leader_pattern.search(line)) for line in lines[:30])
        if (
            any(toc_pattern.match(line) for line in lines[:10])
            or chapter_entries >= 2
            or leader_entries >= 2
        ):
            continue
        entry: tuple[int, str] | None = None
        for line_index, line in enumerate(lines[:4]):
            if line_index <= 1 and part_pattern.match(line) and len(line) <= 120:
                entry = (1, line[:120])
                active_part = True
                break
            match = chapter_pattern.match(line)
            if line_index <= 2 and match:
                number = int(match.group(1))
                suffix = _trim_heading_body(match.group(2))
                if not suffix:
                    continue
                title = f"Capítulo {number}: {suffix}" if len(suffix) <= 105 else f"Capítulo {number}"
                entry = (2 if active_part else 1, title[:120])
                break
            if line_index <= 2 and front_pattern.fullmatch(line) and len(line) <= 120:
                entry = (1, line[:120])
                break
        if entry:
            level, title = entry
            key = (physical_page, title.casefold())
            if key not in seen:
                toc.append([level, title, physical_page])
                seen.add(key)
    return toc


def organize_pdf(input_path: Path, output_path: Path, audit_path: Path | None = None) -> dict[str, Any]:
    """Add page navigation bookmarks and verify original order, geometry, and extracted text."""
    source = require_input(input_path)
    output = require_new_output(source, output_path)
    audit = audit_path.expanduser().resolve() if audit_path else output.with_suffix(output.suffix + ".audit.json")
    temporary = output.with_name(output.stem + ".tmp" + output.suffix)
    if audit in (source.resolve(), output.resolve()):
        output.unlink(missing_ok=True)
        raise ValueError("Audit output must be distinct from the input and organized PDF.")
    if audit.exists():
        output.unlink(missing_ok=True)
        raise FileExistsError(f"Refusing to overwrite audit output: {audit}")
    if temporary.exists():
        output.unlink(missing_ok=True)
        raise FileExistsError(f"Refusing to overwrite temporary output: {temporary}")
    source_hash_before = sha256_file(source)
    try:
        with fitz.open(source) as document:
            if document.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported without an explicit decryption workflow.")
            page_count = len(document)
            geometry = [(round(p.rect.width, 3), round(p.rect.height, 3), p.rotation) for p in document]
            text_hashes = [
                hashlib.sha256(p.get_text("text", sort=True).encode("utf-8")).hexdigest()
                for p in document
            ]
            outline = _organization_outline(document)
            if not outline:
                raise RuntimeError("No safe navigation outline could be generated; refusing to write output.")
            document.set_toc(outline)
            metadata = dict(document.metadata or {})
            metadata["title"] = metadata.get("title") or "Trastornos de personalidad severos — copia organizada"
            metadata["author"] = metadata.get("author") or "Otto F. Kernberg"
            metadata["subject"] = (metadata.get("subject") or "").strip() or (
                "Marcadores de navegación añadidos; contenido y secuencia original preservados."
            )
            document.set_metadata(metadata)
            document.save(str(temporary), garbage=3, deflate=True)
        with fitz.open(temporary) as verified:
            if len(verified) != page_count:
                raise RuntimeError("Page count changed during organization.")
            verified_geometry = [(round(p.rect.width, 3), round(p.rect.height, 3), p.rotation) for p in verified]
            verified_hashes = [
                hashlib.sha256(p.get_text("text", sort=True).encode("utf-8")).hexdigest()
                for p in verified
            ]
            verified_toc = verified.get_toc()
            if geometry != verified_geometry:
                raise RuntimeError("Page geometry or rotations changed; refusing output.")
            if text_hashes != verified_hashes:
                raise RuntimeError("Extracted page text changed; refusing output.")
            if len(verified_toc) != len(outline):
                raise RuntimeError("Bookmark verification failed.")
        if sha256_file(source) != source_hash_before:
            raise RuntimeError("Input SHA-256 changed during processing; refusing output.")
        temporary.replace(output)
        result = {
            "schema": "LOUKSNA_DOCUMENT_WORKBENCH_ORGANIZATION/1.0",
            "observed_at_utc": utc_now(),
            "operation": "ADD_NAVIGATION_BOOKMARKS_WITHOUT_REORDERING",
            "input_name": source.name,
            "input_size_bytes": source.stat().st_size,
            "input_sha256": source_hash_before,
            "output_name": output.name,
            "output_size_bytes": output.stat().st_size,
            "output_sha256": sha256_file(output),
            "source_page_count": page_count,
            "output_page_count": page_count,
            "page_order_changed": False,
            "page_geometry_preserved": True,
            "extracted_page_text_preserved": True,
            "source_modified": False,
            "bookmark_count": len(verified_toc),
            "bookmarks": [{"level": int(lvl), "title": str(title), "page": int(pg)} for lvl, title, pg in verified_toc],
            "human_review": "RECOMMENDED",
            "verification": "PASS_STRUCTURAL_CONTENT_INVARIANCE",
            "limitations": [
                "Bookmarks are inferred conservatively from page-leading headings.",
                "Page order, geometry and extracted page text are verified invariant.",
                "The operation does not validate the accuracy of the source's existing machine translation.",
            ],
        }
        write_json_new(audit, result)
        return result
    except Exception:
        temporary.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        raise
