# LOUKSNAPG2 — Whisper full-rank offline diagnostic, 2026-11-04

**Status:** Diagnostic-only experiment added; no model repair, runtime promotion or certification is claimed.
**Branch:** repair/louksnapg2-whisper-fullrank-offline-diagnostic-20261104
**Candidate source:** GitHub Actions run 41554376806, artifact louksnapg-whisper-fullrank-q4_0-41554376806.
**Provider policy:** No Hugging Face Jobs, Hub API, tokens, inference endpoints or model downloads are used by this diagnostic.

## 1. Why this candidate is distinct

The active Whisper factors use low-rank INT8 factors (rank 29). Historical Q4 storage only repacks those same factor tensors; the Q2-vs-Q4 comparison showed no semantic improvement. The full-rank Q4_0 candidate is different: it was converted from the pinned full Whisper large-v3-turbo teacher checkpoint to GGML full-rank blockwise quantization, without SVD or low-rank truncation.

Candidate identity:
- Weight bytes: 473,992,235.
- Weight SHA-256: 6e670d7569d1ed261cb8a4e554138f0ba6a17be7c64f079145061f93bac54e80.
- Upstream source revision: 7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7.
- whisper.cpp revision: 482279b8a18855ba741d7b88c30fcb3874691f59.

## 2. Previously observed blocker

Prior Q4_0 evaluation jobs did not measure WER. They stopped at CANDIDATE_MEMORY_PEAK_OVER_1GIB, with recorded peaks of approximately 1.075–1.080 GB. This was a memory acceptance guard, not evidence that WER passed or failed.

This diagnostic tests the exact immutable Q4_0 artifact with a 1.25-GiB CPU memory ceiling, zero swap and one CPU. This is explicitly a diagnostic environment change; the active runtime ceiling remains 1 GiB. It does not waive deployment resource limits.

## 3. Offline test inputs

The diagnostic retrieves no model weights. It downloads the already-built Q4_0 artifact from the repository's earlier GitHub Actions run. It checks the embedded SHA-256 manifest before inference.

Audio cases:
1. A local espeak-ng-generated utterance with exact reference text and word-level error-rate calculation.
2. The pinned tests/jfk.flac fixture from OpenAI Whisper source revision 86098128c0b4f24f0e2aa2994de830614b474227; acceptance checks the known-answer phrase anchors used by that repository's own transcription test.

No external model hub, managed API, remote inference service or credentials are used.

## 4. Distribution and certification boundary

The standalone Q4_0 candidate is below 490,000,000 bytes, but the previously measured complete-release projection is 836,570,159 bytes. It therefore cannot be embedded into the current release package. Any future use requires a separately governed external-asset path and exact-package reconstruction proof.

The diagnostic can establish only whether this specific candidate executes correctly against the selected audio cases within the measured diagnostic resource envelope. It cannot establish equivalence to the teacher model, full held-out WER, operational 1-GiB compatibility, G23/G24, or integral LOUKSNAPG2 certification. Promotion stays unauthorized.
