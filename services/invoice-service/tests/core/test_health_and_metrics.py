from fastapi.testclient import TestClient

from app.core.metrics import REGISTRY
from app.main import create_app


def _sample(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_PLT_002_AC6_health_is_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "invoice-service"


def test_PLT_002_AC6_ready_when_database_is_reachable(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}


def test_PLT_002_AC6_not_ready_when_database_is_unreachable(settings):
    unreachable = settings.model_copy(update={"postgres_port": 1})

    with TestClient(create_app(unreachable)) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": {"database": "fail"}}


def test_PLT_002_AC6_health_does_not_depend_on_database(settings):
    unreachable = settings.model_copy(update={"postgres_port": 1})

    with TestClient(create_app(unreachable)) as client:
        assert client.get("/health").status_code == 200


def test_PLT_002_AC7_requests_are_counted_by_route_template(client):
    labels = {"method": "GET", "route": "/api/invoices/_test/items/{item_id}", "status": "200"}
    before = _sample("http_requests_total", labels)

    client.get("/api/invoices/_test/items/1")
    client.get("/api/invoices/_test/items/2")

    assert _sample("http_requests_total", labels) == before + 2


def test_PLT_002_AC7_metrics_endpoint_exposes_prometheus_text(client):
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds_bucket" in response.text
