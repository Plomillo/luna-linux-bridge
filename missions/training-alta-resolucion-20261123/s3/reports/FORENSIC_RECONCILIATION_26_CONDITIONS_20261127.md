# Forensic reconciliation of the 26-condition contract — 2026-11-27

## Authority and immutable sources

- Contract: `PROTODEFINITIVO.txt`, main Git blob `c40ca28ef8e515b25c8d8c6b035d4e0a8eebe2bf`, 103,187 characters returned by GitHub Contents API.
- Training corpus: `PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt`, source branch `feat/metagente-luna-1000-casos-alta-resolucion`, Git blob `c259b6bca37fdfc9711ffda07b3e388e3b9774ff`, 849,313 characters.
- Current candidate branch: `repair/metagente-luna-structured-20261125`.
- Current PR: #196, head `0e62df72d9859616d831a4553a1aec9f8bbe30d2` at the time of this report; draft, open, not merged.
- CI for that head: run #28 / `45932276871`, SUCCESS. `compileall`, Ruff, and pytest passed; pytest reported 60 passed in 6.43 seconds. This proves the tested code suite only, not completion of a contract condition or population execution.

The protocol defines exactly C01–C26, immutable order, cumulative gates, and checkpoint CP-C01…CP-C26. G23 and G24 are nested within C26, not additional conditions. PASS requires all acceptance criteria and evidence; file creation, successful CI, or summaries alone do not increment the counter. Dependencies prohibit advancing beyond a failed/unpassed predecessor.

## Training program forensic reconstruction

Version 2.0 explicitly begins with all cases NOT_RUN and says it does not assert execution or accreditation.

- INF population: 1,000 unique IDs, MGL5-INF-0001 through MGL5-INF-1000.
- Distribution: 20 domains D01–D20, exactly 50 INF cases each.
- TEO population: 50 unique complementary cases MGL5-TEO-0001 through 0050, outside the 1,000 INF count.
- Q5 checklist: Q5-01 through Q5-15.
- Training order: source-preserving case-by-case, preregistration, clean fixture, preflight/hash check, baseline, operation, output/side-effect capture, negative and boundary controls, three clean repetitions, independent oracle, result. Timing/distributed cases preregister rounds/tolerances.
- Mandatory artifacts per execution: fixture.json, environment.lock, procedure.txt, stdout/stderr, exit_code, observed.json, oracle.json, metrics.json, SHA256SUMS, deviation records; include duration/resource data. No real secrets.
- PASS requires original criterion + independent oracle agreement. FAIL is an observed criterion failure. BLOCKED, INCONCLUSIVE and NOT_RUN are distinct and never PASS. Simulation is not execution. Preserve failures, preregister hypothesis/input/thresholds, and repairs require repeat/regression.
- The 50 TEO cases require hermeneutic controls and source/text/context separation. Original text mentions human competent review. User instruction supersedes the human approval/review gate for this mission: use a documented independent automated validator, but do not claim it is equivalent to human scholarly review; retain source/oracle limitations and scope in the dossier.
- Fifth-order accreditation requires evidence across M0 limitation reproduction, preregistered hypothesis, material adaptive mechanism change, M0/M1 comparison, controlled comparison, ablation, reserved test, non-regression, independent M1, transfer, M1→M2, independent M2, O1–O4 preservation, and traceability. Prompt/tool/model/code swaps alone are expressly insufficient.

## Current evidence census

The historical 1,000-dossier JSONL is intact and is not overwritten:
- `S4_2_C05_DOSSIERS.jsonl`: 1,000 dossiers; all `execution_status=NOT_RUN`; incomplete. Historical S2 `REGRESSION_PASS` does not count as current C05 execution.
- Auxiliary `S4_2_CASE_EXECUTION_RESULTS.jsonl`: 21 records, 21 unique case IDs, 18 capability IDs. They are auxiliary local-test records, not the contractual population. Do not promote them.
- Previous forensic census of the six auxiliary ledgers identified 106 unique INF cases, 103 `CRITERION_MET`, 3 `BLOCKED`; all LOCAL_TEST_ONLY. That census remains historical; the current branch file above is one auxiliary ledger, not a substitute for the six-ledger census.
- Separate negative/boundary control PASS credit was previously 0. Control summaries are not automatically execution evidence.
- The new C05 runner/validator/tests are infrastructure. No complete 1,000-plan source-bound population was generated, and no 5,000 authentic executions were run.
- Therefore C05 remains NOT_PASSED. C08 (exactly 1,000 PASS) is not reached.

## 26-condition sequential status

Status meanings: PASS only with complete acceptance evidence; IN_PROGRESS where active work is recorded; BLOCKED where a predecessor or unmet criterion prevents execution; NOT_STARTED otherwise. No counter increment is authorized by this report.

| Condition | Contract title | Forensic status | Basis / missing acceptance evidence |
|---|---|---|---|
| C01 | Contract and isolated branch | IN_PROGRESS | Contract branch exists, and remediation branch/PR exists. No complete mission manifest, condition register, dependency register, approvals, task/session/queue/resource logs and CP-C01 evidence bundle verified. |
| C02 | Forensic sources and references | IN_PROGRESS | Normative source blobs and training branch were verified; GUI, mother, product branch/tag, Piper refs, dependencies and full reference inventory are not all independently evidenced in a signed checkpoint. |
| C03 | Materialize training program | IN_PROGRESS | Exact training source hash and full corpus structure/IDs/counts verified. CP-C03 manifest, source-preservation artifact and SHA256SUMS checkpoint bundle not verified. |
| C04 | Reproducible training environment | IN_PROGRESS | Python 3.12 CI environment compiled, Ruff passed, 60 unit/adversarial tests passed. The full case harness, environment lock per execution, fixture/oracle isolation and reproducibility acceptance not demonstrated. |
| C05 | Individual execution of 1,000 cases | IN_PROGRESS / NOT_PASSED | Historical dossiers: 1,000 NOT_RUN. New independent validator and orchestrator tests pass, but no full source-grounded plan set and no authentic five-run-per-case population. |
| C06 | Material fifth-order demonstration | BLOCKED | No M0/M1/M2, controlled comparison, ablation, reserved test, independent validation, novel transfer, second evolution evidence. |
| C07 | Forensic diagnosis, debugging and repairs | IN_PROGRESS | C05 infrastructure defects have been addressed iteratively; 60 tests now pass. Complete defect register, original failed-run evidence, root causes, repairs and regression closures are not yet consolidated into CP-C07. |
| C08 | Re-execution and closure of 1,000 | BLOCKED | C05 population execution and C07 repair closure are incomplete; no 1,000/1,000 PASS evidence. |
| C09 | Independent metagent validation | BLOCKED | No independent population-level review/reproduction of dossiers, Q5 evidence and implementation. |
| C10 | Certification and agent freeze | BLOCKED | C01–C09 are not PASS; no certified manifest or frozen candidate hash. |
| C11 | Integrate certified agent | BLOCKED | C10 has not produced a certified frozen version. |
| C12 | Freeze refs and reconstruct product | BLOCKED | C11 dependency; no candidate reconstruction checkpoint linked to the certified agent. |
| C13 | Preserve/debug Directiva V3 GUI | BLOCKED | No GUI reference-diff, functional preservation tests, or CP-C13 evidence in this mission sequence. |
| C14 | Identity, orchestration, chat and concurrent sessions | BLOCKED | No integrated functional evidence for single identity, orchestration, multi-session and concurrent chat/voice during tasks. |
| C15 | Tokenizer/context manager | BLOCKED | No inspected model-tokenizer, accuracy, context isolation, limits or integration evidence. |
| C16 | GitHub App and REST/GraphQL | BLOCKED | Current connector-assisted repo work is not evidence of the packaged product's GitHub App, scoped auth, pagination, rate-limit, REST/GraphQL tests. |
| C17 | Git Database API and Git engine | BLOCKED | No product-runtime object/ref/commit concurrency and recovery tests. |
| C18 | Webhooks, Actions, local-remote bridge | BLOCKED | CI workflow is not proof of packaged event bridge, signature validation, durable run recovery or task execution. |
| C19 | Remote reasoning/local resource budget | BLOCKED | No product-level inference placement, cgroup resource, 1 GiB/1-core design measurement, or efficiency evidence. |
| C20 | Voice, STT, TTS and router | BLOCKED | No installed-product STT/VAD/Piper model/config/speaker/hash/voice continuity/Chatterbox/router E2E tests. |
| C21 | Persistent memory, attachments, task queue and continuity | BLOCKED | No atomic memory, versioning, provenance, encrypted sensitive storage, durable attachments, queue/recovery or two-task isolation proof. |
| C22 | Planning, approval, autonomy, stop/resume, conversation | BLOCKED | No integrated plan approval, scope persistence, chat/voice continuity, stop checkpoint and resume tests. This mission has current explicit user authorization for the C05 remediation; it is not a blanket authorization for future scope. |
| C23 | Security, self-repair, debugging, non-regression | BLOCKED | C05 validator hardening exists; product-level Zero Trust, secrets, session isolation, repair safety, security tests and complete regression evidence remain absent. |
| C24 | Integral audit/debug/short functional tests | BLOCKED | No product-wide inventory, clean install smoke tests, integrated defect closure or short functional battery. |
| C25 | Build DEB and SH from canonical payload | BLOCKED | No certified payload, reproducible build, dependency/model locks, artifact hashes, parity or install evidence. |
| C26 | Independent final validation, certification, delivery | BLOCKED | No clean Debian 13/KDE/Wayland VM evidence, independent artifact testing, G23 PASS, G24 certification, final manifests or release artifacts. |

## Counter and gate decision

```
GLOBAL_CONDITION_COUNTER = 0/26
C01 = IN_PROGRESS
C02 = IN_PROGRESS
C03 = IN_PROGRESS
C04 = IN_PROGRESS
C05 = IN_PROGRESS / NOT_PASSED
C06-C26 = BLOCKED_BY_SEQUENTIAL_DEPENDENCIES
```

No CP-C01…CP-C26 checkpoint is certified by this forensic report. Existing artifacts remain evidence inputs only until each checkpoint's complete acceptance bundle is independently verified.

## Corrective execution queue (no condition skipping)

1. Consolidate C01 mission register/checkpoint and prove branch lineage, approved scope, plan ID and append-only evidence.
2. Complete C02 source-reference inventory with verified commits/files/tags/hashes and discrepancies.
3. Seal C03 training corpus manifest, IDs/domain census, TEO census and source hash/SHA256SUMS.
4. Complete C04 reproducibility: dependency lock, environment and fixture/oracle harness, preflight, isolated runner, adversarial tests and deterministic repeat.
5. Finish C05: source-grounded plan population for all 1,000 IDs; validate plan schema and exact source bindings; execute 3 clean NORMAL + separate NEGATIVE + BOUNDARY per INF case; preserve 5,000 run evidence and independent automated validation. Missing/unsupported capability remains BLOCKED/NOT_RUN, never synthetic.
6. Trigger C07 repair procedure for every observed defect; accumulate append-only failure, root cause, patch, re-run and regression evidence while preserving original failure.
7. Only when C05 and C07 criteria are satisfied, execute C06 Q5 experiment, then C08 closure, C09 independent validation and C10 freeze, in the contract order.
8. Then C11→C26 strictly sequentially, each with its own plan, tests, evidence, hashes and checkpoint; any regression reopens the affected condition and invalidates downstream dependencies.

## Authorized validation policy amendment

For the 50 TEO complementary cases, human approval/review is removed as an operational gate by the user's explicit instruction. The replacement is independent automated validation with primary-text/source provenance, separate evaluator implementation, adversarial checks, complete evidence, and explicit uncertainty. This policy change is not a silent rewrite of the normative source; it is recorded as an authorized mission-level deviation. The resulting scope must not be mislabeled as human scholarly review.

## Non-claims

This report does not certify the agent, claim 1,000 cases executed, declare any condition PASS, or authorize product release. It is a forensic status and checkpoint reconciliation. Historical source files and ledgers remain unchanged.
