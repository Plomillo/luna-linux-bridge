# C05 forensic audit addendum — 2026-11-26

This addendum supplements `C05_FORENSIC_AUDIT_20261126.md`. It preserves the original report and records additional evidence found during the continued repository inspection. No historical source, result, dossier, or prior report is overwritten.

## Additional source records examined

- `activation-20261125/M0_RERUN.jsonl`: 1,000 unique INF IDs; 20 `OBSERVED`, 980 `UNMATCHED`. The 980 unmatched rows record exit codes `[2,2,2]`; these are not current C05 executions.
- `results/S2-20261125.1/CASE_MASTER_REGISTER.jsonl`: 1,000 unique IDs; 20 `REGRESSION_PASS`, 22 `VALIDATED`, 914 `NO_CAPABILITY`, 42 `BLOCKED`, and 2 `OBSERVED_NOT_ACCREDITED`. These are S2 classifications, not C05 accreditation.
- `s3/reports/CASE_ROOT_CAUSE_REGISTER.jsonl`: 1,000 rows; every row labels root-cause status `HYPOTHESIS`. The register does not establish 1,000 demonstrated root causes.
- `s3/reports/S4_2_C05_DOSSIERS.jsonl`: still 1,000 unique dossiers, all `NOT_RUN` and `INCOMPLETE`.
- Six `S4_2_CASE_EXECUTION_RESULTS*.jsonl` ledgers: 106 unique case IDs, comprising 103 `CRITERION_MET` and 3 `BLOCKED`; every ledger reports `LOCAL_TEST_ONLY`. Each record contains three repetition IDs and aggregate observations/logs, but these records do not provide the complete per-run persisted artifact chain required by the normative C05 dossier.
- `S4_2_CONTROL_SUMMARY_AMENDMENT.json`: records 74 unique `CRITERION_MET` cases, zero PASS, and 926 NOT_RUN; it reports separate controls for 50 initial cases plus batches of 15 and 9. This is a summary claim, not a substitute for per-run C05 evidence in the 1,000 dossiers.
- `S3_PILOT.json` and the pilot evidence for `MGL5-INF-0254`: one case, three runs, eight tests passed, and `mass_execution=false`. The per-run `SHA256SUMS` files list instruction, IR, plan, observed, oracle, and environment artifacts. The pilot evidence does not include the complete logs, exit-code, metrics, and independent validation chain required for C05.
- `S4_DOCKER_ISOLATION_REPORT.json` and `S4_1_RUNNER_INTEGRATION_AUDIT.json`: Docker was absent and sandbox isolation was not demonstrated. The existing process-separation utility explicitly states that it is not a sandbox, leaves networking unrestricted, and runs as the same user.

## Reconciled interpretation

The repository contains more execution-related work than the 1,000 C05 dossiers alone show. The 106 helper records, 74 control summary, 20 M0 observations, S2 classifications, and the single-case pilot are distinct populations and must not be added together as if they were 1,000 C05 executions.

The controlling C05 population remains:

| Measure | Verified repository state |
|---|---:|
| Expected INF IDs | 1,000 |
| Contractual C05 dossiers | 1,000 |
| Dossiers marked NOT_RUN | 1,000 |
| Dossiers marked INCOMPLETE | 1,000 |
| Helper records | 106 |
| Helper CRITERION_MET | 103 |
| Helper BLOCKED | 3 |
| Control-summary unique CRITERION_MET | 74 |
| Control-summary PASS | 0 |
| M0 rerun OBSERVED | 20 |
| M0 rerun UNMATCHED | 980 |
| S2 NO_CAPABILITY | 914 |
| S2 BLOCKED | 42 |

The 74 control-summary records and 106 helper records are useful work products, but their status and evidence scope remain separate from the C05 dossier population. No historical result is promoted.

## Implications for the current repair

1. Preserve the 1,000 historical C05 dossiers as NOT_RUN until new, complete per-case evidence is independently validated.
2. Preserve the six helper ledgers and control-summary records as auxiliary historical evidence; do not convert `CRITERION_MET` into PASS.
3. Treat the pilot for INF-0254 as a bounded pilot, not mass execution or a C05 closeout.
4. Keep process separation distinct from sandboxing. The new C05 isolated runner records a fresh process and temporary workspace but explicitly records `sandbox=false`; it does not claim Docker, network isolation, or privilege isolation.
5. The new validator requires persisted byte-verified artifacts, producer/oracle source artifacts, run identity, fixture/control provenance, three distinct NORMAL/NEGATIVE/BOUNDARY inputs, clean-process evidence, and no artifact or RUN_ID reuse. The new runner and tests are intended to generate and verify this format; they have not yet been executed by CI in this audit session.
6. The remaining population cannot be launched merely by iterating the 1,000 dossier IDs. An executable, source-grounded capability/input/control plan must exist for each case. Missing plans remain NOT_RUN; they must not be relabelled BLOCKED or populated with invented arguments.

## Updated verdict

`C05 = NOT_PASSED`.

The repository demonstrates bounded execution and partial control coverage, but not 1,000 complete C05 dossiers with the required per-run evidence chain. This addendum records no new case execution and makes no certification claim.
