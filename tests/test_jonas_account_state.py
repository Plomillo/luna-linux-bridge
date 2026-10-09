import hashlib
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from jonas_hott_api.app import app


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def auth():
    return {"Authorization": "Bearer account-state-test-token"}


def respondent_auth(actor):
    return {"Authorization": "Bearer family-test-token:" + actor}


def observation(observation_id, actor, balance, observed_at=None):
    return {
        "observation_id": observation_id,
        "observed_at_utc": observed_at or datetime.now(timezone.utc).isoformat(),
        "balance_credits": balance,
        "source_kind": "manual",
        "source_reference": "family-member-confirmation",
        "actor": actor,
        "shared_pool_id": "family-shared",
        "unit": "credits",
        "consent_confirmed": True,
        "evidence_sha256": digest(observation_id + actor + str(balance)),
        "notes": "Self-reported; not provider-API synchronized.",
    }


def setup_state(monkeypatch, tmp_path):
    import jonas_hott_api.app as module
    monkeypatch.setenv("JONAS_API_TOKEN", "account-state-test-token")
    monkeypatch.setenv("JONAS_ACCOUNT_STATE_TTL_SECONDS", "3600")
    tokens = {name: "family-test-token:" + name for name in
              ("Sebastián", "Diego", "Catalina", "Marjorie", "Cristóbal")}
    monkeypatch.setenv("JONAS_FAMILY_RESPONDENT_TOKENS_JSON", json.dumps(tokens, ensure_ascii=False))
    module.TOKEN = "account-state-test-token"
    module.DB_PATH = str(tmp_path / "shared-state.sqlite3")


def test_shared_pool_observations_are_append_only_and_not_summed(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    with TestClient(app) as client:
        first_payload = observation("credit-001", "Diego", 3936630)
        second_payload = observation("credit-002", "Catalina", 3936630)
        first = client.post("/v1/account/credits/observations", headers=respondent_auth("Diego"), json=first_payload)
        replay = client.post("/v1/account/credits/observations", headers=respondent_auth("Diego"), json=first_payload)
        second = client.post("/v1/account/credits/observations", headers=respondent_auth("Catalina"), json=second_payload)
        latest = client.get("/v1/account/credits", headers=auth())
        history = client.get("/v1/account/credits/history", headers=auth())
    assert first.status_code == second.status_code == replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert latest.status_code == 200
    assert latest.json()["balance_credits"] == 3936630
    assert latest.json()["shared_pool"] is True
    assert latest.json()["current_report_count"] == 2
    assert latest.json()["status"] == "OBSERVED"
    assert latest.json()["certified"] is False
    assert len(history.json()["observations"]) == 2


def test_disagreeing_family_reports_fail_closed_until_latest_reports_agree(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    with TestClient(app) as client:
        a = client.post("/v1/account/credits/observations", headers=respondent_auth("Diego"),
                        json=observation("credit-101", "Diego", 1000))
        b = client.post("/v1/account/credits/observations", headers=respondent_auth("Catalina"),
                        json=observation("credit-102", "Catalina", 900))
        conflict = client.get("/v1/account/credits", headers=auth())
        reconfirm = client.post("/v1/account/credits/observations", headers=respondent_auth("Catalina"),
                                json=observation("credit-103", "Catalina", 1000))
        resolved = client.get("/v1/account/credits", headers=auth())
        history = client.get("/v1/account/credits/history", headers=auth())
    assert a.status_code == b.status_code == reconfirm.status_code == 200
    assert conflict.json()["status"] == "CONFLICTING"
    assert conflict.json()["balance_credits"] is None
    assert conflict.json()["conflict_resolution_required"] is True
    assert resolved.json()["status"] == "OBSERVED"
    assert resolved.json()["balance_credits"] == 1000
    assert len(history.json()["observations"]) == 3


def test_unknown_balance_when_no_observation_exists(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.get("/v1/account/credits", headers=auth())
    assert response.status_code == 200
    assert response.json()["status"] == "UNKNOWN"
    assert response.json()["balance_credits"] is None


def test_only_authorized_family_respondents_and_consent_are_accepted(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    with TestClient(app) as client:
        impersonation = client.post("/v1/account/credits/observations", headers=respondent_auth("Diego"),
                                   json=observation("credit-201", "Sebastián", 100))
        no_consent_payload = observation("credit-202", "Sebastián", 100)
        no_consent_payload.pop("consent_confirmed")
        no_consent = client.post("/v1/account/credits/observations", headers=respondent_auth("Sebastián"),
                                 json=no_consent_payload)
    assert impersonation.status_code == 403
    assert no_consent.status_code == 422


def test_all_five_family_members_have_individual_write_identity(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    respondents = ("Sebastián", "Diego", "Catalina", "Marjorie", "Cristóbal")
    with TestClient(app) as client:
        responses = [
            client.post(
                "/v1/account/credits/observations",
                headers=respondent_auth(name),
                json=observation("all-five-" + str(index), name, 1200),
            )
            for index, name in enumerate(respondents)
        ]
        latest = client.get("/v1/account/credits", headers=auth())
    assert all(response.status_code == 200 for response in responses)
    assert latest.json()["current_report_count"] == 5
    assert set(latest.json()["respondents_reporting"]) == set(respondents)


def test_catalog_snapshot_is_not_certified_by_source_label_alone(monkeypatch, tmp_path):
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
            "models": [{"model_id": "example-model-id", "display_name": "Example model",
                        "capabilities": ["chat"], "metadata": {"status": "test-fixture"}}],
            "evidence_sha256": digest("catalog-source-evidence"),
        }
        saved = client.post("/v1/models/catalog/snapshots", headers=auth(), json=payload)
    assert saved.status_code == 200
    assert saved.json()["provider_catalog_verified"] is False
    assert saved.json()["certified"] is False
