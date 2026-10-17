# Jonas family service — install, backup, restore and rollback

**Release state: source candidate only; not production-deployable or certified.** The repository does not yet provision a shared host, TLS, a reverse proxy, rate limits, a system service, or production secrets. Do not expose the development server directly to the Internet or a household LAN.

## 1. Clean local installation

Use Python 3.11 or newer. Run from a clean checkout or the extracted source candidate:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r jonas_hott_api/requirements.txt
```

Set the following variables using a local secret manager or an environment file stored outside the repository with owner-only permissions:

- `JONAS_API_TOKEN`: long random service token for protected API routes.
- `JONAS_FAMILY_RESPONDENT_TOKENS_JSON`: five distinct private bearer tokens keyed to Sebastián, Diego, Catalina, Marjorie and Cristóbal.
- `JONAS_DB_PATH`: absolute path to the SQLite database.
- `JONAS_PERIOD_LIMIT_MICRO_USD` and `JONAS_PROTECTED_RESERVE_MICRO_USD`: explicit budget values in integer micro-USD; choose real values deliberately, never copy test defaults.

Do not commit secrets, database files, backups, or a populated environment file. Start locally:

```bash
uvicorn jonas_hott_api.app:app --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787/family-check-in`. The form records a manual observation; it does not call a provider balance API. Each person must use their own token. The generic service token is not a respondent identity.

## 2. Health and acceptance checks

```bash
curl --fail http://127.0.0.1:8787/health
python -m pytest -q tests/test_jonas_hott_api.py tests/test_jonas_account_state.py tests/test_jonas_backup_restore.py
```

A passing health response only proves that the local process responds. It does not prove provider billing, official model-catalog completeness, TLS, family-wide deployment, or certification.

## 3. Backup and integrity verification

Stop writes or schedule a quiet window before backing up. The tool uses SQLite's online backup API, runs `PRAGMA integrity_check`, and emits a SHA-256 sidecar and JSON manifest. It refuses to overwrite an existing backup.

```bash
mkdir -p backups
python scripts/missions/backup_restore_jonas_state.py backup \
  --source "$JONAS_DB_PATH" \
  --destination "backups/jonas-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
```

Verify a backup before storing or restoring it:

```bash
BACKUP="backups/jonas-YYYYMMDDTHHMMSSZ.sqlite3"
EXPECTED="$(awk '{print $1}' "$BACKUP.sha256")"
python scripts/missions/backup_restore_jonas_state.py verify \
  --database "$BACKUP" --expected-sha256 "$EXPECTED"
```

Store backups separately from the running database and protect them as sensitive family data.

## 4. Restore and rollback

**Restore is destructive and requires explicit authorization.** Stop the service first; confirm that no `-wal` or `-shm` sidecar exists. The tool verifies the supplied digest, verifies SQLite integrity, creates a pre-restore checkpoint if the destination exists, writes a temporary restored database, verifies it, and then atomically replaces the target.

```bash
BACKUP="backups/jonas-YYYYMMDDTHHMMSSZ.sqlite3"
EXPECTED="$(awk '{print $1}' "$BACKUP.sha256")"
python scripts/missions/backup_restore_jonas_state.py restore \
  --source-backup "$BACKUP" \
  --destination "$JONAS_DB_PATH" \
  --expected-sha256 "$EXPECTED" \
  --confirm-restore \
  --service-stopped-confirmed
```

Do not set `--service-stopped-confirmed` until the service is actually stopped. Keep the generated pre-restore checkpoint and restore JSON report until post-restore validation passes. Restart the service and re-run health checks and the test suite.

Rollback to a prior code version is separate from database restore: stop the process, preserve the database and its backup, revert the code checkout to the prior reviewed commit, reinstall that version's requirements, and run tests before restarting. This repository does not install a systemd service automatically; service-manager rollback must be configured and tested on the eventual host.

## 5. Shared deployment gate

Before multiple devices use the service, configure and independently test HTTPS/TLS, reverse-proxy request limits, allowed origins, per-user token provisioning/rotation/revocation, audit retention, encrypted backup storage, recovery drills, and access control. The current candidate has not passed those gates. Do not treat a successful local CI run as production authorization.
