# C05 source-bound planning backlog execution — 2026-11-27

## Actual automated run

- Workflow: C05 automated independent validation
- Run: #40
- Run ID: `45933817083`
- Candidate commit: `3a68162d18e5bb5d5a783454b5c251f0e6c48654`
- Result: **SUCCESS**
- Job `unit-and-adversarial`: SUCCESS
- compileall: SUCCESS
- source backlog generation: SUCCESS
- artifact upload: SUCCESS
- Ruff: SUCCESS
- pytest: SUCCESS (60 tests)
- workflow summary correctly states this does not execute the 1,000 INF population or certify C05.

## Artifact

- Artifact ID: `15169462863`
- Name: `c05-source-plan-backlog-fe5b785d913eab87036dae109a351d790d2484fe`
- SHA-256: `898549a423db2ed2d0a354a4f36af7a768c3019541c9c4b5116817ddb3a822c2`
- Size: 176,563 bytes
- Expiration: 2027-02-25
- Artifact: https://github.com/Plomillo/luna-linux-bridge/actions/runs/45933817083

## Source census emitted by the job

- Training source SHA-256: `f67c32d8984be78e73ba1acac050349baef9c1fb6adeb59fef15e53821b88daf`
- Source Git blob: `c259b6bca37fdfc9711ffda07b3e388e3b9774ff`
- INF IDs: 1,000; unique: 1,000; canonical order: validated.
- Domain distribution: D01–D20, 50 each (all 20 domains validated).
- Authored executable plans: 0.
- NOT_RUN: 1,000.
- Output status: `SOURCE_BOUND_BACKLOG_ONLY_NOT_EXECUTION`.
- Normal, negative, boundary plan fields intentionally null; no capability, argument, control, result or PASS was invented.
- Each backlog record includes exact source excerpt, line bounds, source-file SHA, Git blob, excerpt SHA, title, operation, fixture instruction, criterion, oracle requirement, seed, and explicit plan/execution state.

## Workflow defect and correction

First run #37 (`45933730635`) generated the backlog successfully but artifact upload failed because the workflow referenced the wrong working-directory path. The report-generation code and workflow artifact path were corrected. Run #40 proves the corrected artifact path and upload step succeeded.

## C05 decision

C05 remains **NOT_PASSED**. This run establishes complete source-bound plan backlog materialization and CI validation only. It does not satisfy individual execution, fixture completion, 3 clean normal repetitions, separate negative/boundary runs, independent case validation, or 1,000 authentic dossiers. The historical dossier and auxiliary ledgers remain unchanged.

## Execution boundary clarification (user instruction)

All mission work, source inspection, code changes, plans, execution, evidence and certification must occur through Git/GitHub and hosted Git workflows. **No user's PC, Desktop Commander, remote desktop, local filesystem or local shell may be accessed for this mission.** Hosted Git Actions runners are the execution environment. Any previous attempt to use a PC-connector was outside scope and is explicitly discontinued.

## Registry census

The registered S3 capability registry currently exposes 67 capability IDs. Registry membership alone does not provide a valid mapping for each INF case, nor source-authored inputs and independently defined controls. A planner must produce a reviewed mapping and reject unsupported cases rather than assign a capability by broad domain or invent inputs.


## Hosted restricted-Docker partial population — 2026-11-27

- Workflow run #76: `45939496888`
- Candidate commit: `bdf25b2d50207ee394468b0603abf3c9a065b4ec`
- Docker job execution step: SUCCESS.
- Source-bound backlog: 1,000 INF records; D01–D20, 50 each.
- Executable-plan compiler: 15 plans emitted from existing normal specifications plus authored NEGATIVE and BOUNDARY controls; 84 other normal specifications skipped because one or both controls were not authored; remaining INF cases have no complete plan.
- Compiled case IDs: `0001, 0002, 0003, 0004, 0005, 0007, 0008, 0009, 0010, 0011, 0012, 0030, 0101, 0102, 0251`.
- Docker population: 75 runs (15 cases × 3 NORMAL + 1 NEGATIVE + 1 BOUNDARY), with the pinned worker image `sha256:5a5d9a113125f04406a5077af89e1fe62791fee66d117b37cf287ad134e93782`.
- Population validator report: 15 authentic results; 985 NOT_RUN; 985 rejected as not executed; 0 contractual PASS; C05 `NOT_PASSED`.
- Artifact ID: `15171603055`; SHA-256: `6d09ea0f59c16a91a6326e39ec38c6814efa19367064548811a1b7dd4f41815a`.
- Artifact URL: https://github.com/Plomillo/luna-linux-bridge/actions/runs/45939496888

The Docker execution and independent per-case evidence checks completed. The final workflow assertion failed because it incorrectly expected the validator's `rejected` list to be empty; the validator correctly listed the 985 unexecuted cases as rejected. This was a workflow assertion defect, not an execution failure. The assertion was corrected to require that the rejected IDs equal exactly the 985 cases absent from the compiled plan set, while requiring all 15 planned cases to be authentic.

The same candidate's automated validation workflow run #122 (`45939496896`) succeeded: compileall, source backlog, TEO dossier compiler, Ruff, and 70 unit/adversarial tests passed. The next hosted run must verify the corrected population assertion and archive the partial batch.

This result is not C05 certification: 985 INF cases remain NOT_RUN; the 15 authentic dossiers have `contract_status=NOT_A_PASS`; the global contract PASS count remains zero. The Docker container continues to share the host kernel (`SHARED_HOST_KERNEL_NOT_VM`).


## Corrected hosted run — 2026-11-27

- Workflow run #81: `45939713093` — SUCCESS.
- Automated validation run #127: `45939713116` — SUCCESS; 71 unit/adversarial tests passed; Ruff and compileall passed.
- Candidate commit: `22c1053bd9a1230eeec534d753a95225f5ffb89d`.
- Docker population step: SUCCESS; the verification step now asserts that the rejected set is exactly the 985 IDs not present in the compiled plan set.
- Results: 15 authentic, independently validated dossiers; 75 restricted-Docker executions; 985 NOT_RUN; 985 rejected specifically as `case-not-executed`; 0 contractual PASS; C05 remains `NOT_PASSED`.
- Pinned Docker image ID: `sha256:4a41649dd0466a9414dbee6bade31b6e335138c419cd75a193a900cb3475f12f`.
- Artifact ID: `15172540071`; SHA-256: `06b71fa107fef0346d0108840dfc088cd9fb5a224a406c1d76a976cbee38ab85`.
- Artifact URL: https://github.com/Plomillo/luna-linux-bridge/actions/runs/45939713093

This run verifies the full path from source-bound plan compilation through the pinned Docker executor, persisted artifacts, negative/boundary semantic checks, primary validation, and independent validation for the 15 compiled cases. It does not certify the 985 cases without plans or the global C05 gate.
