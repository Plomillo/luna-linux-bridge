# LOUKSNAPG architectural contract

Contract: `LOUKSNAPG-AC-001`, version `1.0.0`.

This contract formalizes the six authorized obligations: (1) CUSTOSZ V9 primary plus Kestra secondary with separate real run receipts; (2) official upstream source review and exact variant/revision pins before repairing the candidate; (3) real behavior-level validation of all 21 target IDs; (4) persistent, artifact-bound telemetry; (5) separate G23 and G24 with non-regression and rollback; and (6) fail-closed prohibitions including no heavy model-weight downloads and no Remote Commander.

The static CI check proves only that the contract has not drifted. It always leaves `release_eligible=false` and `global_certification=NOT_GRANTED`. A product can be considered for release only when a real `LOUKSNAPG_ARCHITECTURE_EXECUTION_EVIDENCE/1.0` file binds the exact contract SHA-256, source commit and candidate SHA-256, both worker receipts, all five model-source records, a verified material repair, 21 non-synthetic functional results, persistent telemetry, the Kestra audit, G23 and a separately signed G24, host matrix, rollback, non-regression, and the canonical block/axiom bindings.

## Evidence-first source notes

- GPT-OSS upstream: https://github.com/openai/gpt-oss and https://github.com/openai/gpt-oss/blob/main/README.md
- Whisper upstream: https://github.com/openai/whisper and https://github.com/openai/whisper/blob/main/README.md. Whisper's `turbo` task is transcription; the upstream documentation says it is not trained for translating non-English speech into English.
- SeamlessM4T upstream: https://github.com/facebookresearch/seamless_communication and https://github.com/facebookresearch/seamless_communication/blob/main/docs/m4t/README.md. The model card lists the v2-large repository at a roughly 29.9 GB total size; these weights are not downloaded by this contract validation.
- Granite Docling: https://huggingface.co/ibm-granite/granite-docling-258M and https://www.ibm.com/granite/docs/models/docling
- Qwen3: https://github.com/QwenLM/Qwen3 and https://github.com/QwenLM/Qwen3/blob/main/docs/source/inference/transformers.md

Source browsing and static contract tests do not count as model execution. Unavailable runtimes, missing model files, unpinned revisions, missing telemetry, failed task assertions, absent G23, or missing signed G24 must remain `HOLD_NOT_CERTIFIED`.
