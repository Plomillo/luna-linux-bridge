# Cajita demand router — candidate implementation

Status: additive candidate, not certified.

## Scope

This change adds a standard-library-only planner for the six operational domains and preserves the existing 14 canonical command routes. It does not rewrite Louksna's canonical authority or silently reassign agents, engines, or commands. The route matrix is embedded as data and validated by self-test.

The planner separates three levels:

1. Canonical route profile: command, allowed agents, engines, criticality, and initial domain hint.
2. Demand classification: a deterministic keyword preclassifier adds domains required by the concrete task, such as audio transcription, document extraction, translation, or reasoning.
3. Resource-aware execution gate: a task is not authorized until a real task adapter is registered and peak RSS is measured. Smoke tests are evidence only for the exact smoke operation; they do not establish task quality.

## Resource policy

- RAM ceiling: 1,024 MiB.
- One CPU-thread budget per worker.
- One domain process at a time.
- On-demand sequential stages; unload between stages.
- The planner itself does not load model weights.
- An unknown command, unregistered adapter, missing resource measurement, or missing capability fails closed.

These are guardrails, not proof that the model payloads can execute under a 1 GiB cap. Peak RAM is not measured for any of the six domains. The router also does not execute domain tasks; it emits a route plan and evidence blockers.

## Commands

From the cajita-luna-runtime directory:

- python cajita_router.py selftest
- python cajita_router.py routes
- python cajita_router.py plan --request "Transcribe este audio"
- python cajita_router.py plan --route-command "/play traductor" --request "Traduce este párrafo al inglés" --trace-file logs/router-audit.jsonl

The audit trace intentionally stores request hashes and route metadata, not raw request text.

## Blockers before operational promotion

- Connect Cerebro's real inference API to the request classifier; current classification is lexical and deterministic.
- Register and test task adapters for answer generation, transcription, translation, document extraction, PDF generation, and advanced reasoning.
- Measure peak resident memory and runtime latency per domain on the target device.
- Add adapter shutdown/unload verification and prove that resources are released between stages.
- Run independent validation and applicable governance gates. This candidate does not claim certification.


## Entry through the existing Cajita runtime

The planner is also exposed through the existing runtime CLI:

- python cajita-luna-runtime/cajita_runtime.py routes
- python cajita-luna-runtime/cajita_runtime.py selftest
- python cajita-luna-runtime/cajita_runtime.py plan --request "Transcribe este audio"
- python cajita-luna-runtime/cajita_runtime.py plan --route-command "/play traductor" --request "Traduce este párrafo al inglés"

This is CLI integration for planning only. It does not turn current model smoke entrypoints into task-execution adapters.


## Functional model adapters and live resource gates — 2026-10-23

The additive module \`cajita_model_adapter.py\` provides a real-task adapter candidate for D01, D03, D04, D05 and D06, plus a read-only registry self-test for D02. Model adapters invoke each existing low-rank runtime and use local-only tokenizer/config loading. D05 also has a standard-library PDF writer; PDF generation does not claim to be an AI-model inference operation.

Before running a model task, the adapter verifies the fixed SHA-256 of \`CAJITA_RUNTIME_V1/weights_manifest.json\`, then verifies the selected model asset size/hash and rejects Git LFS pointer text. The CI job checks out with \`lfs: true\`; binary weights are required to be materialized before inference.

Commands, to be run from the repository root:

- \`python -B cajita-luna-runtime/cajita_runtime.py adapter selftest\`
- \`python -B cajita-luna-runtime/cajita_runtime.py adapter measure --domain D01_CEREBRO --max-rss-mib 800\`
- \`python -B cajita-luna-runtime/cajita_runtime.py adapter measure-all --max-rss-mib 800 --timeout-seconds 600 --report-file artifacts/cajita-resource-evidence.json --trace-file artifacts/cajita-resource-audit.jsonl\`
- \`python -B cajita-luna-runtime/cajita_runtime.py adapter generate-pdf --text-file input.txt --output-file output.pdf\`

Each inference stage runs as its own child process. The supervisor samples RSS every 50 ms and compares this with the child's OS high-water mark, terminates a worker that crosses the configured ceiling, and confirms the PID is reaped before returning. The default worker ceiling is 800 MiB, reserving at least 224 MiB from the 1,024 MiB global goal for the OS and supervisor. This is a watchdog based on process RSS sampling, not a kernel/cgroup hard memory reservation; rapid spikes can still occur between samples. The report makes this enforcement boundary explicit.

The durable report/audit records commit, weight/input/output hashes, RSS, elapsed time, return status and process-reaping evidence. It does not persist raw prompt text or generated text. The input-file path is not stored in the resource report; only byte count and SHA-256 are recorded.

The resource workflow executes minimal real inference one domain at a time, uploads the report as a GitHub Actions artifact, and fails if an adapter, asset hash, memory measurement or process-reaping check fails. A synthetic silent WAV validates the transcription code path, a tiny local text is used for translation, a synthetic PPM image validates document-model inference, and short prompts validate language-model generation. These are interface/inference tests only: transcription WER, translation adequacy, OCR/layout quality and reasoning quality are not certified by them.

The anti-hallucination ONNX file remains blocked: ONNX Runtime is not in the current dependency lock, and the payload architecture is not independently verified. It must not be reported as an active inference adapter. Peak RSS remains unmeasured until the host's actual inference workflow produces evidence; therefore the route planner still fails closed for execution when a required domain lacks a measured profile.
