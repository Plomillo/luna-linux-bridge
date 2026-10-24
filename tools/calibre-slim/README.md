# Cajita Calibre PDF/EPUB Overlay Candidate v2

**Status: candidate only; not certified.** This derivative is based on the existing Calibre v9.17.0 candidate and preserves Calibre's upstream conversion engine. It is not the independent micro-converter introduced in PR #100.

## Exact public scope

- TXT -> PDF (create a PDF)
- TXT -> EPUB (create an EPUB)
- PDF -> EPUB
- EPUB -> PDF

Only PDF and EPUB are allowed as output formats. HTML, DOCX, other ebook formats, GUI, store/catalog/device-management functions, translation catalogs, and OCR are outside the scope. TXT remains only as the minimum source format for creating new files. The OEB intermediate remains private to Calibre's upstream conversion pipeline.

## 16 MB package contract

The generated artifact is a small **Calibre feature overlay**, not a self-contained Calibre installation. The workflow measures the exact `.tar.xz` archive and fails if it exceeds **16,000,000 bytes**.

The overlay contains the narrowed upstream Calibre built-in conversion registry, the scope-enforcing wrapper, the upstream version/identity lock, license notices, and evidence metadata. At execution time it delegates to the official Calibre v9.17.0 Linux x86-64 runtime installed outside this overlay, using `CALIBRE_EBOOK_CONVERT` if the executable is not available on `PATH`. It sets `CALIBRE_DEVELOP_FROM` so the pinned Calibre runtime uses the narrowed registry.

**Important size boundary:** the overlay archive's 16 MB measurement does not include the external native Calibre runtime or its Qt/WebEngine dependencies. The previous complete binary distribution measured about 179.2 MB compressed after pruning. This candidate therefore does **not** claim that a self-contained, complete Calibre installation fits into 16 MB. The external runtime must already be provisioned for the overlay to operate.

## Provenance and tests

- Upstream repository: `kovidgoyal/calibre`
- Pinned upstream tag: `v9.17.0`
- Pinned source/binary sizes and SHA-256 values are recorded in `source-lock.json`.
- The workflow checks the untouched upstream runtime first, narrows a disposable copy, then tests the four required conversion operations and rejects out-of-scope inputs/outputs.
- The final overlay archive receives a byte-exact size measurement and SHA-256. It is not published as passing if the archive exceeds the cap or the conversion canaries fail.
- GPL-3.0 license and copyright notices remain included.

The candidate does not modify `main`, `CajitadeLuna.md`, or `MACRODOWN_MANIFEST.json`. Passing smoke tests does not grant certification or authorize integration.
