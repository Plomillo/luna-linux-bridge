# C05 validator design correction — 2026-11-26

This correction supplements the forensic audit and its addendum. It records the exact execution shape required by the training program and the corresponding validator correction.

## Normative interpretation

The training program's case template states:

`aplicar negativo/borde y repetir 3 veces`

This means, per INF case:

1. Three NORMAL repetitions of the same source-derived input, from clean process/workspace state.
2. One separately executed NEGATIVE control.
3. One separately executed BOUNDARY control.

The total is five independently identified runs per case, not three runs labelled NORMAL, NEGATIVE, and BOUNDARY. The protocol's C05 record additionally requires the original case identity, scenario, objective, operation, criterion, input, fixture, environment, Luna version, machinery, expected and observed results, logs, metrics, hashes, risks, limitations, reproducible evidence, independent review, and final state.

## Implementation correction

The C05 validator and assembler were corrected to enforce:

- Exactly three NORMAL repetitions with identical inputs and stable primary outcomes.
- Exactly one separately persisted NEGATIVE run.
- Exactly one separately persisted BOUNDARY run.
- Negative and boundary inputs distinct from the normal input and from each other.
- Five unique RUN_ID values and unique artifact paths.
- Persisted byte-hashed fixture, environment, procedure, control specification, stdout, stderr, observed result, oracle, metrics, and producer/oracle source artifacts.
- Fresh-process temporary-workspace evidence, explicitly with `sandbox=false`.
- A separate automated per-case evidence review from `LUNA_C05_INDEPENDENT_VALIDATOR`; no human approval gate.

The runner preserves the legacy `EXECUTED` lifecycle status for existing callers. The C05 isolated execution path maps the observed oracle verdict separately and records `LOCAL_SUBPROCESS_TEST_ONLY`, without claiming Docker or network isolation.

## Current execution state

The correction changes validation and evidence-generation code only. It does not execute or promote historical cases. The 1,000 contractual C05 dossiers remain `NOT_RUN` until new five-run evidence and independent per-case review are generated. The 106 auxiliary helper records, 74 control-summary records, M0 reruns, and the INF-0254 pilot remain separate historical populations.

The new unit and end-to-end tests have been added to the branch, but this audit session has not executed the suite. No C05 PASS or certification is claimed.
