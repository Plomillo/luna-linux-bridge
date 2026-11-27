# C05 batch-six and contract-adjudication repair — 2026-11-27

## Scope

This append-only report records source-grounded implementation changes on `repair/metagente-luna-structured-20261125`. It does not modify the historical 1,000 C05 dossiers or claim C05 completion.

## Forensic defect: omitted batch-six candidates

The coverage matrix and executable-plan compiler previously included D01 and batches 2–5, but omitted `metagente_luna_s4/batch6.py`. That file contains seven additional source-operation candidates. Its literal interpreter had one READY stable-age candidate and six blocked candidates; a declared stack fixture was available but the interpreter incorrectly marked the stack sequence as missing.

Two cases are now executable using only the already-declared fixture material:

- `MGL5-INF-0105`: stable age sorting, preserving order among equal ages. Added a typed executor, separate insertion-sort oracle, invalid-record negative control, and empty-record boundary control.
- `MGL5-INF-0109`: push/pop/peek sequence with controlled underflow. Added a typed executor, separate stack-state-machine oracle, single-underflow negative control, and empty-sequence boundary control.

The literal interpreter now uses the predeclared stack fixture rather than reporting it missing. Both capabilities are registered with input schemas and independent oracle IDs. Batch six is included in both the plan compiler and coverage matrix.

## Corrected source census

| Measure | Previous | Current |
|---|---:|---:|
| Typed normal specifications | 99 | 101 |
| Interpreter candidates | omitted | 7 |
| Interpreter candidates READY and registered | omitted | 2 |
| Interpreter candidates still blocked | omitted | 5 |
| Unique source-plan candidate cases | undercounted | 106 |
| Complete plans with normal + negative + boundary | 15 | 17 |
| Typed normal specs missing one or both controls | 84 | 84 |
| Cases without typed normal spec or interpreter candidate | undercounted | 894 |
| INF cases not in executable plan set | 985 | 983 |

The 17 plans are not a C05 population closeout. The remaining 983 cases are explicitly NOT_RUN until their own source-grounded operation, fixture, capability, negative control, boundary control, and five-run evidence exist.

## Contract adjudication repair

The execution path previously assembled case records with the default `contract_status=NOT_A_PASS` and did not perform a complete positive adjudication. The runner now records a contract evaluation and permits contractual PASS only if:

1. All three identical NORMAL repetitions have execution PASS, lifecycle EXECUTED, and successful oracle results.
2. The authored NEGATIVE expectation is satisfied.
3. The authored BOUNDARY expectation is satisfied.
4. The per-case independent evidence validator returns PASS.

The primary adjudicator uses the registered control contract. The independent validator has a separate fail-closed expectation implementation for the current executable control set. Unknown expectation identifiers are rejected. The population validator refuses a contractual PASS unless the explicit three-normal/two-control evaluation is present and complete.

A fail-open predicate in the `empty-roundtrip` control was corrected: an empty output no longer passes when the lifecycle is BLOCKED or INCONCLUSIVE.

## Execution-path correction

The previous implementation launched five Docker containers for every case without a complete plan. That produced no underlying operation result and consumed execution time to rediscover a known planning gap. The population runner now:

- Executes only complete authored plans (currently 17).
- Writes the other 983 cases as NOT_RUN in a separate source-bound blocker inventory.
- Retains exact source excerpt, line range, source-file hash, excerpt hash, and blocker reasons.
- Refuses to overwrite any existing ledger, report, or blocker inventory before execution.
- Keeps evidence-inventory completion separate from C05 functional certification.

The hosted workflow checks exact ID equality among the ledger's NOT_RUN rows, rejected validator rows, and source-bound blocker inventory. It continues to require `c05_status=NOT_PASSED` while 983 cases remain unexecuted.

## Regression coverage added

- Batch-six stable sorting and stack operation tests.
- Batch-six source interpreter readiness tests.
- Negative and boundary control acceptance tests.
- Independent control adjudication tests, including rejection of unknown expectations.
- Contract adjudication tests requiring all three normal repetitions and both controls.
- Validator test rejecting contractual PASS without explicit adjudication.
- Population inventory tests for exact 17/983 accounting, duplicate blocker IDs, and fail-closed output collisions.
- Coverage-matrix assertions for all seven interpreter candidates and the corrected counts.

## Hosted validation state

Latest candidate commit at report creation: `97217e6404b0f0cd8e5cdb91e279fddb0f846719`.

- Restricted-Docker workflow run #232 (`45945750202`): QUEUED.
- Independent validation workflow run #278 (`45945750206`): PENDING.
- Earlier run #135 (`45942770269`) remains on the prior implementation and was still executing the old five-container-per-case loop at last inspection.

The latest code has not yet received a completed CI result in this report. No test pass is claimed from queued workflows.

## Decision

`C05 = NOT_PASSED`.

The compiler and validator now account for 17 executable plans and 983 source-bound NOT_RUN cases. C05 requires 1,000 cases with three clean NORMAL repetitions, separate NEGATIVE and BOUNDARY runs, complete persisted evidence, independent per-case validation, and contractual PASS. The remaining 983 operations have not been fabricated or promoted.
