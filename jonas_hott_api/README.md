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
pytest -q tests/test_jonas_hott_api.py
```

## Safety boundary

- Bind to loopback for local development; do not expose publicly without TLS, network restrictions, secret management, and an authentication review.
- Configure real limits and reserve only through an authorized operator after reviewing the original Jonas policy.
- Reserve a defensible upper bound before any external provider call. Settle using provider usage/billing evidence afterward.
- The API cannot prevent calls made outside the gateway. Isolate credentials so application callers cannot bypass it.
- A settlement above its reservation records the overrun and halts new reservations. Resume is an operator action and this API cannot independently prove reconciliation.
- Hashes are integrity aids, not proof of authorship, truth, formal equivalence, or certification.
- Automatic provider calls remain disabled until official pricing/billing semantics, concurrency/restart behavior, security, savings, quality non-regression, independent review, and rollback are validated.

See [the design and validation gates](../docs/jonas-hott-live-telemetry.md).
