import hashlib
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from jonas_hott_api.app import app


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def auth():
    return {"Authorization": "Bearer account-state-test-token"}


def respondent_token(actor):
    return {
        "Sebastián": "family-test-token:sebastian",
        "Diego": "family-test-token:diego",
        "Catalina": "family-test-token:catalina",
        "Marjorie": "family-test-token:marjorie",
        "Cristóbal": "family-test-token:cristobal",
    }[actor]


def respondent_auth(actor):
    return {"Authorization": "Bearer " + respondent_token(actor)}


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
    tokens = {name: respondent_token(name) for name in
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
    assert latest.json()["confirmed_balance_credits"] is None
    assert latest.json()["confirmation_state"] == "AWAITING_FAMILY_CONFIRMATIONS"
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
        latest = client.get("/v1/account/credits", headers=respondent_auth("Cristóbal"))
    assert all(response.status_code == 200 for response in responses)
    assert latest.json()["current_report_count"] == 5
    assert latest.json()["confirmed_balance_credits"] == 1200
    assert latest.json()["confirmation_state"] == "CONFIRMED_BY_ALL_FIVE"
    assert set(latest.json()["respondents_reporting"]) == set(respondents)


def test_guided_family_checkin_page_is_served_without_provider_api(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.get("/family-check-in")
    assert response.status_code == 200
    assert "Sebastián" in response.text
    assert "Cristóbal" in response.text
    assert "No consulta ninguna API de saldo" in response.text


def test_family_credit_write_fails_closed_without_all_respondent_tokens(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    monkeypatch.delenv("JONAS_FAMILY_RESPONDENT_TOKENS_JSON")
    with TestClient(app) as client:
        response = client.post(
            "/v1/account/credits/observations",
            headers=respondent_auth("Diego"),
            json=observation("missing-family-token-map", "Diego", 100),
        )
    assert response.status_code == 503


def test_stale_family_observation_is_marked_stale(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    old_time = (datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year - 1)).isoformat()
    with TestClient(app) as client:
        saved = client.post(
            "/v1/account/credits/observations",
            headers=respondent_auth("Diego"),
            json=observation("stale-credit-001", "Diego", 1000, old_time),
        )
        latest = client.get("/v1/account/credits", headers=auth())
    assert saved.status_code == 200
    assert latest.json()["freshness"] == "STALE"
    assert latest.json()["status"] == "STALE"
    assert latest.json()["balance_credits"] is None
    assert latest.json()["last_observed_balance_credits"] == 1000


def test_catalog_rejects_duplicate_model_ids(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    payload = {
        "snapshot_id": "duplicate-model-ids",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_kind": "manual",
        "source_reference": "local-fixture",
        "actor": "test-importer",
        "models": [{"model_id": "same-id"}, {"model_id": "same-id"}],
        "evidence_sha256": digest("duplicate-catalog-fixture"),
    }
    with TestClient(app) as client:
        response = client.post("/v1/models/catalog/snapshots", headers=auth(), json=payload)
    assert response.status_code == 422


def test_catalog_snapshot_id_cannot_be_replayed_with_changed_content(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    payload = {
        "snapshot_id": "immutable-catalog-001",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_kind": "manual",
        "source_reference": "local-fixture",
        "actor": "test-importer",
        "models": [{"model_id": "model-a"}],
        "evidence_sha256": digest("catalog-source-evidence"),
    }
    changed = {**payload, "models": [{"model_id": "model-b"}]}
    with TestClient(app) as client:
        first = client.post("/v1/models/catalog/snapshots", headers=auth(), json=payload)
        replay = client.post("/v1/models/catalog/snapshots", headers=auth(), json=changed)
    assert first.status_code == 200
    assert replay.status_code == 409


def test_model_recommendations_require_evidence_for_constrained_metrics(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    snapshot = {
        "snapshot_id": "recommendation-catalog-001",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_kind": "manual",
        "source_reference": "local-fixture-not-an-official-catalog",
        "actor": "test-importer",
        "models": [
            {
                "model_id": "vision-good",
                "display_name": "Vision Good",
                "capabilities": ["chat", "vision"],
                "metadata": {
                    "quality_score": 0.92,
                    "quality_score_evidence_sha256": digest("quality-evidence"),
                    "latency_ms": 250,
                    "latency_ms_evidence_sha256": digest("latency-evidence"),
                    "estimated_cost_credits": 2.5,
                    "estimated_cost_credits_evidence_sha256": digest("cost-evidence"),
                },
            },
            {
                "model_id": "vision-unknown-cost",
                "capabilities": ["vision"],
                "metadata": {
                    "quality_score": 0.95,
                    "quality_score_evidence_sha256": digest("quality-evidence-2"),
                    "latency_ms": 100,
                    "latency_ms_evidence_sha256": digest("latency-evidence-2"),
                },
            },
        ],
        "evidence_sha256": digest("snapshot-source-evidence"),
    }
    with TestClient(app) as client:
        saved = client.post("/v1/models/catalog/snapshots", headers=auth(), json=snapshot)
        response = client.get(
            "/v1/models/recommendations",
            headers=auth(),
            params={
                "task": "image understanding",
                "required_capabilities": ["vision"],
                "min_quality_score": 0.8,
                "max_latency_ms": 300,
                "max_estimated_cost_credits": 5,
            },
        )
    assert saved.status_code == 200
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "CANDIDATES_UNVERIFIED"
    assert result["catalog_source_verified"] is False
    assert [item["model_id"] for item in result["recommendations"]] == ["vision-good"]
    assert result["recommendations"][0]["estimated_cost_credits"] == 2.5
    assert result["excluded"][0]["reason"] == "CONSTRAINT_NOT_MET_OR_UNKNOWN"
    assert "COST_UNKNOWN_OR_UNEVIDENCED" in result["excluded"][0]["details"]


def test_model_recommendations_leave_unpriced_cost_unknown(monkeypatch, tmp_path):
    setup_state(monkeypatch, tmp_path)
    snapshot = {
        "snapshot_id": "recommendation-catalog-unknown-cost",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_kind": "manual",
        "source_reference": "local-fixture",
        "actor": "test-importer",
        "models": [{"model_id": "unpriced", "capabilities": ["chat"], "metadata": {}}],
        "evidence_sha256": digest("unknown-cost-catalog"),
    }
    with TestClient(app) as client:
        client.post("/v1/models/catalog/snapshots", headers=auth(), json=snapshot)
        response = client.get(
            "/v1/models/recommendations",
            headers=auth(),
            params={"task": "chat", "required_capabilities": ["chat"]},
        )
    assert response.json()["recommendations"][0]["estimated_cost_credits"] is None
    assert response.json()["recommendations"][0]["catalog_source_verified"] is False


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
