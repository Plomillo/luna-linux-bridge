#!/usr/bin/env python3
"""Task-specific metadata finalizer; does not alter shared factory providers."""
from __future__ import annotations
import hashlib
import json
import pathlib
import sys
from docx import Document

docx_path = pathlib.Path(sys.argv[1])
evidence_path = pathlib.Path(sys.argv[2])

doc = Document(str(docx_path))
props = doc.core_properties
props.title = "Creando preguntas para una encuesta — Entrega 1"
props.subject = "Metodología Cuantitativa de la Investigación — Responsabilidad y preguntas tipo Likert"
props.author = "Valeria Galaz; Diego Norambuena; Paula Pizarro; Joel Quezada"
props.keywords = "UNIACC; Metodología Cuantitativa; responsabilidad; BFI-2; NEO-FFI-30; escala Likert"
doc.save(str(docx_path))

# Reopen the exact artifact and verify metadata before recording its digest.
verified = Document(str(docx_path)).core_properties
expected_title = "Creando preguntas para una encuesta — Entrega 1"
expected_author = "Valeria Galaz; Diego Norambuena; Paula Pizarro; Joel Quezada"
assert verified.title == expected_title, f"TITLE_MISMATCH:{verified.title!r}"
assert verified.author == expected_author, f"AUTHOR_MISMATCH:{verified.author!r}"

sha = hashlib.sha256(docx_path.read_bytes()).hexdigest()
evidence_path.parent.mkdir(parents=True, exist_ok=True)
evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
evidence.update({
    "status": "APPLIED_AND_VERIFIED",
    "artifact": docx_path.name,
    "sha256": sha,
    "metadata_title": verified.title,
    "metadata_subject": verified.subject,
    "author_names": verified.author,
    "metadata_verified": True,
})
evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status":"PASS","artifact":docx_path.name,"sha256":sha,"title":verified.title,"author":verified.author},ensure_ascii=False,sort_keys=True))
