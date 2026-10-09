# Jonas — three-track operational completion plan

Status: IMPLEMENTATION IN PROGRESS; NOT CERTIFIED.
Authority: this branch and PR #49 only. Do not merge, deploy, or claim global certification until all gates pass.

The three remaining tracks proceed in parallel but use separate evidence and acceptance gates.

## Track A — family-confirmed balance check-ins and shared telemetry

Scope correction: do not integrate with a 1min.AI balance API. The intended workflow is to ask family members directly for the balance they can currently see and record their answers as attributable observations.

1. Provide a guided check-in for each authorized respondent: Sebastián, Diego, Catalina, and Marjorie. Ask for the displayed balance, applicable account/plan, unit, time checked and timezone, and whether the answer is self-reported or supported by optional evidence.
2. Store each answer as a separate append-only observation with respondent, account scope, observed/recorded timestamps, balance, unit, source type, evidence digest if supplied, and validation status.
3. Never assume family members share one account or credit pool. Keep balances separate by person/account unless scope, units, and permission to aggregate are all established.
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
The current branch contains initial service routes for credit observations and catalog snapshots. The required balance workflow is family-confirmed check-ins; provider balance-API integration is out of scope. Check-in prompts, consent-aware views, safe aggregation, full catalog ingestion, test execution, deployment, family package, and certification remain incomplete.
