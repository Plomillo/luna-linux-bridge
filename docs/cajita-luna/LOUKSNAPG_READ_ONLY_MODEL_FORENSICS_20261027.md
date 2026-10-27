# LOUKSNAPG read-only model forensics — 2026-10-27

## Control state

- Repository: `Plomillo/luna-linux-bridge`
- PR: [#157](https://github.com/Plomillo/luna-linux-bridge/pull/157)
- Source head inspected: `5d8c035e64c6c523afd14e779e8df8e65ce64b61`
- Frozen candidate artifact from the previously completed G24 run: 373,265,919 bytes; SHA-256 `989277d80a596a8a38564d4234e441896b105b2ba4a5843ed99a0877c88ca663`.
- Candidate mutation: **FORBIDDEN** during this forensic pass. No rebuild, replacement, quantization, file write, model inference, download, or promotion was performed.
- Intended local inspection envelope: read-only metadata/headers and hashes; one CPU thread maximum; no inference. A numeric RAM ceiling has not been provided, so no model-loading operation is authorized by this record.

## New observation: local read-only channel did not complete

The online Desktop Commander device `LOUKSNA` was selected. Read-only directory inspection failed with:

`Cannot find module .../@wonderwhy-er/desktop-commander/dist/utils/feature-flags.js imported from .../usageTracker.js`

A metadata read of the previously recorded Docling path also returned `ENOENT`; the available directory-listing operation failed before it could enumerate the current filesystem. Therefore this pass obtained **no fresh local model bytes, hashes, headers, or memory measurements**. Existing Git evidence below is not represented as a new local read.

## Evidence already present in Git

### Docling — D05_DOCLING

Source record: [LOUKSNAPG_DOCLING_LOCAL_ORIGINAL_REFERENCE_20261026.json](LOUKSNAPG_DOCLING_LOCAL_ORIGINAL_REFERENCE_20261026.json)

- Model: `ibm-granite/granite-docling-258M`; local GGUF size 138,559,520 bytes; recorded SHA-256 `4ba41a480d2b6594613a23819df8fcc382d9dab9691e28bf327b3ac799fe0a82`.
- Vision projector: 190,031,712 bytes; recorded SHA-256 `4b7b2c4ed3162bd9cb323668c188e2324838b8f8ca4f3f9767f16c4c600d43ad`.
- With the official prompt `Convert this page to docling.` and 512-pixel input, output repeated “Description” and did not extract the expected invoice total `133.45`. The repeat-penalty follow-up emitted `<br/>` loops. Both are recorded `FAIL_QUALITY`; loading success is not task-quality success.
- Repair direction: verify model/projector pair and runtime compatibility; then test the official document-conversion path against OCR/layout ground truth. Do not tune decoding parameters alone and infer equivalence.

### Five model targets — prior G24 record

The G24 evidence already linked in PR #157 records 0/5 model-target quality approvals. The previous package-level result applies only to its exact subject hash; it is not evidence for a different candidate or source commit.

| Target | Pinned upstream model in the integral gate | Required repair evidence |
|---|---|---|
| `D01_CEREBRO_ROOT` | `openai/gpt-oss-120b` | Verify source/shard inventory and tensor identity; bounded load/inference; semantic task suite; peak RSS under an explicitly authorized ceiling. Prior G24 noted RSS above 1 GiB and degenerate output. |
| `D03_TRANSCRIPCION_ROOT` | `openai/whisper-large-v3-turbo` | Verify weight/tokenizer/runtime pairing; compare transcript against a fixed reference with WER/CER and language coverage. Prior output failed quality. |
| `D04_TRADUCCION_GENERAL` | `facebook/seamless-m4t-v2-large` | Verify weight/config/tokenizer pairing; bilingual reference set, direction coverage, adequacy and hallucination checks. Prior output failed quality. |
| `D05_DOCLING` | `ibm-granite/granite-docling-258M` | Verify GGUF plus projector, preprocessing, prompt, and layout extraction; invoice total and document-structure checks. Existing local test failed quality. |
| `D06_ANALISIS_AVANZADO` | `Qwen/Qwen3-14B` | Verify actual model variant, config, tokenizer and weights together; run bounded semantic tasks and factuality checks. Prior output failed quality. |

Official source revisions and model revisions are pinned in `tools/louksnapg_integral_gate.py`; those identifiers must be preserved in per-model evidence. The integral gate requires real inference, weight hashes before/after, official source/revision identity, test and quality-report hashes, and all 21 target results. Primitive smoke tests and synthetic reports are not substitutes.

## Next authorized sequence

1. Restore the local read-only inspection channel without changing model files or the candidate. Confirm the device and model paths via directory metadata before opening any weights.
2. Record each model's path, byte size, SHA-256, file type/header metadata, adjacent config/tokenizer/projector files, and provenance. Hash incrementally with one CPU thread; do not load tensors into RAM.
3. Compare the observed files to pinned source identities and the candidate's own manifest. Report missing, mismatched, truncated, or unpaired assets before attempting any inference.
4. Only after a concrete RAM ceiling is specified and the model/runtime pair is verified, run one bounded functional probe at a time. Preserve raw outputs and resource telemetry; never rewrite the frozen candidate.
5. Implement any justified repair in a separate, explicitly versioned candidate branch/artifact. Bind its exact bytes to all 21 target tests, independent G23 attestation, separate G24 decision, Kestra receipt, rollback and non-regression evidence.

## Current forensic disposition

`CANDIDATE_FROZEN=TRUE`
`FRESH_LOCAL_MODEL_READ=NOT_COMPLETED_TOOLING_FAILURE`
`MODEL_REPAIR_FINDINGS=EXISTING_GIT_EVIDENCE_ONLY`
`INTEGRAL_CERTIFICATION=HOLD_NOT_GRANTED`

This report is additive evidence only. It does not alter or certify `LOUKSNAPG.md`.
