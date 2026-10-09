# Jonas — three-track operational completion plan

Status: IMPLEMENTATION IN PROGRESS; NOT CERTIFIED.
Authority: this branch and PR #49 only. Do not merge, deploy, or claim global certification until all gates pass.

The three remaining tracks proceed in parallel but use separate evidence and acceptance gates.

## Track A — 1min.AI credit balance source and synchronization
1. Verify from official 1min.AI documentation or authenticated account access whether an endpoint returns remaining account/team credits. Record exact endpoint, auth scope, response schema, rate limits, and source URL as evidence.
2. If the endpoint is verified, implement a least-privilege scheduled poller with secret storage, bounded frequency, timeout, no retry storm, request idempotency, UTC timestamps, response schema validation, and append-only observations. Never commit credentials or raw sensitive responses.
3. If no supported endpoint is verified, keep manual authenticated observations; clearly label source_kind=manual. Do not infer remaining credits from tokens, estimates, or API request counts.
4. Mark observations FRESH/STALE/UNKNOWN. Alert or fail closed for spending authorization when stale/unknown. Distinguish observed balance, usage events, reserved amount, and projections.
5. Acceptance: fixture tests for valid/malformed/unauthorized responses, stale/unknown state, duplicates, clock/timezone handling, secret redaction, source provenance, and concurrency. Provider integration remains disabled until source verification.

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
The current branch contains initial API routes for recording and reading manual credit observations and catalog snapshots. It does not yet prove a live 1min.AI balance API, automatic synchronization, full catalog ingestion, successful test execution, deployment, family-ready packaging, or certification. The `official_api` source label supplied by a caller is not itself proof of authenticity; ingestion must validate provenance before treating data as authoritative.
