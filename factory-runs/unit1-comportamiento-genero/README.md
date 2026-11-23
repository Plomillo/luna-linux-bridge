# U1 — Comportamiento y género

This run is isolated from all Unit 2 work. It was produced on the requested candidate branch:
`candidate/document-factory-v1-unit2-20261013`.

## Authoritative inputs

- Moodle activity and rubric: `sources/assignment-and-rubric.md`.
- Exact activity attachment: `sources/Guia de la buena esposa.pdf`.
- SHA-256 of the attachment: `ccb0979322fceba254e01c4eb5b5a8d5954326eaa0112c414ac635ff27626c5f`.
- Essay source: `source/report.md`.

## Outputs

- `deliverables/Trabajo1_DiegoIgnacioNorambuenaMiranda.docx` — Word submission.
- `deliverables/Trabajo1_DiegoIgnacioNorambuenaMiranda.pdf` — rendered review copy.
- `evidence/validation.json` — automated validation.
- `evidence/rubric-assessment.json` — alignment with the six Moodle criteria.
- `evidence/case-coverage.json` — traceability to all eleven rules, the Extra panel and final image.
- `workspace/data/source-ledger.json` — citation/source traceability.

## Rebuild and verify

From the repository root:

```bash
python3 -B factory-runs/unit1-comportamiento-genero/build.py
python3 -B factory-runs/unit1-comportamiento-genero/verify.py
python3 -B document-factory/src/selftest.py
python3 -B document-factory/src/test_rubric_compiler.py
```

The build expects LibreOffice Writer and Poppler utilities. The checks can be reproduced from the repository root with the commands above.

## Validation boundary

The document has four body pages: one introduction page and three development pages, with the conclusion on the final development page. Cover and references make six pages total. Format, source hash, citation ledger, page structure and rubric arithmetic are machine-checked.

The rubric's delivery-on-time criterion depends on the learner submitting the DOCX to Moodle before the close time. Language and substantive grading remain human judgments. G23 and G24 have not been executed; no academic score or certification is claimed.
