from app.core.errors import INTERNAL_ERROR_MESSAGE


def test_PLT_002_AC8_unhandled_error_returns_standard_body_with_request_id(client, logs):
    response = client.get("/api/invoices/_test/boom", headers={"X-Request-ID": "boom-request-1"})

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "boom-request-1"
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": INTERNAL_ERROR_MESSAGE,
            "details": {},
            "request_id": "boom-request-1",
        }
    }
    assert "Traceback" not in response.text
    assert "probe failure" not in response.text

    lines = logs()
    error = next(line for line in lines if line["event"] == "http.unhandled_error")
    assert error["request_id"] == "boom-request-1"
    assert "RuntimeError: probe failure" in error["exception"]
    access = next(line for line in lines if line["event"] == "http.access")
    assert access["status"] == 500
    assert access["level"] == "error"


def test_PLT_002_AC8_app_error_uses_its_own_code_and_message(client):
    response = client.get("/api/invoices/_test/app-error")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "DEMO_ERROR"
    assert error["message"] == "A friendly message."
    assert error["details"] == {"hint": "x"}
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_PLT_002_AC8_validation_error_is_friendly(client):
    response = client.get("/api/invoices/_test/items/not-a-number")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "Some of the information sent was not valid."
    assert error["details"]["fields"][0]["field"] == "path.item_id"


def test_PLT_002_AC8_not_found_is_friendly(client):
    response = client.get("/api/invoices/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
