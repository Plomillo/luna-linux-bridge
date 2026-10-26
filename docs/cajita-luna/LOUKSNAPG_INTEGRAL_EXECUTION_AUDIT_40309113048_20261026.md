# LOUKSNAPG integral execution audit — 2026-10-26

**Decision: `HOLD_NOT_CERTIFIED`.** This is an evidence-bound report for candidate source commit `5fab498b6faae08f59962861503b1a1202fcc83c`. The audit report itself is committed separately and does not rewrite or reclassify that execution.

## Exact runs

- Factory: [40309113060](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113060)
- Secondary audit: [40309113048](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113048)
- Pull request: [#157](https://github.com/Plomillo/luna-linux-bridge/pull/157)

## Candidate integrity

The single-file `LOUKSNAPG.md` candidate measured **371,947,713 bytes**, SHA-256 `3337c635d77d509e061768d573330345ff6673bafa8de828ad8b0bd3b1d52f7c`. It is under the 479,000,000-byte distribution ceiling. Independent package-integrity G23 succeeded for its exact source commit and candidate hash. That result covers container/package identity, hashes and registered smoke scope—not semantic model quality or integral certification.

G24 ran with a one-CPU quota and a 1 GiB memory cgroup. Container smoke returned 0; measured peak memory was 979,845,120 bytes. Six source-bound runtime-engine smoke checks passed within their limited scope. However, the five model-backed known-answer tasks all failed semantic quality: Cerebro text generation, Whisper transcription, Seamless translation, Docling invoice extraction and Qwen arithmetic. Execution-level passes are not quality passes: the evidence records 5 executions, 0 quality passes, 5 quality failures; task harness exit code 3 and integral functional gate exit code 2. G24 decision: `NOT_GRANTED`.

## Six obligations

| Obligation | Observed status | Evidence-based reason |
|---|---|---|
| C1 — Coordinated workers | `HOLD` | CUSTOSZ V9 produced a bounded packaging receipt. Kestra was `NOT_CONFIGURED`; there is no execution ID or terminal state. |
| C2 — Official source repair | `HOLD` | Source/model revision metadata is pinned, but 0 material model-repair records were verified and 5 quality checks failed. |
| C3 — Primitive functions | `HOLD` | Only 5 of 21 registered targets were exercised; 0/5 model quality checks passed. |
| C4 — Telemetry and audit | `PASS_TRACEABILITY_WITH_RELEASE_HOLD` | Twelve hash-bound events, including `KESTRA_AUDIT_RESULT`, are sequence- and subject-bound. The event faithfully binds a `NOT_CONFIGURED` receipt; this does not prove Kestra ran. |
| C5 — Governed release chain | `HOLD` | Functional G23 is not established, Kestra did not execute, G24 is not granted, and host/non-regression/rollback evidence is incomplete. |
| C6 — Prohibitions and recovery | `PASS_PROHIBITIONS_OBSERVED` | No heavy model weights downloaded, no Remote Commander used, no canonical mutation, and no synthetic diagnostics treated as product proof. |

**Summary:** 2 obligations passed, 4 held; `release_eligible=false`; `global_certification=NOT_GRANTED`.

## C4 final telemetry

The audit preserved the 11-event preaudit snapshot as the dispatch input and generated a separate 12-event final telemetry file after the Kestra attempt.

- Pre-dispatch events: 11.
- Final events: 12; last event `KESTRA_AUDIT_RESULT`.
- Kestra receipt status: `NOT_CONFIGURED`.
- Execution ID present: false; terminal state: null.
- Receipt file SHA-256: `f917cd0bd146050f189e4e3ec5b40f765c3dece94b5199579138b3fc2179b06c`.
- Final telemetry physical file SHA-256: `f3cd8927fba91fb45de10ff4cfca89b7fe2f79a0eb74c9f68f8acd607f289906`.
- Final telemetry remains `INCOMPLETE_HOLD`; product certification remains `NOT_GRANTED`.

The C4 fix is now in the branch: it cannot claim a complete trace merely because 11 pre-dispatch events exist. The final post-dispatch receipt is an explicit, hash-bound 12th event, validated against the actual receipt file.

## Artifacts

- [Product candidate artifact](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113048/artifacts/12643823593)
- [G23 package-integrity evidence](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113060/artifacts/12644645898)
- [G24 decision and task evidence](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113060/artifacts/12644791261)
- [G24 runtime telemetry](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113060/artifacts/12643663783)
- [Auxiliary evidence including final C4 telemetry and the six-obligation report](https://github.com/Plomillo/luna-linux-bridge/actions/runs/40309113048/artifacts/12644851027)

## Remaining blockers

1. Configure GitHub Actions variable `KESTRA_URL` and secret `KESTRA_API_TOKEN`, then verify an actual Kestra execution ID and terminal state. The current run did not dispatch.
2. Repair the five model candidates materially and bind before/after weight hashes to the exact candidate and official model revisions. The current run did not download heavy original weights, and all five semantic checks failed.
3. Produce non-synthetic, task-specific execution evidence for all 21 registered targets.
4. Obtain independent, verified functional G23 and a separate authorized G24 signature; then complete host matrix, non-regression and runtime rollback verification.

This report records what happened; it is not a certification claim. The main branch was not modified or merged.
