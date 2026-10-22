# Sequential startup contract — Cajita de Luna / PUAC2

**Authority:** `Louksna.md` and the persisted seven-block plan.  
**Controller:** `scripts/cajita_luna_sequential_startup.py`  
**Execution host:** local LOUKSNA PC; Desktop Commander is auxiliary only.  
**CUSTOS executor:** CUSTOSZ V9, only when its own authorization gate reports active authorization.  
**RAM policy:** 1 GiB process-tree budget; controller address-space limit 384 MiB and one sequential read-only child at up to 640 MiB.  
**Mutation policy:** fail closed; no transformation in Blocks 1–3; no changes to frozen scopes; no Edge move/delete; no evidence files written inside Cajita by the controller.

## Canonical sequence

1. **B1 — Freeze and baseline.** Read-only full-tree inventory, streamed SHA-256 of the five frozen scopes, and Edge archive digest. Report files, bytes, hashes and any scan errors.
2. **B2 — Full inventory and registry reconciliation.** Compare the legacy registry and validate required manifests without rewriting the historic registry or inventing reconciliation outcomes. D01–D22 manifests are enumerated and digest-checked as auxiliary inputs.
3. **B3 — Exact bytes and resource feasibility.** Validate the quantitative plan, hard cap of 479,000,000 decimal bytes, RAM, available storage, operation bounds, rollback reserve and evidence reserve before writes.
4. **B4 — CUSTOSZ V9 optimization routed through D01–D22.** Not dispatched by this controller. Requires B1–B3 PASS, an exact measured strategy and active CUSTOSZ authorization.
5. **B5 — Functional validation, including Edge profile/authentication state.**
6. **B6 — Checkpoint, rollback and non-regression verification.**
7. **B7 — PUAC2 independent validation G23 and distinct certification G24.**

No later block may execute after an earlier block is HOLD or FAIL. Later blocks are recorded as `NOT_STARTED_PREDECESSOR_HOLD`. There is no automatic retry loop: a failed precondition is recorded with a timestamp and exact blocker so the controller does not oscillate or repeatedly mutate state. Correcting a blocker creates a new, traceable run.

## Persistence and telemetry

The controller writes its run report, bounded child stdout/stderr, and append-only SHA-256 hash-chained `events.jsonl` to the CUSTOS continuity job directory **outside** Cajita. It does not publish Edge contents, credentials, cookies, session state or model payloads. Every run records the GitHub commit, D01–D22 manifest digests, CUSTOSZ V9 package digest and authorization result, tree-size data, protected-file hashes, RAM limits and block states.

A controller startup can report `SUCCESS_TELEMETRY_CONFIRMED` even when the mission is `HOLD`; those statuses are intentionally distinct. No controller start or unit-test pass is treated as Cajita certification.

## Actual first run

Run ID: `20261022T071427355820Z`  
GitHub `main`: `b88cc56aeb81930230babd700d426c84046ed9a8`  
Controller: `SUCCESS_TELEMETRY_CONFIRMED`; mission: `HOLD`.  
B1: `PASS`; B2: `HOLD` because `FROZEN_V9_OUTPUTS_MANIFEST_MISSING` and `REGISTRY_RECONCILIATION_MANIFEST_MISSING`; B3–B7: `NOT_STARTED_PREDECESSOR_HOLD`.  
D01–D22 manifest inventory: 22/22 JSON files present and parseable. CUSTOSZ V9 reports `active_authorized=false`, `certification=NOT_GRANTED`, and its 12-check self-test does not grant authorization. The tree measurement was 1,656,649,690 bytes; Edge archive 951,395,079 bytes. No payload writes occurred.

The full host-local run report and logs remain outside the repository in the CUSTOS continuity job directory. Only this sanitized summary is versioned.
