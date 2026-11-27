# C05 forensic audit — 2026-11-26

## Scope and checkpoint

- Repository: `Plomillo/luna-linux-bridge`
- Branch: `repair/metagente-luna-structured-20261125`
- Audited HEAD: `3f1d186f5e3903cfe36c9ed76644236e439cbfc`
- Parent/checkpoint: `5251c8ac747d2588f096c4e61f2f8aadae04f59e`
- Branch comparison: identical to audited HEAD; 1 commit ahead of parent, 0 behind.
- No source, historical dossier, or original training-program file was modified by this audit.

## Normative sources

- `PROTODEFINITIVO.txt`: Git blob `c40ca28ef8e515b25c8d8c6b035d4e0a8eebe2bf`.
- `PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt`: Git blob `c259b6bca37fdfc9711ffda07b3e388e3b9774ff`.

The protocol defines C05 as individual execution of INF-0001 through INF-1000. Each case must have an individual dossier and authentic result; NOT_RUN is not execution. The training program further requires preflight, frozen fixture/hash, environment.lock, procedure, stdout/stderr, exit code, observed output, independent oracle, metrics, SHA256SUMS, negative and boundary controls, and three repetitions from a clean state. Simulation is not execution.

## What the audited Grok commit changed

Commit `3f1d186f5e3903cfe36c9ed76644236e439cbfc` changes exactly four files:

1. Adds `OWNER_RESOLUTION_HUMAN_REVIEW.json`.
2. Modifies `src/metagente_luna_s4/c05_validator.py`.
3. Modifies `src/metagente_luna_s4/runner.py`.
4. Modifies `tests/test_c05_validator.py`.

The change correctly rejects NOT_RUN rows even when `individual_investigation=true`. It also preserves the original human-review phrases and records an owner resolution that human review is not an operational gate. It does not implement a TEO executor: the runner still returns BLOCKED for every `MGL5-TEO-` case because no hermeneutic capability is registered.

## Reconciled C05 population

The branch's `S4_2_C05_DOSSIERS.jsonl` contains exactly 1,000 unique INF IDs, but all 1,000 rows have:

- `execution_status=NOT_RUN`
- `dossier_status=INCOMPLETE`
- no RUN_ID or repetition IDs
- no fixture artifact
- no execution stdout/stderr or metrics

The dossier itself states that the source text was parsed but the case was not executed.

Six auxiliary execution ledgers contain 106 unique INF IDs in total:

| Ledger | Rows | CRITERION_MET | BLOCKED |
|---|---:|---:|---:|
| S4_2_CASE_EXECUTION_RESULTS.jsonl | 21 | 21 | 0 |
| S4_2_CASE_EXECUTION_RESULTS_BATCH2.jsonl | 29 | 29 | 0 |
| S4_2_CASE_EXECUTION_RESULTS_BATCH3.jsonl | 15 | 15 | 0 |
| S4_2_CASE_EXECUTION_RESULTS_BATCH4.jsonl | 9 | 9 | 0 |
| S4_2_CASE_EXECUTION_RESULTS_BATCH5.jsonl | 25 | 25 | 0 |
| S4_2_CASE_EXECUTION_RESULTS_BATCH6.jsonl | 7 | 4 | 3 |
| **Total** | **106** | **103** | **3** |

These 106 helper records do not close the 1,000-case C05 population. All identify the backend as `LOCAL_TEST_ONLY`. The first 50 explicitly state that negative and boundary runs were not executed. Independent review is recorded as NOT_AVAILABLE for those first 50 and is absent from the remaining 56. The three BLOCKED rows have no repetition IDs. These records remain auxiliary evidence and must not be promoted to C05 PASS.

Therefore, 894 INF IDs have no corresponding row in these six auxiliary execution ledgers, and all 1,000 contractual C05 dossiers remain NOT_RUN.

## Validator defects confirmed by source inspection

The current validator is a partial correction, not a complete evidence validator:

1. `_evidence_matches` hashes an inline `evidence_payload`; it does not open or verify an external artifact produced by an execution.
2. It does not require RUN_ID, fixture file, environment.lock, procedure, stdout/stderr, exit code, observed.json, oracle.json, metrics.json, SHA256SUMS, or three actual repetitions.
3. It does not verify fixture hashes against fixture bytes or establish fixture provenance.
4. It does not verify RUN_ID uniqueness across dossiers.
5. It does not enforce negative and boundary runs or clean-state repetitions.
6. It does not enforce consistency between execution and contractual status. A row with `execution_status=FAIL` and `contract_status=PASS` can avoid the current contradiction checks if it has a matching inline payload hash, a nonempty fixture hash, and no other flagged field.
7. The test helper `_with_evidence("FAIL")` manufactures 1,000 in-memory strings and their hashes, then asserts C05 PASS. This proves acceptance of synthetic rows, not authentic execution.

The runner is restricted to `LOCAL_TEST_ONLY`; `guard.authorize` rejects other backends because no sandbox is available. Runner result statuses also include EXECUTED, ERROR, and REJECTED, while the C05 validator's accepted execution outcomes are PASS, FAIL, BLOCKED, and INCONCLUSIVE. A real, explicit adapter and status contract are still required.

## CI evidence

Workflow run `45902718124` completed successfully. The log confirms:

- Python 3.12.15 environment setup.
- `pytest tests`: 43 passed in 4.11 seconds.
- `ruff check src tests`: all checks passed.
- No workflow artifacts were published.

These are code-level CI results only. They do not represent execution of the 1,000 INF cases or C05 certification.

## Human-review resolution

The owner-resolution record states `human_review_operational_gate=false`, `automated_validation_required=true`, and `fake_human_attestation=false`. This audit preserves that resolution and does not alter the source program. The source still contains human-review wording, including TEO requirements; any automated replacement is an explicit owner-authorized deviation and must remain traceable. No human reviewer or attestation is to be fabricated.

## Verdict

`C05 = NOT_PASSED`.

Reason: 1,000 contractual dossiers remain NOT_RUN. The 106 auxiliary records are not a substitute for those dossiers and do not satisfy the full evidence protocol. The synthetic validator test is not evidence of real case execution.

## Required work before C05 can close

1. Define and enforce a versioned evidence schema matching both normative sources.
2. Replace inline self-hashed payload acceptance with verification of real, persisted artifacts and their SHA256SUMS.
3. Enforce execution/contract status consistency, RUN_ID uniqueness, fixture integrity/provenance, environment, procedure, three clean-state repetitions, negative/boundary controls, independent oracle, and per-case evidence.
4. Implement an execution adapter that records actual runner outcomes without converting helper labels such as CRITERION_MET into PASS.
5. Resolve capability coverage for every one of the 1,000 INF cases. Missing capability or missing essential input must be reported, not fabricated.
6. Execute every case individually and preserve PASS, FAIL, BLOCKED, or INCONCLUSIVE as actually observed. NOT_RUN remains unexecuted.
7. Generate the required evidence files and validate each dossier independently.
8. Re-run adversarial tests, the full CI suite, and a population-level C05 validation over the persisted 1,000 dossiers.
9. Advance the global counter only when the protocol's C05 acceptance criteria are evidenced and the required checkpoint is preserved.

This report is an audit record only. It does not claim that C05 has been closed, that the 1,000 cases have been executed, or that the agent is certified.
