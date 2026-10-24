# Cajita PDF/EPUB Micro Candidate v1

Status: EXPERIMENTAL / NOT CERTIFIED. This is a small independent implementation of the requested conversion paths. It is not the Calibre upstream binary and does not claim Calibre-wide feature parity.

## Exact functional scope

- PDF -> EPUB: extracts selectable PDF text and puts it into a valid EPUB chapter, grouped by source page.
- EPUB -> PDF: reads the EPUB spine in order, extracts chapter text, and creates a reflowed PDF.
- TXT -> PDF: creates a PDF from UTF-8 text.
- TXT -> EPUB: creates a valid EPUB from UTF-8 text.

The public launcher rejects HTML, DOCX, MOBI and other formats. TXT is the only creation input format. No GUI, translation catalogs, store/catalog integrations, device support, OCR, networking or telemetry are included.

## Size budget and packaging boundary

The build workflow measures the exact .tar.xz release package and fails unless its size is <= 16,000,000 bytes. It also records SHA-256 and the file inventory. The archive includes the converter source plus pinned, vendored pypdf, ReportLab and Pillow Python packages. Pillow is included only because the pinned ReportLab release imports PIL utilities on its text-rendering path; the application does not provide image conversion. The package does not include the CPython interpreter, Python standard library or glibc; host Python >= 3.9 is required.

## Fidelity limitations

This deliberately trades Calibre's full document-layout fidelity for a much smaller scope. It is a text extraction and reflow engine, not a full layout-preserving converter. It does not preserve PDF/EPUB images, CSS layout, annotations, embedded fonts, bookmarks or other advanced structures. Encrypted PDFs and image-only/scanned PDFs are rejected; OCR is not present. The bundled Vera font covers many Unicode characters, but this is not a guarantee of full script coverage.

The four conversion paths are not considered validated until the GitHub Actions functional tests pass. A successful build is not certification of Calibre equivalence.

## Use

Run on a Linux host with Python 3.9 or newer:

    ./launch input.txt output.pdf
    ./launch input.txt output.epub
    ./launch input.pdf output.epub
    ./launch input.epub output.pdf

An existing output is never replaced unless --force is supplied.

## Dependencies and provenance

The build pins and verifies the official PyPI wheel hashes for pypdf 6.21.2, ReportLab 5.1.0 and Pillow 12.0.0 before vendoring them. Their licenses and the bundled Vera font license are retained in the package. The source lock and package SHA-256 are emitted as build evidence.

This is an alternative candidate. It does not modify the main Cajita runtime, Macrodown manifest, or the existing Calibre Slim v2 PR.
