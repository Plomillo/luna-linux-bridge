#!/usr/bin/env python3
"""Tiny, bounded PDF/EPUB/text converter for Cajita. Not the Calibre upstream engine."""
from __future__ import annotations
import argparse, html, os, posixpath, re, sys, tempfile, zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

APP_NAME = "Cajita PDF/EPUB Micro Converter"
APP_VERSION = "1.0.0"
MAX_INPUT_BYTES = 256 * 1024 * 1024
MAX_EPUB_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_EPUB_MEMBERS = 10000
ALLOWED_INPUTS = {".pdf", ".epub", ".txt"}
ALLOWED_OUTPUTS = {".pdf", ".epub"}

class VisibleText(HTMLParser):
    BLOCKS = {"address","article","aside","blockquote","div","dl","dt","dd","figcaption","figure","footer","h1","h2","h3","h4","h5","h6","header","li","main","ol","p","pre","section","table","tr","td","th","ul"}
    HIDDEN = {"head","script","style","noscript","svg","nav"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.HIDDEN:
            self.hidden_depth += 1
            return
        if self.hidden_depth:
            return
        if tag in self.BLOCKS or tag == "br":
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("• ")
    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "br":
            self.parts.append("\n")
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.HIDDEN and self.hidden_depth:
            self.hidden_depth -= 1
            return
        if not self.hidden_depth and tag in self.BLOCKS:
            self.parts.append("\n")
    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)
    def text(self):
        raw = html.unescape("".join(self.parts)).replace("\r\n", "\n").replace("\r", "\n")
        cleaned = []
        for line in raw.splitlines():
            line = re.sub(r"[ \t\f\v]+", " ", line).strip()
            if line:
                cleaned.append(line)
            elif cleaned and cleaned[-1] != "":
                cleaned.append("")
        while cleaned and cleaned[-1] == "":
            cleaned.pop()
        return "\n".join(cleaned).strip()

def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()

def clean_text(text):
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)

def read_text_file(path):
    text = clean_text(path.read_text(encoding="utf-8-sig", errors="replace"))
    if not text:
        raise ValueError("El archivo de texto no contiene contenido legible.")
    return text

def safe_zip_member(base, href):
    href = unquote(href.split("#", 1)[0].split("?", 1)[0])
    member = posixpath.normpath(posixpath.join(base, href))
    if member == ".." or member.startswith("../") or member.startswith("/"):
        raise ValueError("La ruta interna del EPUB sale de su paquete.")
    return member

def read_epub(path):
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        if len(infos) > MAX_EPUB_MEMBERS:
            raise ValueError("El EPUB excede el límite de archivos internos.")
        if sum(info.file_size for info in infos) > MAX_EPUB_UNCOMPRESSED_BYTES:
            raise ValueError("El EPUB excede el límite de expansión permitido.")
        if "mimetype" not in archive.namelist() or archive.read("mimetype").strip() != b"application/epub+zip":
            raise ValueError("EPUB inválido: falta mimetype o su contenido es incorrecto.")
        damaged = archive.testzip()
        if damaged:
            raise ValueError(f"EPUB dañado: error de integridad en {damaged}.")
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next((item for item in container.iter() if local_name(item.tag) == "rootfile"), None)
        if rootfile is None:
            raise ValueError("EPUB inválido: no declara su paquete OPF.")
        opf_member = posixpath.normpath(rootfile.attrib.get("full-path", ""))
        if not opf_member or opf_member.startswith("../") or opf_member.startswith("/"):
            raise ValueError("EPUB inválido: ruta OPF insegura.")
        opf_root = ET.fromstring(archive.read(opf_member))
        title = next((e.text.strip() for e in opf_root.iter() if local_name(e.tag) == "title" and e.text and e.text.strip()), path.stem)
        base = posixpath.dirname(opf_member)
        manifest = {}
        for item in opf_root.iter():
            if local_name(item.tag) == "item":
                item_id, href = item.attrib.get("id"), item.attrib.get("href")
                if item_id and href:
                    manifest[item_id] = (safe_zip_member(base, href), item.attrib.get("media-type", ""))
        ordered = []
        for itemref in opf_root.iter():
            if local_name(itemref.tag) == "itemref":
                item_id = itemref.attrib.get("idref", "")
                if item_id in manifest:
                    member, media_type = manifest[item_id]
                    if media_type in {"application/xhtml+xml", "text/html"}:
                        ordered.append(member)
        sections = []
        names = set(archive.namelist())
        for number, member in enumerate(ordered, 1):
            if member not in names:
                raise ValueError(f"EPUB inválido: falta el capítulo {member}.")
            parser = VisibleText()
            parser.feed(archive.read(member).decode("utf-8", "replace"))
            body = parser.text()
            if body:
                sections.append({"title": f"Capítulo {number}", "text": body})
        if not sections:
            raise ValueError("El EPUB no contiene texto extraíble; no se admite OCR ni conversión de imágenes.")
        return title, sections

def read_pdf(path):
    reader = PdfReader(str(path), strict=False)
    if reader.is_encrypted:
        raise ValueError("El PDF está cifrado; esta versión no gestiona contraseñas.")
    sections = []
    for number, page in enumerate(reader.pages, 1):
        try:
            text = clean_text(page.extract_text() or "")
        except Exception as exc:
            raise ValueError(f"No se pudo extraer texto de la página {number}: {exc}") from exc
        if text:
            sections.append({"title": f"Página {number}", "text": text})
    if not sections:
        raise ValueError("El PDF no contiene texto extraíble; los PDF escaneados requieren OCR, fuera de alcance.")
    title = str(reader.metadata.title).strip() if reader.metadata and reader.metadata.title else path.stem
    return title or path.stem, sections

def make_pdf(output, title, sections):
    import reportlab
    fonts_dir = Path(reportlab.__file__).resolve().parent / "fonts"
    font_path, bold_path = fonts_dir / "Vera.ttf", fonts_dir / "VeraBd.ttf"
    font_name, bold_name = "Helvetica", "Helvetica-Bold"
    if font_path.is_file():
        try:
            if "CajitaVera" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("CajitaVera", str(font_path)))
            font_name = "CajitaVera"
            if bold_path.is_file():
                if "CajitaVeraBold" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("CajitaVeraBold", str(bold_path)))
                bold_name = "CajitaVeraBold"
        except Exception:
            font_name, bold_name = "Helvetica", "Helvetica-Bold"
    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CajitaTitle", parent=base_styles["Title"], fontName=bold_name, fontSize=19, leading=24, alignment=TA_CENTER, textColor=colors.HexColor("#172033"), spaceAfter=18)
    heading_style = ParagraphStyle("CajitaHeading", parent=base_styles["Heading2"], fontName=bold_name, fontSize=13, leading=17, spaceBefore=10, spaceAfter=7)
    body_style = ParagraphStyle("CajitaBody", parent=base_styles["BodyText"], fontName=font_name, fontSize=10.5, leading=14, spaceAfter=6, splitLongWords=1)
    story = [Paragraph(html.escape(title or "Documento"), title_style), Spacer(1, 6)]
    for index, section in enumerate(sections):
        heading, content = clean_text(section.get("title", "")), clean_text(section.get("text", ""))
        if heading and (len(sections) > 1 or heading.lower() != (title or "").lower()):
            story.append(Paragraph(html.escape(heading), heading_style))
        for paragraph in re.split(r"\n\s*\n", content):
            paragraph = paragraph.strip()
            if paragraph:
                safe = html.escape(paragraph, quote=False).replace("\n", "<br/>")
                story.append(Paragraph(safe, body_style))
        if index != len(sections) - 1:
            story.append(Spacer(1, 8))
    if len(story) <= 2:
        raise ValueError("No hay contenido para crear el PDF.")
    SimpleDocTemplate(str(output), pagesize=A4, title=(title or "Documento")[:200], author=APP_NAME, subject="PDF generado por el runtime compacto Cajita", leftMargin=48, rightMargin=48, topMargin=48, bottomMargin=48, pageCompression=1).build(story)

def make_epub(output, title, sections):
    import hashlib
    title = clean_text(title) or "Documento"
    digest = hashlib.sha256((title + "\n" + "\n".join(s.get("text", "") for s in sections)).encode("utf-8")).hexdigest()
    identifier = f"urn:sha256:{digest}"
    body_parts = [f"<h1>{html.escape(title)}</h1>"]
    for index, section in enumerate(sections, 1):
        heading = clean_text(section.get("title", "")) or f"Sección {index}"
        body_parts.append(f"<section id=\"section-{index}\"><h2>{html.escape(heading)}</h2>")
        for paragraph in re.split(r"\n\s*\n", clean_text(section.get("text", ""))):
            paragraph = paragraph.strip()
            if paragraph:
                rendered = "<br/>".join(html.escape(line) for line in paragraph.splitlines())
                body_parts.append(f"<p>{rendered}</p>")
        body_parts.append("</section>")
    chapter = ('<?xml version="1.0" encoding="utf-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="und" xml:lang="und">'
        '<head><title>' + html.escape(title) + '</title><meta charset="utf-8"/>'
        '<style>body{font-family:serif;line-height:1.5;margin:5%}h1,h2{line-height:1.2}p{orphans:2;widows:2}</style></head><body>' + "".join(body_parts) + '</body></html>')
    nav = ('<?xml version="1.0" encoding="utf-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="und" xml:lang="und">'
        '<head><title>Contents</title><meta charset="utf-8"/></head><body>'
        '<nav epub:type="toc" id="toc"><h1>Contents</h1><ol><li><a href="chapter.xhtml">'
        + html.escape(title) + '</a></li></ol></nav></body></html>')
    container = ('<?xml version="1.0" encoding="UTF-8"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    opf = ('<?xml version="1.0" encoding="utf-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="und">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="pub-id">{identifier}</dc:identifier><dc:title>{html.escape(title)}</dc:title>'
        f'<dc:language>und</dc:language><dc:creator>{html.escape(APP_NAME)}</dc:creator>'
        '</metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        '<item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>'
        '<spine><itemref idref="chapter"/></spine></package>')
    with zipfile.ZipFile(output, "w") as archive:
        first = zipfile.ZipInfo("mimetype"); first.compress_type = zipfile.ZIP_STORED; first.date_time = (2020,1,1,0,0,0)
        archive.writestr(first, "application/epub+zip")
        for name, data in (("META-INF/container.xml", container), ("OEBPS/content.opf", opf), ("OEBPS/nav.xhtml", nav), ("OEBPS/chapter.xhtml", chapter)):
            info = zipfile.ZipInfo(name); info.compress_type = zipfile.ZIP_DEFLATED; info.date_time = (2020,1,1,0,0,0)
            archive.writestr(info, data.encode("utf-8"))

def convert(source, destination, force=False):
    source = source.expanduser().resolve(strict=True)
    destination = destination.expanduser().resolve()
    if not source.is_file():
        raise ValueError("La entrada debe ser un archivo regular.")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("El archivo de entrada supera el límite de 256 MiB.")
    source_ext, output_ext = source.suffix.lower(), destination.suffix.lower()
    if source_ext not in ALLOWED_INPUTS:
        raise ValueError("Solo se aceptan entradas PDF, EPUB o TXT. HTML y DOCX están excluidos.")
    if output_ext not in ALLOWED_OUTPUTS:
        raise ValueError("Solo se permiten salidas PDF o EPUB.")
    if source_ext == output_ext:
        raise ValueError("Solo se permiten PDF a EPUB, EPUB a PDF o creación desde TXT.")
    if destination == source:
        raise ValueError("La entrada y la salida no pueden ser el mismo archivo.")
    if destination.exists() and not force:
        raise FileExistsError("La salida ya existe; use --force para reemplazarla.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    os.close(fd); temp = Path(temp_name)
    try:
        if source_ext == ".txt":
            sections, title = [{"title": source.stem, "text": read_text_file(source)}], source.stem
        elif source_ext == ".pdf":
            title, sections = read_pdf(source)
        else:
            title, sections = read_epub(source)
        if output_ext == ".pdf":
            make_pdf(temp, title, sections)
            with temp.open("rb") as handle:
                if handle.read(5) != b"%PDF-":
                    raise ValueError("La salida generada no tiene firma PDF.")
        else:
            make_epub(temp, title, sections)
            with zipfile.ZipFile(temp, "r") as archive:
                if archive.read("mimetype").strip() != b"application/epub+zip" or archive.testzip():
                    raise ValueError("La salida generada no superó la validación EPUB.")
        if destination.exists() and not force:
            raise FileExistsError("La salida ya existe; no se reemplazó.")
        os.replace(temp, destination)
    finally:
        try: temp.unlink(missing_ok=True)
        except OSError: pass

def main(argv=None):
    parser = argparse.ArgumentParser(prog="calibre-micro", description="PDF ↔ EPUB y creación desde TXT. Sin HTML, DOCX, OCR, tiendas ni interfaz gráfica.")
    parser.add_argument("input", nargs="?", help="Archivo de entrada PDF, EPUB o TXT")
    parser.add_argument("output", nargs="?", help="Archivo de salida .pdf o .epub")
    parser.add_argument("--force", action="store_true", help="Permitir reemplazar un archivo de salida existente")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    args = parser.parse_args(argv)
    if not args.input or not args.output:
        parser.print_usage(sys.stderr); return 2
    try:
        convert(Path(args.input), Path(args.output), force=args.force)
        print(f"PASS: {args.input} -> {args.output}")
        return 0
    except Exception as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
