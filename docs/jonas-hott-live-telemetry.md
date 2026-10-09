# Jonas — HoTT/Univalence + live telemetry: operational savings layer

Status: **proposal / unverified implementation**. This extension is additive to `Jonas.yml`; it does not change the original policy, authorize model calls, or claim formal HoTT verification.

## 1. Goal

Operationalize cost savings with a typed, evidence-carrying control plane. Higher-order dependent-type ideas structure contracts and proof obligations; HoTT/univalence inspires a strict equivalence gate; live telemetry measures actual resource use and supports rollback. These are engineering controls inspired by the mathematics, not a claim that ordinary Python implements a proof assistant or that a hash constitutes a proof.

## 2. Invariants

- **Fail closed:** missing budget, price bound, token/cost bound, API token, accounting database, or evidence hash means no reservation and no provider call.
- **Protected reserve:** automation may spend only `period_limit - protected_reserve`; reserve values must be explicitly configured in integer micro-USD. Never infer a limit from `null`.
- **Atomicity and idempotency:** reservation runs in a SQLite `BEGIN IMMEDIATE` transaction; a repeated request ID returns the existing reservation only if its request parameters match exactly. Conflicts are rejected.
- **No implicit retries or provider calls:** this API only authorizes/records budgets and telemetry. It does not call a model provider. A caller must check a successful reservation before making any external request and reconcile afterward.
- **Cost correctness:** use integer micro-USD; no floating-point arithmetic for money. Include model, controller, evaluation, correction, tool, infrastructure, and retry costs when applicable.
- **Evidence and provenance:** each decision emits a UTC event with policy version, request ID, bounded estimate, decision, and evidence digest. Never log prompts, credentials, or chain-of-thought.
- **Kill switch:** a detected overrun or accounting failure halts new reservations until an operator explicitly clears the halt after reconciliation.
- **No silent promotion:** optimization remains observational until quality and cost evaluation gates pass; deployment/promotion requires human approval.

## 3. Type-theoretic interpretation (operational, not a proof claim)

Model every consequential action as a typed record with explicit input, preconditions, output, evidence, and failure states. A reservation is valid only with a witness for each required precondition: authorized budget, finite upper cost bound, known pricing source, sufficient spendable balance, and durable accounting. Missing witnesses produce a rejection value, never a permissive default.

A model/configuration substitution is **not** accepted because names or output schemas match. Treat it as equivalent only when a versioned equivalence dossier supplies: (1) identical mandatory capability contract, (2) reproducible evaluation evidence, (3) predefined non-inferiority thresholds, (4) no critical-test regression, (5) net savings of at least 10% after controller/evaluation/correction costs, and (6) a signed human approval. This is an engineering analogue of proof-relevant equivalence, not a formal derivation of univalence.

## 4. Savings calculation

For a fixed evaluation cohort:

`C_valid = (C_model + C_controller + C_evaluation + C_corrections + C_tools + C_infrastructure) / N_valid`

`S_net = (C_reference - C_candidate) / C_reference × 100`

Require `N_valid > 0`, a positive reference cost, comparable cohorts, and evidence for every included cost. Accept a candidate only if `S_net >= 10%`, mandatory quality/security tests pass, and all predefined non-inferiority bounds pass. If evidence is incomplete, report **INCONCLUSIVE**, not savings.

## 5. Live telemetry and API contract

The reference API exposes:
- `GET /health`: process health only; not certification.
- `POST /v1/reservations`: reserve a caller-supplied upper-bound cost atomically.
- `POST /v1/reservations/{request_id}/settle`: reconcile actual cost against reservation.
- `GET /v1/telemetry`: aggregate reservations, settled spend, rejected requests, and halt state; no prompt content.
- `POST /v1/halt` and `POST /v1/resume`: authenticated operator controls. Resume must be used only after external reconciliation.

All non-health routes require a bearer token from `JONAS_API_TOKEN`. Budget settings are explicit environment variables: `JONAS_PERIOD_LIMIT_MICRO_USD` and `JONAS_PROTECTED_RESERVE_MICRO_USD`. If unset or invalid, new reservations are denied. Do not expose this service publicly without TLS, network restrictions, secret management, and deployment-specific authentication review.

## 6. Family-confirmed shared balance observations and model catalog (implementation started)

The branch adds authenticated endpoints for append-only balance observations and versioned model-catalog snapshots. The intended balance workflow is to ask each authorized family member directly for the balance they can currently see. Integration with a 1min.AI account/billing balance API is out of scope and must not be implemented.

A complete check-in must record respondent, account scope, balance and unit, observed time and timezone, recorded time, source type (self-reported or supported by supplied evidence), validation status, and evidence digest when applicable. Keep each person's/account's balance separate unless account scope, units, and permission to aggregate are established. A freshness window can mark observations FRESH/STALE/UNKNOWN; reminders may ask people to reconfirm but cannot generate a newer balance without their response. Do not infer credits from tokens.

This is shared state only for clients that reach the same service/database or an explicitly configured synchronization layer. GitHub preserves code and review history; it is not itself a live shared database. A saved catalog snapshot is not proof that the full current catalog has been fetched. These additions remain unverified and uncertified.


## 7. HoTT / univalence and observability boundaries

- Types/contracts describe admissible actions; runtime validation checks concrete values.
- Evidence digests establish content identity only, not authorship, correctness, or equivalence.
- Univalence is a mathematical principle, not implemented merely by comparing JSON schemas or hashes.
- Telemetry is “live” only for events observed by this process. Provider-side billing, out-of-band credentials, and calls bypassing the gateway remain outside its visibility and must be isolated or separately reconciled.
- The service starts in a non-authorizing state until configuration is explicit. This branch is not production-certified.

## 8. Validation gate before production

1. Configure nonzero/explicit spend limit and protected reserve through an authorized operator.
2. Verify current provider prices and billing semantics from official sources; record URL, retrieval time, version/hash, and reviewer.
3. Test concurrent reservations, duplicate IDs, restart persistence, unavailable database, invalid token, insufficient balance, settlement overrun, halt/resume, and protected-reserve preservation.
4. Run a reproducible reference-vs-candidate evaluation on a separated validation set.
5. Demonstrate at least 10% net savings with no critical regression.
6. Independent review, release manifest/hash, access-control review, rollback drill, and explicit approval.
7. Until all gates pass: keep automatic provider calls disabled.

## 9. Provenance

This document is an additive design record for `Plomillo/luna-linux-bridge`. It does not modify `Jonas.yml` or any canonical Louksna artifact. The source of truth for the implementation is the version-controlled branch and its review history; a pull request must be reviewed before merging.
