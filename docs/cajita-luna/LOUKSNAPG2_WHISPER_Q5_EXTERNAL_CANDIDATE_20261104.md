# Whisper Q5_0 — external candidate asset (draft)

**Branch:** repair/louksnapg2-whisper-q5-external-asset-20261104  
**Source workflow:** run 41788008012  
**Q5 build artifact:** 13302725061 (584,516,333 bytes)  
**Q5 evaluation artifact:** 13302302384  
**Target release tag:** louksnapg2-whisper-fullrank-q5_0-candidate-20261104

## Evidence

The Q5_0 full-rank candidate is materially distinct from the active Whisper rank-29 INT8/SVD representation. Its Q5 weight is 574,041,195 bytes with SHA-256 \`394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2\`.

Teacher checkpoint identity: OpenAI Whisper large-v3-turbo, SHA-256 \`aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a\`. Conversion tool: whisper.cpp revision \`482279b8a18855ba741d7b88c30fcb3874691f59\`.

Q5_0 passed two fixed tests in a one-GiB cgroup with zero swap and one CPU:
- local synthetic audio: exact \`Hello world.\`;
- pinned JFK recorded speech: exact known-answer transcript, WER 0.00.

Maximum native Whisper process RSS was 759,226,368 bytes. The evaluation reported no OOM events.

## Strict boundaries

- Two tasks are not a representative held-out speech corpus. Full WER validation remains pending.
- The active Whisper runtime remains unchanged and continues to fail its current synthetic E2E case.
- Q5 is not integrated into Cajita and is not a domain repair certificate.
- Candidate weight alone is 574,041,195 bytes; the recorded complete-release projection is 936,619,119 bytes, above the 490,000,000-byte package cap.
- The candidate therefore remains external and non-promoting. It must not be silently embedded or substituted.
- The GitHub Release is deliberately created as a draft and prerelease, not published as an operational runtime.
- Original teacher checkpoint, active weights, canonical files and certification state remain unmodified.

No Hugging Face platform service, Hub API, token or remote inference endpoint is used.
