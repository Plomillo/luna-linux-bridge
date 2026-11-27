# C05 automated gate remediation — 2026-11-26

## Governing decision

There is no human authorization, human attestation, or human reviewer approval gate in the C05 execution or validation path. The operative gate is independent automated validation, recomputed from persisted evidence. A caller-supplied report that merely says PASS is not trusted.

This applies to C05 case execution and validation. It does not claim that unrelated repository release or deployment workflows have been changed.

## Changes committed on `repair/metagente-luna-structured-20261125`

- `c05_validator.py`: the primary gate now invokes the separate `independent_validator.independently_validate_case` itself, compares the complete recomputed report with the submitted report, and rejects forged or stale PASS objects.
- `independent_validator.py`: independently reads persisted artifacts, recomputes byte hashes, validates source-file SHA-256 and Git blob identity, checks exact source line-range bytes, checks five unique run records, distinct control inputs, outcome/oracle consistency, environment isolation metadata, and the evidence digest.
- `runner.py`: validates the source file, Git blob, line range, and excerpt before starting each clean-process run.
- `evidence.py`: persists the source excerpt, environment lock, raw logs, observed output, independent oracle and producer source, metrics, and a per-run `SHA256SUMS` manifest.
- `registry.py` and new `independent_oracles.py`: move the CIDR reference oracle into a module distinct from its producer.
- `execute_c05_population.py`: orchestrates exactly three NORMAL runs and separate NEGATIVE and BOUNDARY runs for each explicitly planned INF case. Missing or invalid plans remain NOT_RUN; it refuses to overwrite existing ledgers.
- Adversarial tests now cover forged independent-validation reports, persisted evidence, source provenance, environment lock, SHA256SUMS, and control identity.
- `.github/workflows/c05-automated-validation.yml`: adds compile, Ruff, and pytest checks on the target branch and PRs to main.

## Commits in this remediation sequence

- `376348a207bf12d4ceaf848ddb62da174958f81c` — source excerpt bytes read correctly by the primary validator.
- `3eccde790c21e94b4020c6e072ba038c8d71375f` — independent validation recomputed at the primary gate.
- `05caf220af1cf971e62ccd403a97fcc081115c0f` — environment lock and SHA256SUMS persisted.
- `90e00f14de60510074a2c1df70f6b17cd5a5a04f` — environment lock and SHA256SUMS required by primary validator.
- `e2b82a0a01aa6bd61e4ec8da796006bc5b13848e` — independent verification of environment lock and SHA256SUMS.
- `1aecc68a198deea2603ad750bae7aaae8030627e` — SHA256SUMS newline serialization correction in tests.
- `393a0be672ff4a701d5bf83b03cb644b48219802` — forged independent-validation PASS adversarial test.
- `83cc9128850df7870058a65ede662ba51817525e` and `db2bf952509db7b048c81b910893d30d7896087f` — independent CIDR oracle module and registry binding.
- `22d7786717eebdd720dea9c66550bcc1541c9d95` and `9a8622fb2bed20da1b1d2d3f4f2e485a4c2e4018` — automated CI workflow and PR trigger.

## Verification state

- The normative program is present at repository root with Git blob `c259b6bca37fdfc9711ffda07b3e388e3b9774ff`.
- The 1,000 contractual INF identifiers are specified by that source.
- The 1,000 existing C05 dossiers remain historical NOT_RUN records; they were not overwritten.
- The execution orchestrator requires an explicit source-grounded plan JSONL. No complete 1,000-case plan population has been produced or verified in this remediation session.
- The new tests and workflow have been authored but have not been executed in an available shell/CI result. No test-pass claim is made.
- The current PR is draft #196: https://github.com/Plomillo/luna-linux-bridge/pull/196
- No workflow run result for the latest head commit was available through the connected GitHub run query at the time of this report.

## Verdict

`C05 = NOT_PASSED`.

The human operational gate has been removed from C05 and replaced by recomputed independent automated validation. C05 remains open until the complete 1,000-case source-grounded plan population is executed, all five runs per case are persisted, the independent validator passes every dossier, and the resulting population validator returns PASS. C08's 1,000-PASS requirement remains separate. No synthetic evidence, human attestation, or status promotion is accepted.
