# LOUKSNAPG2 — five-model primary E2E execution mission

**Branch:** repair/louksnapg2-gpu-foundation-20261103
**Commit baseline:** 6f9b601feb3b9e0e2be1e716ad204ccd8b5312fc
**Status before this push-triggered run:** E2E workflow was previously marked action_required by GitHub; no model E2E jobs had started.

## Fixed test scope

The workflow executes only the five registered local Cajita model adapters. It does not invoke remote inference endpoints, Hugging Face services, auxiliary models, Tesseract, Whisper.cpp or translation fallbacks.

| Domain | Model/adapter | Fixed acceptance input |
|---|---|---|
| D01_CEREBRO | GPT-OSS compact runtime | Short question about repository contents; output must mention files, source code or documents |
| D03_TRANSCRIPCION | Whisper compact runtime | Locally synthesized “hello world” audio; both words required |
| D04_TRADUCTOR_INTELIGENTE | SeamlessM4T compact runtime | English greeting; Spanish greeting phrase required |
| D05_INTELIGENCIA_DOCUMENTAL | Granite Docling compact runtime | High-contrast invoice image; invoice number 4821 and total 37.50 required |
| D06_SISTEMA_INTELIGENTE | Qwen3 compact runtime | 2 + 2; numeric answer 4 required |

## Interpretation

The workflow uses the exact active compact artifacts, verifies hashes and records per-domain execution, output predicates and resource measurements. A pass proves only these fixed synthetic cases on these compact artifacts. It does not prove held-out accuracy or semantic equivalence to dense upstream checkpoints. Every domain remains HOLD for full model repair/certification until architecture-specific evidence and independent held-out suites pass.

The 490,000,000-byte release cap, original-weight immutability, offline model loading and fail-closed G23/G24 controls remain unchanged.
