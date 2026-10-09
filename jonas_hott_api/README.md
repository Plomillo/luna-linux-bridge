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
uvicorn jonas_hott_api.app:app --host 127.0.0.1 --port 8787
```

Amounts are integer micro-USD. The example numbers above are for local tests only, not recommended family-budget settings. Never deploy with example budgets or a sample token. If either budget variable is missing or invalid, reservation requests fail closed.

Run tests from the repository root:

```bash
pytest -q tests/test_jonas_hott_api.py tests/test_jonas_account_state.py
```

## Shared 1min.AI account state (initial implementation)

The additive routes store a shared, append-only history of observed credits and model-catalog snapshots in the configured SQLite database:

- `POST /v1/account/credits/observations` records an authenticated observation with UTC timestamp, source type (`manual` or `official_api`), actor, source reference, and evidence digest.
- `GET /v1/account/credits` returns the latest observation plus its age and `FRESH`/`STALE` status. No observation means `UNKNOWN`.
- `GET /v1/account/credits/history` returns the observation history.
- `POST /v1/models/catalog/snapshots` stores a versioned catalog snapshot with provenance.
- `GET /v1/models/catalog` returns the latest saved catalog snapshot and freshness metadata.

Set `JONAS_ACCOUNT_STATE_TTL_SECONDS` to the approved freshness window (default: 3600 seconds). A manual observation is explicitly labeled manual; the service does not infer credits from token usage. **Automatic account-balance synchronization is not implemented** because an official, authenticated 1min.AI balance endpoint has not yet been verified. Likewise, saving a catalog snapshot is not the same as automatically fetching the complete live catalog. These endpoints share observations among clients connected to the same service/database; separate installations do not magically share state unless deployed against an authorized shared service or synchronized through a controlled channel.

## Safety boundary

- Bind to loopback for local development; do not expose publicly without TLS, network restrictions, secret management, and an authentication review.
- Configure real limits and reserve only through an authorized operator after reviewing the original Jonas policy.
- Reserve a defensible upper bound before any external provider call. Settle using provider usage/billing evidence afterward.
- The API cannot prevent calls made outside the gateway. Isolate credentials so application callers cannot bypass it.
- A settlement above its reservation records the overrun and halts new reservations. Resume is an operator action and this API cannot independently prove reconciliation.
- Hashes are integrity aids, not proof of authorship, truth, formal equivalence, or certification.
- Automatic provider calls remain disabled until official pricing/billing semantics, concurrency/restart behavior, security, savings, quality non-regression, independent review, and rollback are validated.

See [the design and validation gates](../docs/jonas-hott-live-telemetry.md).
