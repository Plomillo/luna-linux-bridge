import importlib
import hashlib

from fastapi.testclient import TestClient


def configured_app(monkeypatch, tmp_path):
    monkeypatch.setenv("JONAS_API_TOKEN", "test-only-token")
    monkeypatch.setenv("JONAS_PERIOD_LIMIT_MICRO_USD", "1000000")
    monkeypatch.setenv("JONAS_PROTECTED_RESERVE_MICRO_USD", "200000")
    import jonas_hott_api.app as module
    module.DB_PATH = str(tmp_path / "jonas-test.sqlite3")
    module.TOKEN = "test-only-token"
    module.initialize_db()
    return module


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def headers():
    return {"Authorization": "Bearer test-only-token"}


def reservation(request_id="r-001", amount=300000):
    return {
        "request_id": request_id,
        "estimated_max_micro_usd": amount,
        "model_id": "operator-approved-reference",
        "policy_version": "test-v1",
        "evidence_sha256": digest("pricing-source-evidence"),
    }


def test_reservation_preserves_protected_reserve(monkeypatch, tmp_path):
    module = configured_app(monkeypatch, tmp_path)
    with TestClient(module.app) as client:
        response = client.post("/v1/reservations", headers=headers(), json=reservation(amount=800001))
        assert response.status_code == 402
        telemetry = client.get("/v1/telemetry", headers=headers())
        assert telemetry.status_code == 200
        assert telemetry.json()["protected_reserve_micro_usd"] == 200000
        assert telemetry.json()["reserved_micro_usd"] == 0


def test_reservation_and_idempotent_replay(monkeypatch, tmp_path):
    module = configured_app(monkeypatch, tmp_path)
    with TestClient(module.app) as client:
        first = client.post("/v1/reservations", headers=headers(), json=reservation())
        replay = client.post("/v1/reservations", headers=headers(), json=reservation())
        assert first.status_code == 200
        assert first.json()["status"] == "RESERVED"
        assert replay.status_code == 200
        assert replay.json()["idempotent_replay"] is True


def test_overrun_halts_new_reservations(monkeypatch, tmp_path):
    module = configured_app(monkeypatch, tmp_path)
    with TestClient(module.app) as client:
        created = client.post("/v1/reservations", headers=headers(), json=reservation())
        assert created.status_code == 200
        settled = client.post(
            "/v1/reservations/r-001/settle",
            headers=headers(),
            json={"actual_micro_usd": 300001, "usage_evidence_sha256": digest("usage")},
        )
        assert settled.status_code == 409
        blocked = client.post("/v1/reservations", headers=headers(), json=reservation("r-002", 100))
        assert blocked.status_code == 423


def test_missing_budget_fails_closed(monkeypatch, tmp_path):
    module = configured_app(monkeypatch, tmp_path)
    monkeypatch.delenv("JONAS_PERIOD_LIMIT_MICRO_USD")
    with TestClient(module.app) as client:
        response = client.post("/v1/reservations", headers=headers(), json=reservation())
        assert response.status_code == 503
