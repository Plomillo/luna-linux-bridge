# LOUKSNAPG architectural contract

Contract: `LOUKSNAPG-AC-001`, version `1.0.0`. The integrated LOUKSNAPG distribution ceiling is **479,000,000 bytes**; the Cajita runtime archive has its own separate **470,000,000-byte** ceiling.

This contract formalizes six mandatory obligations: (1) CUSTOSZ V9 is the bounded primary worker and Kestra the independent secondary auditor, each with a real execution receipt; (2) official upstream source and model repositories are pinned to exact revisions; (3) all 21 registered targets need real behavior-specific validation and task-level semantic quality; (4) telemetry is persistent, ordered, and bound to the exact source commit, contract digest and candidate digest; (5) G23 is independent validation and G24 is a separate signed authorization, followed by non-regression and rollback verification; (6) fail-closed prohibitions include no heavy model-weight downloads, no Remote Commander, no synthetic evidence as product proof, and no unauthorized canonical or model substitution.

The static CI check proves only that the contract has not drifted. It always leaves `release_eligible=false` and `global_certification=NOT_GRANTED`. A model execution is not a semantic-quality pass; an engine startup/smoke test is not a consumer-task pass; package identity integrity is not functional certification.

### C4 post-dispatch telemetry rule

C4 has two distinct telemetry artifacts. `LOUKSNAPG_TELEMETRY_PREAUDIT.json` is the immutable, hash-bound input snapshot sent to the secondary auditor; it records that dispatch is pending and must not be rewritten afterward. Once dispatch is attempted, the workflow materializes the actual `LOUKSNAPG_KESTRA_AUXILIARY_RECEIPT.json` and appends one final event, `KESTRA_AUDIT_RESULT`, to `LOUKSNAPG_TELEMETRY_FINAL.json`. That event binds the receipt's byte-level SHA-256, status, execution-ID presence, terminal state, source commit, candidate SHA-256 and contract SHA-256. The final envelope is re-hashed, and the six-obligation audit validates the appended event against the actual receipt file. A missing receipt or `NOT_CONFIGURED` receipt is recorded as `HOLD`; it cannot count as a Kestra execution receipt or make C1/C5 pass.

This preserves the preaudit evidence sent to Kestra and eliminates a false-positive where 11/11 pre-dispatch event types passed traceability while the actual Kestra result was not bound into the audited record. The complete final telemetry remains `INCOMPLETE_HOLD` until the worker receipt, all 21 real task results, signed G23, separate signed G24, host matrix, non-regression and rollback checks are independently evidenced.

## Pinned official sources

### Calibre Slim document-conversion runtime

The document-conversion shim is bound to the signed official Calibre release **v9.17.0**. GitHub's official release metadata confirms the tag object `58cfea71a2c2d893b853d73ca586ec9b28f7b2ba`, whose signed payload points to source commit `e6b9e09472f6e63f8a12bf376eb54836042f0f5f` ("version 9.17.0"). The source-lock validator now binds both official release assets by exact ID, URL, filename, byte size and SHA-256; it also requires the verified tag-signature status reported by GitHub. This workflow only reads release metadata and **does not download the 201,590,724-byte Calibre binary or its source archive**.

The embedded overlay is separately locked to `calibre-slim-overlay.tar.xz`, 58,180 bytes, SHA-256 `dc1518eccd24d0bb6a294918381d9d42fa24df8b05026d1f173dadbd6e70977b`. On every invocation the converter re-reads that archive, rejects unsafe/duplicate paths, validates the complete cached file set, file sizes, SHA-256 values, modes and directory set, and refuses cache drift. The discovered system `ebook-convert --version` output must contain exactly one Calibre version token and that token must equal `9.17.0`; partial substring matches such as `19.17.0` or `9.17.00` are denied. Its source-lock SHA-256 and executable SHA-256 are emitted with the runtime identity. This proves the runtime's reported version against the signed release pin; it is not a separate reproduction build from source.


All repository revisions below were recorded as metadata only; model checkpoint payloads were **not** downloaded.

| Target | Official source/code revision | Official model repository revision | Task constraint |
|---|---|---|---|
| `D01_CEREBRO_ROOT` | [openai/gpt-oss @ 5681a6b](https://github.com/openai/gpt-oss/commit/5681a6b6552635e7b29cde94a61ca6a7aee90ebd) | [openai/gpt-oss-120b @ b5c939d](https://huggingface.co/openai/gpt-oss-120b/tree/b5c939de8f754692c1647ca79fbf85e8c1e70f8a) | Preserve the GPT-OSS 120B identity; no silent replacement |
| `D03_TRANSCRIPCION_ROOT` | [openai/whisper @ 8609812](https://github.com/openai/whisper/commit/86098128c0b4f24f0e2aa2994de830614b474227) | [openai/whisper-large-v3-turbo @ 41f01f3](https://huggingface.co/openai/whisper-large-v3-turbo/tree/41f01f3fe87f28c78e2fbf8b568835947dd65ed9) | Transcription only; Whisper turbo is not to be used as non-English-to-English translation |
| `D04_TRADUCCION_GENERAL` | [seamless_communication @ 9a081e9](https://github.com/facebookresearch/seamless_communication/commit/9a081e935c29c6b1e0e05bcbf3fcb623ad306524) | [facebook/seamless-m4t-v2-large @ b8d7691](https://huggingface.co/facebook/seamless-m4t-v2-large/tree/b8d7691bcced0d24b2655f534b6148be78346b72) | Text-to-text translation; v2-large is a roughly 29.9 GB repository snapshot |
| `D05_DOCLING` | [granite-docling-258M @ 982fe3b](https://huggingface.co/ibm-granite/granite-docling-258M/tree/982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe) | Same pinned model revision | Document/image understanding and structured extraction |
| `D06_ANALISIS_AVANZADO` | [Qwen3 @ 7a2f61f](https://github.com/QwenLM/Qwen3/commit/7a2f61ffc7a20d47efcd2bf97f6f2bf52729042e) | [Qwen3-0.6B @ c1899de](https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca) | Qwen3-0.6B only until another exact variant is separately pinned and authorized |

## Observed functional blockers

The execution evidence captured in GitHub Actions run [40284216661](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40284216661) applies to candidate source commit `d09f79a088781d26fc5b1c3e830db9abfb42c147`; it is **historical evidence for that exact candidate**, not evidence for newer source revisions.

- Candidate container integrity passed at 371,947,716 bytes; candidate SHA-256: `febfd2ca07f5238b3ab69e526158532a116c429a608397df86b0136f468f5f84`.
- The six source-bound engine smoke checks passed within that limited scope. They do not establish the 21 consumer-task adapters.
- Each of the five model-backed execution processes returned `PASS_FUNCTIONAL_EXECUTION`, but all five deterministic known-answer quality checks failed. Overall task harness status was `FAIL`, task exit code `3`, and integral functional gate return code `2`. G24 remained `NOT_GRANTED`.
- The runtime candidates produced visibly incorrect outputs: repeated/fragmentary text for GPT-OSS and Seamless, incorrect speech transcription, nonsensical Docling extraction, and incorrect Qwen arithmetic. The detailed output hashes and exact checks are preserved in `LOUKSNAPG_INTEGRAL_REPAIR_BLOCKERS_20261026.md`.
- The same repository records GPT-OSS rank-1 SVD with relative Frobenius error `0.9983363410727844`, and Qwen3 rank-12 SVD with error `0.9964088220513415` (residual before INT8 factor quantization `0.9964067735222465`). These are severe loss indicators, not a runtime-startup problem.
- The auxiliary workflow also recorded Kestra `NOT_CONFIGURED`: `KESTRA_URL` and `KESTRA_API_TOKEN` were absent in GitHub Actions. The workflow failed closed and uploaded its telemetry artifact; no Kestra execution ID was produced.

Consequently, model-source pins, package integrity, contract CI, and smoke tests must not be interpreted as repaired model quality. The current compact model factors do not contain the discarded high-rank components needed to reconstruct the original checkpoints. Because heavy upstream weight downloads are prohibited and model substitution is not authorized, the repository evidence does not support claiming full model repair. The correct release state is `HOLD_NOT_CERTIFIED` until a permitted repair path produces new identity-bound candidate weights and the entire 21-target evidence chain passes.

## Release evidence schema

A release candidate requires an actual `LOUKSNAPG_ARCHITECTURE_EXECUTION_EVIDENCE/1.0` envelope binding the exact contract SHA-256, source commit and candidate SHA-256; both real worker receipts; all five source/model revision records and weight identities; verified material repairs with before/after candidate weight hashes; 21 non-synthetic task results; persistent telemetry; a Kestra execution receipt; independently signed G23; a separately signed G24 by a distinct signer; host matrix; rollback; non-regression; and canonical block/axiom bindings.

If any required input is absent, stale, mismatched, synthetic-only or not independently verifiable, the outcome remains `HOLD_NOT_CERTIFIED`.