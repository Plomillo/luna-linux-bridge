# Jonas HoTT-inspired budget and telemetry API

This is an isolated, additive reference service. It reserves budget and records telemetry; it **does not call an LLM/provider** and does not prove provider-side billing.

## Local development

Use Python 3.11+.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r jonas_hott_api/requirements.txt
export JONAS_API_TOKEN='replace-with-a-long-random-secret'
export JONAS_PERIOD_LIMIT_MICRO_USD='1000000'
export JONAS_PROTECTED_RESERVE_MICRO_USD='200000'
export JONAS_DB_PATH='./state/jonas-telemetry.sqlite3'
# Set five distinct tokens via a local secret manager; never commit actual values.
export JONAS_FAMILY_RESPONDENT_TOKENS_JSON='{"Sebastián":"<secret-1>","Diego":"<secret-2>","Catalina":"<secret-3>","Marjorie":"<secret-4>","Cristóbal":"<secret-5>"}'
uvicorn jonas_hott_api.app:app --host 127.0.0.1 --port 8787
```

Amounts are integer micro-USD. The example numbers above are for local tests only, not recommended family-budget settings. Never deploy with example budgets or a sample token. If either budget variable is missing or invalid, reservation requests fail closed.

Run tests from the repository root:

```bash
pytest -q tests/test_jonas_hott_api.py tests/test_jonas_account_state.py
```

## Family respondent identity and secret handling

Balance submissions require a separate bearer token for each authorized respondent. The server binds the authenticated token to the submitted actor and rejects attempts to submit for another family member. Configure all five entries in `JONAS_FAMILY_RESPONDENT_TOKENS_JSON` through a local secret manager or deployment environment; never commit actual token values. If the mapping is absent, malformed, incomplete, or ambiguous, writes fail closed. The generic API token remains for other authenticated API routes and does not establish a respondent's identity.

The values above are placeholders only. Do not deploy the example budget values or any sample credential.

Install, health-check, backup, restore, and rollback instructions: [Jonas family deployment guide](../docs/jonas-family-deployment.md). The SQLite backup/restore helper is `scripts/missions/backup_restore_jonas_state.py`; restore requires both explicit authorization and confirmation that the service is stopped.

## Family-confirmed shared balance observations (initial implementation)

The service stores a shared, append-only history of balance observations and model-catalog snapshots in the configured SQLite database. The balance workflow is to ask each authorized family member directly for the balance they can currently see; there is no integration with a 1min.AI balance API.

- `POST /v1/account/credits/observations` records an authenticated observation. Current schema supports source type, timestamp, actor, source reference, balance, and evidence digest.
- `GET /family-check-in` serves the guided Spanish form for manual check-ins, including respondent identity, displayed balance, account/plan, local observation time/timezone, consent, and optional external-evidence digest.
- Writes require a distinct private token for each of Sebastián, Diego, Catalina, Marjorie, and Cristóbal. A submitted actor must match the token identity; missing/incomplete token configuration denies writes.
- The pool is `CONFIRMED_BY_ALL_FIVE` only when all five have fresh matching reports. Until then, the latest matching value may be shown as `OBSERVED`, while `confirmed_balance_credits` remains null. Conflicting fresh reports return no balance; stale reports are disclosed separately and do not create a current conflict.
- If no external evidence is attached, the form records a SHA-256 digest of the self-report payload and labels it as such; that digest is not proof that the provider-side balance is true.
- `GET /v1/account/credits` returns the latest observation plus age and `FRESH`/`STALE`; no observation means `UNKNOWN`.
- `GET /v1/account/credits/history` returns observation history.
- `POST /v1/models/catalog/snapshots` stores a versioned catalog snapshot.
- `GET /v1/models/catalog` returns the latest saved snapshot and freshness metadata.
- `GET /v1/models/recommendations?task=chat&required_capabilities=chat` returns a deterministic shortlist from the saved snapshot.
- Optional recommendation constraints: `min_quality_score`, `max_latency_ms`, and `max_estimated_cost_credits`. When a constraint is requested, a metric without a valid attached evidence digest fails closed and excludes that candidate.
- Cost, latency, and quality remain `UNKNOWN` unless the catalog entry carries the corresponding metric and `<metric>_evidence_sha256`. A digest being present is not independent validation.
- Recommendations return `catalog_source_verified=false` and `certified=false`; this branch does not yet fetch or verify a complete official model catalog endpoint. A saved snapshot is not proof of catalog completeness.

The family uses one shared pool (`family-shared`, unit `credits`) for Sebastián, Diego, Catalina, Marjorie, and Cristóbal. Every participant's response is a separate observation of the same balance; never sum responses. The API compares the latest report per respondent. If current reports disagree, it returns `CONFLICTING` with no confirmed balance and preserves history until participants reconfirm. Each observation records consent, respondent, observation and recording timestamps, and evidence digest. A manual record is not proof of provider-side truth. The service only shares state among clients connected to the same service/database; separate installations need an explicitly configured shared service or controlled synchronization.


## Safety boundary

- Bind to loopback for local development; do not expose publicly without TLS, network restrictions, secret management, and an authentication review.
- Configure real limits and reserve only through an authorized operator after reviewing the original Jonas policy.
- Reserve a defensible upper bound before any external provider call. Settle using provider usage/billing evidence afterward.
- The API cannot prevent calls made outside the gateway. Isolate credentials so application callers cannot bypass it.
- A settlement above its reservation records the overrun and halts new reservations. Resume is an operator action and this API cannot independently prove reconciliation.
- Hashes are integrity aids, not proof of authorship, truth, formal equivalence, or certification.
- Automatic provider calls remain disabled until official pricing/billing semantics, concurrency/restart behavior, security, savings, quality non-regression, independent review, and rollback are validated.

See [the design and validation gates](../docs/jonas-hott-live-telemetry.md).
