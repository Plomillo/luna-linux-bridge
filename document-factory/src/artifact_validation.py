from __future__ import annotations
import re,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
REQ={"docx":["[Content_Types].xml","_rels/.rels","word/document.xml"],"pptx":["[Content_Types].xml","_rels/.rels","ppt/presentation.xml"],"xlsx":["[Content_Types].xml","_rels/.rels","xl/workbook.xml"]}
def validate_ooxml(path,kind):
    failures=[]
    try:
        with zipfile.ZipFile(path) as z:
            bad=z.testzip()
            if bad: failures.append("ZIP_CRC_FAIL:"+bad)
            names=z.namelist()
            if any(n.startswith("/") or ".." in n.split("/") for n in names): failures.append("UNSAFE_ARCHIVE_PATH")
            for req in REQ[kind]:
                if req not in names: failures.append("MISSING_PART:"+req)
                elif req.endswith(".xml"):
                    try: ET.fromstring(z.read(req))
                    except Exception: failures.append("INVALID_XML:"+req)
    except Exception as exc: failures.append("OOXML_OPEN_FAIL:"+str(exc))
    return {"status":"PASS" if not failures else "FAIL","failures":failures}
def validate_pdf(path):
    data=Path(path).read_bytes(); failures=[]
    if not data.startswith(b"%PDF-"): failures.append("PDF_HEADER_MISSING")
    if b"%%EOF" not in data[-2048:]: failures.append("PDF_EOF_MISSING")
    if not re.search(rb"\b\d+\s+\d+\s+obj\b",data): failures.append("PDF_OBJECT_MISSING")
    return {"status":"PASS" if not failures else "FAIL","failures":failures}
