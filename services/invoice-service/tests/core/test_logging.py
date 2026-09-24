import io
import re

import pytest

from app.core.logging import REDACTED, configure_logging, get_logger, redact_sensitive

REQUIRED_KEYS = {"timestamp", "level", "service", "event", "message"}


def _access_lines(lines):
    return [line for line in lines if line["event"] == "http.access"]


def test_PLT_002_AC1_every_line_is_json_with_required_fields(client, logs):
    client.get("/api/invoices/does-not-exist")

    lines = logs()
    assert lines, "expected at least one log line"
    for line in lines:
        assert line.keys() >= REQUIRED_KEYS
        assert line["service"] == "invoice-service"
    access = _access_lines(lines)[0]
    assert re.fullmatch(r"[0-9a-f]{32}", access["request_id"])
    assert access["timestamp"].endswith("Z")


def test_PLT_002_AC2_valid_incoming_request_id_is_kept_everywhere(client, logs):
    response = client.get("/api/invoices/does-not-exist", headers={"X-Request-ID": "abc-12345"})

    assert response.headers["X-Request-ID"] == "abc-12345"
    assert response.json()["error"]["request_id"] == "abc-12345"
    assert _access_lines(logs())[0]["request_id"] == "abc-12345"


@pytest.mark.parametrize(
    "incoming",
    [None, "short", "has spaces in it", "x" * 65, 'quote"injection-1', "semi;colon-12345"],
)
def test_PLT_002_AC2_missing_or_malformed_request_id_is_replaced(client, incoming):
    headers = {} if incoming is None else {"X-Request-ID": incoming}

    response = client.get("/health", headers=headers)

    request_id = response.headers["X-Request-ID"]
    assert request_id != incoming
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)


def test_PLT_002_AC3_one_access_line_per_request(client, logs):
    client.get("/api/invoices/_test/items/42")

    access = _access_lines(logs())
    assert len(access) == 1
    line = access[0]
    assert line["method"] == "GET"
    assert line["path"] == "/api/invoices/_test/items/42"
    assert line["route"] == "/api/invoices/_test/items/{item_id}"
    assert line["status"] == 200
    assert line["level"] == "info"
    assert isinstance(line["duration_ms"], float)


def test_PLT_002_AC3_client_errors_are_logged_as_warnings(client, logs):
    client.get("/api/invoices/does-not-exist")

    line = _access_lines(logs())[0]
    assert line["status"] == 404
    assert line["route"] == "unmatched"
    assert line["level"] == "warning"


def test_PLT_002_AC5_sensitive_keys_are_redacted_and_long_values_truncated():
    event = redact_sensitive(
        None,
        "info",
        {
            "event": "x",
            "api_key": "sk-secret",
            "Password": "hunter2",
            "authorization": "Bearer abc",
            "document_text": "confidential",
            "raw_extraction": {"a": 1},
            "rows": [1, 2],
            "content": "file bytes",
            "note": "y" * 600,
            "ok": "fine",
        },
    )

    for key in (
        "api_key",
        "Password",
        "authorization",
        "document_text",
        "raw_extraction",
        "rows",
        "content",
    ):
        assert event[key] == REDACTED
    assert event["note"].startswith("y" * 500)
    assert event["note"].endswith("[truncated]")
    assert len(event["note"]) < 600
    assert event["ok"] == "fine"


def test_PLT_002_AC5_emitted_lines_never_contain_secrets(app, logs):
    get_logger("test").info("test.event", api_key="sk-live-secret")

    line = next(line for line in logs() if line["event"] == "test.event")
    assert line["api_key"] == REDACTED


def test_PLT_002_AC9_log_level_is_configurable(settings):
    stream = io.StringIO()
    try:
        configure_logging(settings.service_name, "WARNING", stream=stream)
        log = get_logger("test")
        log.info("hidden.event")
        log.warning("shown.event")
    finally:
        configure_logging(settings.service_name, settings.log_level)

    output = stream.getvalue()
    assert "hidden.event" not in output
    assert "shown.event" in output
