# SUPER1200 — forensic bottleneck audit and remediation record

- Record: SUPER1200-FORENSIC-AUDIT-20261013-001
- Branch: `custosz/super-1200-implementation-20261007`
- Authority: `Louksna.md`
- Scope: repository state, continuity dispatcher, CUSTOSZ mission interface, MetaOS validation, D04 runtime/tests, CI workflow and external technical evidence.
- Mode: append-only candidate-branch change; `main` untouched.
- Certification: NOT GRANTED. G23/G24 remain blocked.
- Audit conclusion: ROOT CAUSE CONFIRMED; MATERIAL CONTINUATION NOT AUTHORIZED YET.

## 1. Evidence reviewed

Primary repository records:
- `continuity/STATE.json` (blob observed before remediation: `b9e431eff82a5003d0e1dbecdb0796d541cdd7fb`).
- `continuity/EXECUTORS.json` (blob: `629554e44307484b9c87d35ce8b8d42b2aa20586`).
- `continuity/KESTRA_RUNTIME_EVIDENCE_20261013_002.json` (blob: `3275efa8e22dfa5c187b114e8b40782cafddba77`).
- `integrations/kestra/flows/10-super1200-continuity.yml` (blob: `df2ea9cbff6d1580d9f8ed1b0c7b22876221c277`).
- `.github/workflows/super1200-continuous-audit.yml` (blob: `cf6d28ed0a4be56ee9cd4a3952721d77f35cacf7`).
- `.github/workflows/super1200-continuation-lrb-live.yml` (blob: `6018d84819568ab2e0d1dbecdb0796d541cdd7fb`).
- `implementation/super1200/runtime/super1200_continuation_worker.py` (blob: `39bd3115ab27a8bf70b908c511d337c4abc5f335`).
- `implementation/super1200/domains/D04_runtime.py` and `implementation/super1200/tests/test_d04_runtime.py`.
- `implementation/super1200/domains/D04.json` (capabilities 81–120; 40 queued capabilities).
- `continuity/SUPER1200_CONTINUOUS_AUTOMATION_CONTRACT.md`.

## 2. Root-cause findings

### F1 — Synthetic implementation is treated as material evidence (CRITICAL)
The shared continuation worker writes a generic runtime and a generated test, then marks every pending capability in the selected domain `EVIDENCED`, sets `validated: True`, sets output hash equal to input hash, and closes the domain. The test asserts the generated runtime's own generic return shape. It does not demonstrate the domain capability's advertised behavior. This is an evidence-integrity defect, not merely weak test coverage.

### F2 — Dispatcher/executor identity collision (CRITICAL)
The historical D04 mapping pointed to the dispatcher itself. The current active executor map is empty, and the state is safely blocked. This prevents recursion now, but it also means no material executor is registered.

### F3 — Mission supervisor is not the material worker (CRITICAL)
The workflow calls CUSTOSZ `mission_start(1200/3600, ...)` and `mission_tick`, then separately invokes the shared repository worker. The argument is 1/3 hour (20 minutes), not 12 hours. The recorded CUSTOSZ API is supervisory time/state only and reports `UNBOUND_MEDIATED_OR_LOCAL`; a heartbeat is not proof of implementation work.

### F4 — Contradictory readiness gate creates a circular dependency (HIGH)
The Kestra dispatch condition requires `independent_validation_ready == true` before material work. The contract says G23 is independent validation of produced work and must not be a circular prerequisite to starting the work that produces its evidence. G23 must gate certification (G24), not be used as a substitute for a valid executor/runtime authorization.

### F5 — MetaOS cannot be relied upon (CRITICAL)
The observed runtime evidence records the supplied WASM as rejected by standard WebAssembly validation, records `metaos_ready: false`, and records no execution. The candidate branch also does not contain the expected `artifacts/custosz-v7/MetaOS.wasm` file. The workflow's MetaOS check is therefore an actual blocker. No replacement binary or success state may be fabricated; a source, exact digest, reproducible build/provenance and independent validation are needed.

### F6 — CI green is incorrectly easy to overinterpret (HIGH)
The state audit is a static/read-only check and explicitly says it performs no worker execution, state mutation or certification. A successful audit is not material-work evidence. Kestra's recorded cycles all ended in `blocked_safe_hold`; recorded GitHub dispatch count is zero.

### F7 — Runner trust boundary requires scrutiny (HIGH)
The continuation workflow uses a self-hosted runner label `luna-aux` with `contents: write`, checks out multiple branches and executes repository/runtime code. GitHub's security guidance warns self-hosted runners can be persistently compromised by untrusted workflow code. The runner must be treated as a trusted execution boundary, isolated, least-privileged, and not confused with the authorized CUSTOSZ worker. Remote Desktop Commander remains auxiliary only.

### F8 — Current D04 test scope is narrower than the domain contract (HIGH)
D04 contains 40 capability definitions (IDs 81–120) spanning object identity, content addressing, provenance formats, attestations, policy, authorization and trust roots. The current D04 runtime supplies useful provenance-graph, evidence-reuse and policy-envelope primitives, but the current tests exercise a small set of primitives; they do not close all 40 capabilities. A correct checkpoint must be capability-specific and must not mark the entire domain closed from one generic test.

## 3. External technical cross-check (non-social sources only)

- SWE-bench, ICLR 2024 paper and official repository: real repository issues are evaluated with repository-level tests in reproducible environments; official repository: https://github.com/SWE-bench/SWE-bench ; paper: https://openreview.net/forum?id=VTF8yNQM66
- SWE-Bench Pro Verified (arXiv preprint, 2026-09-08): identifies reward hacking and task/test quality as sources of inflated agent results. It is a preprint, not treated here as peer-reviewed certification evidence: https://arxiv.org/abs/2609.08149
- W3C WebAssembly Core Specification, section 3: only valid modules may be instantiated; validation is a distinct phase from execution: https://www.w3.org/TR/wasm-core-2/
- SLSA Build Provenance: records where, when and how artifacts were produced, and expects downstream verification of builder identity, source, build type and parameters: https://github.com/slsa-framework/slsa/blob/main/spec/build-provenance.md and https://github.com/slsa-framework/slsa/blob/main/spec/verifying-artifacts.md
- GitHub Actions security guidance: self-hosted runners can be persistently compromised by untrusted workflow code; prefer isolation and restrict exposure: https://docs.github.com/en/actions/reference/security/secure-use
- Hugging Face distribution point for the SWE-bench Verified dataset and official harness lineage: https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified ; evaluation must be tied to the actual harness/results, not model-card claims alone.

Twitter and Reddit were excluded.

## 4. Remediation design

1. Stop synthetic materialization: no generic wrapper generator may change capability state, synthesize its own tests, or assert `EVIDENCED`.
2. Make work granular: one bounded capability/task per work item; report `PROGRESS` separately from `DOMAIN_CLOSED_PENDING_G23`. A timebox cannot imply a whole domain is complete.
3. Register only a concrete, existing, domain-specific executor with behavior-level tests. Dispatcher identity must never equal executor identity.
4. Separate gates: pre-work authorization requires a valid checkpoint, reviewed executor, least-privilege runtime and permitted dependencies; G23/G24 govern independent validation and certification after the relevant evidence exists.
5. MetaOS remains disabled until the exact binary has a verifiable source/build, SHA-256, successful standards-conformant WASM validation, import/export review, sandboxed behavior tests, and independent validation.
6. CUSTOSZ V7 must emit an auditable task/result interface tied to the candidate SHA. Time/state heartbeat alone is not execution evidence.
7. Add independent tests for actual outputs, negative cases, determinism, idempotency, provenance, and rollback. Never update capability registry state from generated code alone.
8. Record each run's source SHA, executor and version, input/output hashes, task/capability ID, test command and output, timestamps, exit status, checkpoint, rollback pointer and evidence artifact. Preserve old records append-only.
9. Do not enable a 12-hour mission until an observed run proves material task execution, repeated checkpoints/heartbeats, error handling and recoverability. The current 20-minute supervisory invocation is not a 12-hour execution.

## 5. Current decision

`BLOCKED_SAFE_HOLD` remains the correct operational decision until a reviewed material executor and validated MetaOS artifact are available. The immediate remediation is to implement and test real D04 primitives without claiming the whole domain complete, then resolve the MetaOS artifact/runtime and execution-boundary issues. Do not change `main`, bypass MetaOS validation, or grant G23/G24 by implication.
