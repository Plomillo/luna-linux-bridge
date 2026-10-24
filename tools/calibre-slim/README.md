# Cajita Calibre Slim Candidate v1

Status: EXPERIMENTAL / NOT CERTIFIED. This is a separate candidate and does not replace the current Cajita runtime, its Macrodown manifest, or the canonical architecture.

## Objective

Reduce the official Calibre distribution to a headless conversion tool for PDF and EPUB workflows. The user-facing command is calibre-slim-convert. It accepts PDF, EPUB, HTML, TXT, and DOCX inputs, but limits outputs to PDF and EPUB. Calibre's internal OEB intermediate is retained because the upstream conversion pipeline uses it.

The candidate starts from the official Linux x86-64 binary distribution and separately captures the official source distribution. Both downloads are pinned by SHA-256 and size in source-lock.json. The upstream release is Calibre v9.17.0, commit e6b9e09472f6e63f8a12bf376eb54836042f0f5f. The signed tag is reported as verified by GitHub.

## What is removed

The pruning script replaces the broad built-in plugin registry with a narrow registry for the required conversion formats and default profiles. It removes non-target conversion plugins, GUI action and ebook-store modules, device drivers not required by the generic device interface, catalog/editor/news modules, UI translation catalogs/resources, translated man pages, and command wrappers outside the conversion scope. The small `archive_input.py` helper is retained even though it is not a public conversion plugin, because the official `TXTInput` module imports its `archive_file_data` helper at module load. The frozen-payload scrub therefore retains this dependency instead of treating it as dead code.

The script edits only a disposable extracted candidate tree. It does not edit the canonical runtime or the upstream download. It preserves LICENSE and COPYRIGHT material in the candidate.

The source pruning step produces a reviewable, pruned Python source snapshot; the runtime overlay contains the narrowed `builtins.py` registry. The upstream native launcher is not rebuilt and its frozen import index is not regenerated. Instead, the workflow asks the official embedded runtime for the authoritative path/offset/size index, records the index and archive hashes, and zeroes payloads for explicitly excluded modules in place while preserving every offset and the frozen archive's exact byte length. The post-pruning conversion suite is required to pass before packaging.

This method makes the selected out-of-scope module payloads unavailable without risking offset drift, but it is not a proof that all dead code has been removed. Unclassified modules remain intact, and the raw frozen archive length does not decrease; the benefit is in the compressed distribution and the feature payload that remains usable. A full frozen archive rebuild with a regenerated native index is still a separate release gate.

## What must not be mistaken for junk

Interface translations are not the same as language support for book content. The candidate deliberately preserves Unicode processing, fonts, document language handling, right-to-left and CJK support resources, and the Qt/WebEngine dependencies used to render PDF output. It does not remove language-specific resources merely because a user interface is not translated.

PDF input is intrinsically lossy for many complex, multi-column, image-based, scanned, math-heavy, or non-Unicode-font documents. The slim candidate must not claim that slimming fixes those upstream limitations.

## Execution and gates

The workflow downloads the pinned source and binary artifacts, verifies their SHA-256 values, runs baseline conversion canaries, applies the pruning profile to a copy, runs the same canaries after pruning, checks output file signatures and EPUB ZIP integrity, checks that the smoke marker survives PDF-to-EPUB conversion, records raw and compressed sizes, and publishes a candidate artifact only if the post-pruning tests pass.

The source archive is retained as a companion source snapshot with the same pruning policy applied. This workflow does not compile Calibre from the altered source archive; the binary artifact is the official upstream binary distribution with the staged pruning transformation applied. Source rebuildability and broad functional equivalence therefore remain separate validation gates.

No source file is called dead solely because a text search found no references. The pruned profile is a controlled feature subset, not a claim that every removed module was defective. Fixes to upstream bugs must be issue-specific, regression-tested, and recorded as separate patches.

## Evidence required before integration

- Pinned upstream artifacts pass SHA-256 and source-identity checks.
- Baseline PDF/EPUB canaries pass before pruning.
- PDF-to-EPUB, EPUB-to-PDF, HTML/TXT/DOCX-to-PDF and HTML/TXT/DOCX-to-EPUB pass after pruning.
- EPUB containers are valid and the smoke marker survives round trips where extraction is applicable.
- Runtime and archive sizes are measured rather than estimated.
- License, copyright, source snapshot, patch script, and pruning manifest are included.
- Independent validation and a real Cajita integration/resource-budget test are completed before certification.

The candidate is not added to MACRODOWN_MANIFEST.json automatically. The current runtime has only a small raw byte margin under its 470,000,000-byte cap; this artifact must remain separate until global byte rebalancing proves it can fit without breaking the hard limit.