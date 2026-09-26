"""PLT-002 AC6/AC7 for assistant-service: no database; readiness = downstream + AI key."""

import httpx
from fastapi.testclient import TestClient

from app.main import create_app


def test_PLT_002_AC6_health_is_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "assistant-service"


def test_PLT_002_AC6_ready_checks_both_services_and_skips_db_and_key_in_fake_mode(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"invoice_service": "ok", "contract_service": "ok"},
    }


def test_PLT_002_AC6_ready_fails_when_a_service_is_down(client, downstream):
    downstream.unreachable.add("contract")

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["contract_service"] == "fail"


def test_PLT_002_AC6_claude_mode_without_a_key_is_not_ready(settings, downstream):
    claude = settings.model_copy(update={"assistant_llm": "claude"})
    app = create_app(claude, transport=httpx.MockTransport(downstream.handle))

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["ai_key"] == "fail"


def test_PLT_002_AC7_metrics_are_exposed(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "assistant_chats_total" in response.text


def test_PLT_002_unknown_api_route_uses_the_standard_error_body(client):
    response = client.get("/api/assistant/nope", headers={"X-Request-ID": "abc-12345"})

    assert response.status_code == 404
    assert response.json()["error"]["request_id"] == "abc-12345"
