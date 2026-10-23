# Jonas Budget & Telemetry — runnable MVP

A small local web application for budget limits, protected reserves, idempotent spend recording, event telemetry, and candidate savings gates. Uses Python 3.10+ standard library only; no package installation is required.

## Run

From this directory:

```sh
python app.py
```

Open http://127.0.0.1:8765. Data is stored in `jonas.sqlite3` beside the app by default. Set `JONAS_DB`, `JONAS_HOST`, or `JONAS_PORT` to override defaults. Keep the host at loopback for local use.

## Features

- Create budgets with an explicit protected reserve.
- Record spend using integer micro-USD, transactional SQLite writes, and idempotency keys.
- Reject spending that would consume the protected reserve or exceed the limit.
- Halt a budget; halted budgets reject new spending.
- Append events to a SHA-256 hash chain and verify the chain through `GET /api/telemetry`.
- Evaluate candidate savings; accepted only at >=10% savings, quality pass, and no critical regression.
- Browser dashboard plus JSON API.

## API

- `GET /api/health`
- `GET /api/budgets`
- `POST /api/budgets` — `{"id":"team","limit":"100","reserve":"10"}`
- `POST /api/budgets/{id}/spend` — `{"amount":"2.5","idempotency_key":"invoice-123","category":"inference","note":"optional"}`
- `POST /api/budgets/{id}/halt`
- `POST /api/budgets/{id}/resume` — requires `{"confirm":true}`
- `GET /api/telemetry`
- `POST /api/savings/evaluate` — `{"baseline_cost":"100","candidate_cost":"85","quality_pass":true,"critical_regression":false}`

## Tests

```sh
python -m unittest -v
```

## Important limitations

This is a local MVP, not production-certified software. It does not call model providers, fetch official prices, reconcile provider invoices, or prove actual savings by itself. Telemetry only covers events this service sees. The server has no authentication or CSRF protection and must not be exposed to a network; add security controls and independent review before any shared or production deployment. The hash chain detects accidental/unauthorized modification relative to the stored chain but is not externally anchored and cannot prevent a privileged attacker from rewriting the database and recomputing hashes. No automatic model/config substitution is performed.
