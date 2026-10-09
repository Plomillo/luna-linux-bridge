# Jonas — three-track operational completion plan

Status: IMPLEMENTATION IN PROGRESS; NOT CERTIFIED.
Authority: this branch and PR #49 only. Do not merge, deploy, or claim global certification until all gates pass.

The three remaining tracks proceed in parallel but use separate evidence and acceptance gates.

## Track A — family-confirmed balance check-ins and shared telemetry

Scope correction: do not integrate with a 1min.AI balance API. The intended workflow is to ask family members directly for the balance they can currently see and record their answers as attributable observations.

1. Provide a guided check-in for each authorized respondent: Sebastián, Diego, Catalina, Marjorie, and Cristóbal. Ask for the displayed balance, applicable account/plan, unit, time checked and timezone, and whether the answer is self-reported or supported by optional evidence.
2. Store each answer as a separate append-only observation with respondent, account scope, observed/recorded timestamps, balance, unit, source type, evidence digest if supplied, and validation status.
3. Treat this as exactly one shared family credit pool (`family-shared`, unit `credits`) for Sebastián, Diego, Catalina, Marjorie, and Cristóbal. Each answer is a separate confirmation of the same pool; never sum reports. Record who confirmed and when. Compare each respondent's latest report, preserve all prior observations, and mark the pool CONFLICTING with no confirmed balance when current reports disagree. Do not silently select a value; ask participants to reconfirm until the current reports agree.
4. Show FRESH/STALE/UNKNOWN using a documented freshness window. Reminders may request a new check-in, but the system must not claim to know a new balance before the person confirms it.
5. Resolve conflicting or ambiguous answers by asking the relevant respondent to confirm. Never infer credits from tokens or poll a provider billing API.
6. Acceptance tests: attribution, duplicate submissions, stale/missing/conflicting observations, timezone normalization, consent/privacy, safe aggregation, audit history, and access control.


## Track B — complete model catalog and recommendations
1. Use the documented official model-list endpoint if verified; capture response schema and pagination/completeness semantics.
2. Import the catalog as a timestamped, hashed snapshot. Track model ID, documented metadata/capabilities, source URL, retrieval time, and catalog freshness. Never label a partial result as the complete catalog.
3. Separate provider-reported metadata from benchmark results and local inference. Recommend per task based on documented capability, quality constraints, latency, estimated credit cost only when evidenced, and uncertainty.
4. Do not estimate 1min.AI credits from token counts unless a documented pricing/conversion rule exists for that exact model and plan. Unknown costs remain UNKNOWN and cannot be presented as verified savings.
5. Acceptance: tests for pagination/partial catalogs, duplicate IDs, stale snapshots, unavailable fields, unpriced models, task constraints, ranking determinism, and safe fallback.

## Track C — safe family-facing package and shared service
1. Produce a reproducible source package with setup guide, configuration example containing placeholders only, data-flow/privacy explanation, health checks, backup/restore instructions, and uninstall/rollback steps.
2. Separate personal API keys from the package. Each family member must use their own credential or a deliberately configured shared account with explicit permission; never bundle a live secret in a ZIP, GitHub artifact, source file, or QR code.
3. If users need a common balance view, deploy one authenticated shared service/database with per-user authorization, TLS, rate limits, audit events, retention policy, backups, and recovery tests. A repository alone does not provide live shared state.
4. Default to read-only credit visibility and recommendations. Budget reservations or provider calls remain disabled unless configured and explicitly authorized. Do not expose prompts or personal content in shared telemetry by default.
5. Acceptance: clean-environment install test, secret scan, permission tests, unauthorized-user denial, backup/restore, reproducible build hash, documented support boundaries, and family usability review.

## Cross-track governance gates
- Every event carries event/request ID, actor or service identity, UTC timestamp, source and version, validation outcome, and integrity digest.
- Append-only event history; no silent replacement, reclassification, or certification propagation.
- Independent review and non-regression tests required before certification.
- Any failed/missing evidence => FAIL CLOSED for the affected capability.
- Keep work on this feature branch and PR #49. Do not modify canonical Louksna artifacts or merge this PR as a side effect of implementation.

## Current known state
The branch contains routes for credit observations and catalog snapshots. The shared-pool rule is one family balance, never a sum of reports; only manual family confirmations are in scope, and provider balance-API integration is prohibited. Test execution and review remain required. Deployment, family package, and certification remain incomplete.

## Execution update — 2026-10-09 (append-only; not certified)

### Materialized and tested
- Track A: added the guided manual form at `/family-check-in`; submissions are bound to one of five distinct respondent credentials (Sebastián, Diego, Catalina, Marjorie, Cristóbal). A respondent cannot submit under another person's identity. Incomplete token configuration fails closed.
- Track A: preserved the single `family-shared` pool; reports are never summed. Fresh conflicting reports produce `CONFLICTING` with no balance. Stale reports are surfaced separately. `confirmed_balance_credits` remains null until all five respondents have fresh matching reports.
- Track B: added deterministic `GET /v1/models/recommendations`. Capability constraints are explicit; quality/latency/cost constraints exclude candidates when the corresponding metric or a valid evidence digest is absent. Unknown credit cost remains null. Recommendations remain unverified and uncertified.
- Cross-track: hardened immutable/idempotent replay checks, rejected duplicate catalog model IDs, and added a hash-bound CI evidence artifact.
- CI run [37975433850](https://github.com/Plomillo/luna-linux-bridge/actions/runs/37975433850) completed with **20 passed, 0 failed** for the API/shared-account test suite; compile passed. CI report digest: `82a8d5f454ea7d3775756eec720c90d51496197f592246f33b5bb7691b7a4c12`. Artifact digest: `sha256:bb76cfdda07c9c17ee7d832baa9dac14c6e369ba2a50dce5da6c2e41293ce8a6`.

### Explicit remaining blockers
- No direct messages have been sent to family members; each person must open the check-in page on the configured shared service and submit their own observation.
- The API is not deployed as a family-accessible shared service. Production TLS, rate limits, deployment secret management, access-control review, backup/restore and recovery testing remain unproven.
- No verified complete official model-list endpoint or pagination/completeness contract has been implemented. A saved snapshot or `source_kind=official_api` label does not prove provider authenticity or catalog completeness.
- A reproducible, installable family distribution and clean-environment install/uninstall/rollback evidence remain incomplete.
- The local Jonas budget MVP is separate from the shared-account API; no provider billing reconciliation or actual savings measurement is established.
- This CI pass is implementation-level evidence only. G23 independent validation, G24 certification, production authorization and merge remain **NOT EXECUTED / NOT AUTHORIZED**.

## Package and reproducibility evidence — 2026-10-09

- CI run [37975961011](https://github.com/Plomillo/luna-linux-bridge/actions/runs/37975961011) completed successfully for the current family API candidate.
- API/shared-account suite: **20 passed, 0 failed**. The same 20 tests passed again after extracting the generated archive into a fresh directory and installing its declared dependencies in a new virtual environment.
- Deterministic source-candidate archive SHA-256: `7dd62823a8fc68214be3340b07cd81bc83e283e7a5acad7c845709665663bf28`.
- CI evidence report SHA-256: `40d7a97edb6b7e91a3ab20e5a896aeceed92b098e61f790b0dc3a7a9c8d2b86a`.
- Uploaded evidence artifact SHA-256: `sha256:8016e9e549855e6f314bb5d1134cf685a6ca7a86d27bfb7408a91fa1b521af8e`.
- Package status remains `SOURCE_CANDIDATE_NOT_PRODUCTION_DEPLOYABLE`; this evidence does not close deployment, TLS, family outreach, provider catalog, backup/restore, or G23/G24 gates.

## Backup/restore and package regression evidence — 2026-10-09

- CI run [37976334899](https://github.com/Plomillo/luna-linux-bridge/actions/runs/37976334899): compile passed; **23 API/shared-account/backup tests passed**; source archive extracted into a clean directory, dependencies installed in a fresh virtual environment, and the same **23 tests passed again**.
- Deterministic family source-candidate archive SHA-256: `819e43b14fd5fd56ac6caffe5c5594ce827dbf130ec0bf9fad0d4072355a74df`.
- CI evidence report SHA-256: `86feb5ec403d78599ced8d047a59c7f7937394b722b1814fc569e19340763006`.
- Uploaded artifact SHA-256: `sha256:b3de822d81e0d70db4a974968fead5ca8b793ef66cf5ace565abe3f675f9d34e`.
- The packager scans for common secret patterns, includes source/test/deployment/recovery documentation, and labels the archive `SOURCE_CANDIDATE_NOT_PRODUCTION_DEPLOYABLE`.
- Backup/restore tests verify SQLite integrity, SHA-256 matching, pre-restore checkpoint preservation, and explicit fail-closed restore authorization. These are automated local tests, not a production recovery drill.

