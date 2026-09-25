"""Standard error responses (PLT-002 AC8, architecture.md API conventions).

Every error body has the same shape and carries the request ID, so the UI can show
"Something went wrong. Reference: <request_id>".
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger
from app.core.request_context import REQUEST_ID_HEADER

log = get_logger("errors")

INTERNAL_ERROR_MESSAGE = "Something went wrong on our side. Please try again."

_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    404: ("NOT_FOUND", "We couldn't find what you were looking for."),
    405: ("METHOD_NOT_ALLOWED", "This action isn't supported here."),
    413: ("FILE_TOO_LARGE", "This file is too large."),
}


class AppError(Exception):
    """A business error with a message that is safe to show to users as-is."""

    def __init__(
        self, code: str, message: str, status: int = 400, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


def error_body(
    code: str, message: str, request_id: str | None, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        }
    }


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status, content=error_body(code, message, _request_id(request), details)
    )


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return error_response(request, exc.status, exc.code, exc.message, exc.details)


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(p) for p in err["loc"]), "problem": err["msg"]}
        for err in exc.errors()
    ]
    return error_response(
        request,
        422,
        "VALIDATION_ERROR",
        "Some of the information sent was not valid.",
        {"fields": fields},
    )


async def _http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _HTTP_ERRORS.get(exc.status_code, ("HTTP_ERROR", str(exc.detail)))
    return error_response(request, exc.status_code, code, message)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)


class UnhandledErrorMiddleware:
    """Turns any unexpected exception into the standard 500 body.

    Sits inside the request-context and access-log middleware, so the error log line, the
    response header and the error body all carry the request ID.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def track_start(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, track_start)
        except Exception:
            log.error(
                "http.unhandled_error",
                message=f"Unhandled error on {scope['method']} {scope['path']}",
                exc_info=True,
            )
            if response_started:
                raise
            request_id = scope.get("state", {}).get("request_id")
            response = JSONResponse(
                status_code=500,
                content=error_body("INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE, request_id),
                headers={REQUEST_ID_HEADER: request_id} if request_id else None,
            )
            await response(scope, receive, send)
