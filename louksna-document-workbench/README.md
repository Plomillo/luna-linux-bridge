# Louksna Document Workbench

STATUS: IMPLEMENTED_CANDIDATE_NOT_CERTIFIED

This is a new, standalone candidate component for local document processing. It is intentionally separate from Document Factory: it does not import it, call it, modify it, or require it as a dependency. Document Factory remains untouched.

## Purpose

Provide an independently developed path for:
- inspecting PDF structure and text coverage;
- reordering PDF pages only when the supplied order is a complete, explicit permutation;
- invoking OCRmyPDF as an optional local subprocess;
- producing a text-only reflow edition from PDFs whose extracted text is usable;
- translating extracted PDF text with locally installed Argos Translate language packages;
- preserving page references, glossary substitutions, input/output SHA-256 values, and a machine-readable audit record.

Kestra may later orchestrate these commands as isolated stages. Kestra is not itself the PDF parser or translator. This candidate does not change the existing Kestra installation or flows.

## Explicit limitations

The reflow operation is a reading-copy reconstruction, not a facsimile. It does not promise to preserve the original page design, figures, tables, footnote placement, typography, or pagination. It is deliberately guarded by the required --confirm-text-only option. Keep the original PDF as the authoritative source and compare the result before replacing anything in a personal library.

The translation operation translates text extracted from PDFs; it does not guarantee scholarly, clinical, or publication-grade accuracy. Machine-translated output requires human review. Language packages must already be installed locally for the offline Argos backend. This tool does not silently download a model, send a document to a cloud API, or overwrite the input.

OCR is delegated to an installed ocrmypdf executable. It is not automatically run when text extraction is sparse; the operator must choose the OCR step explicitly.

## Safety and audit rules

- Input files are read-only. Output paths must be distinct from input paths and must not already exist.
- Page reorder requires every page exactly once; no implicit deletion, duplication, or reordering is permitted.
- No cloud service is configured by default.
- Outputs include SHA-256 provenance records.
- Sparse-text pages are reported. Text-only reconstruction refuses sparse PDFs unless --allow-sparse is explicit.
- Translation retains source page markers and fails closed if glossary placeholders appear to have been lost by the translation backend.
- This branch is a candidate only. It does not claim independent validation, certification, production activation, or rollback verification.

## Install

Use Python 3.11 or later, preferably in a virtual environment.

Install the project from this directory with python -m pip install -e . For offline translation support, install the optional extra with python -m pip install -e ".[translate]", then install suitable Argos language packages through the operator's approved local package process. Package download and model installation are intentionally not triggered by this application.

OCR requires OCRmyPDF and its system dependencies to be installed separately. A text reflow PDF requires the extracted text to be meaningful.

## Commands

- Inspect: louksna-docworkbench inspect input.pdf --audit output.json
- Reorder: louksna-docworkbench reorder input.pdf output.pdf --order 1,3,2
- OCR: louksna-docworkbench ocr input.pdf output_ocr.pdf --language spa
- Reflow: louksna-docworkbench reflow input.pdf reading_copy.pdf --confirm-text-only
- Translate: louksna-docworkbench translate input.pdf --output-dir translated --prefix kernberg-en --source es --target en --glossary glossary.json

The page order above is only an example. For a reorder, the list must contain each original page number exactly once. The translator glossary is a JSON object whose keys are source-language terms and whose values are preferred target-language terms, for example {"transferencia": "transference"}.

## Future integration

A separate Kestra flow can invoke the CLI in a dedicated, resource-limited runner and preserve each stage's inputs, outputs, hashes, and result. That workflow should be added only after this package's local tests, task-runner isolation, resource limits, timeout handling, and failure/rollback behavior are independently reviewed. This repository change does not enable arbitrary script execution in the existing Kestra runtime.

## Scope boundary

No files under document-factory/ are modified or required. Do not merge this candidate into main or call it certified without the repository's separate evidence, G23 independent validation, G24 certification, non-regression, and rollback gates.
