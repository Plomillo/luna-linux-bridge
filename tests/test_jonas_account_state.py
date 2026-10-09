import hashlib
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from jonas_hott_api.app import app


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def auth():
    return {"Authorization": "Bearer account-state-test-token"}


def test_shared_credit_observation_is_append_only_and_fresh(monkeypatch, tmp_path):
    import jonas_hott_api.app as module
    monkeypatch.setenv("JONAS_API_TOKEN", "account-state-test-token")
    monkeypatch.setenv("JONAS_ACCOUNT_STATE_TTL_SECONDS", "3600")
    module.TOKEN = "account-state-test-token"
    module.DB_PATH = str(tmp_path / "shared-state.sqlite3")

    with TestClient(app) as client:
        payload = {
            "observation_id": "credit-observation-001",
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "balance_credits": 3936630,
            "source_kind": "manual",
            "source_reference": "operator-provided-account-screenshot",
            "actor": "operator",
            "evidence_sha256": digest("source-evidence"),
            "notes": "Manual baseline; not an API-synchronized value.",
        }
        first = client.post("/v1/account/credits/observations", headers=auth(), json=payload)
        replay = client.post("/v1/account/credits/observations", headers=auth(), json=payload)
        latest = client.get("/v1/account/credits", headers=auth())
        history = client.get("/v1/account/credits/history", headers=auth())

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert latest.status_code == 200
    assert latest.json()["balance_credits"] == 3936630
    assert latest.json()["source_kind"] == "manual"
    assert latest.json()["freshness"] == "FRESH"
    assert latest.json()["balance_is_estimate"] is False
    assert history.status_code == 200
    assert len(history.json()["observations"]) == 1


def test_missing_credit_observation_is_unknown(monkeypatch, tmp_path):
    import jonas_hott_api.app as module
    monkeypatch.setenv("JONAS_API_TOKEN", "account-state-test-token")
    module.TOKEN = "account-state-test-token"
    module.DB_PATH = str(tmp_path / "empty-state.sqlite3")

    with TestClient(app) as client:
        response = client.get("/v1/account/credits", headers=auth())

    assert response.status_code == 200
    assert response.json()["status"] == "UNKNOWN"
    assert response.json()["balance_credits"] is None


def test_catalog_snapshot_is_shared_and_versioned(monkeypatch, tmp_path):
    import jonas_hott_api.app as module
    monkeypatch.setenv("JONAS_API_TOKEN", "account-state-test-token")
    module.TOKEN = "account-state-test-token"
    module.DB_PATH = str(tmp_path / "catalog-state.sqlite3")

    with TestClient(app) as client:
        payload = {
            "snapshot_id": "catalog-snapshot-001",
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_kind": "official_api",
            "source_reference": "https://docs.1min.ai/docs/api/openai-compatible",
            "actor": "catalog-importer",
            "models": [
                {"model_id": "example-model-id", "display_name": "Example model",
                 "capabilities": ["chat"], "metadata": {"status": "test-fixture"}}
            ],
            "evidence_sha256": digest("catalog-source-evidence"),
        }
        saved = client.post("/v1/models/catalog/snapshots", headers=auth(), json=payload)
        latest = client.get("/v1/models/catalog", headers=auth())

    assert saved.status_code == 200
    assert saved.json()["model_count"] == 1
    assert saved.json()["provider_catalog_verified"] is True
    assert latest.status_code == 200
    assert latest.json()["models"][0]["model_id"] == "example-model-id"
    assert latest.json()["source_kind"] == "official_api"
