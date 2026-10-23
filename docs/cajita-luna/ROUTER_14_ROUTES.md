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

These are guardrails, not proof that the model payloads can execute under a 1 GiB cap. Peak RAM is not measured for five model domains. The router also does not execute domain tasks; it emits a route plan and evidence blockers.

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
