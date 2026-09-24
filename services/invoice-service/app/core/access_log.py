"""One access log line per request (PLT-002 AC3)."""

import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger

log = get_logger("access")

# Operational endpoints are polled constantly; keep them out of INFO logs.
QUIET_PATHS = frozenset({"/health", "/ready", "/metrics"})


def route_template(scope: Scope) -> str:
    """The matched route's template (e.g. /api/<module>/{id}), to keep labels low-cardinality."""
    route = scope.get("route")
    return getattr(route, "path", None) or "unmatched"


class AccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status = 500
        start = time.perf_counter()

        async def capture_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture_status)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            path = scope["path"]
            if path in QUIET_PATHS:
                level = "debug"
            elif status >= 500:
                level = "error"
            elif status >= 400:
                level = "warning"
            else:
                level = "info"

            client = scope.get("client")
            getattr(log, level)(
                "http.access",
                message=f"{scope['method']} {path} {status} in {duration_ms} ms",
                method=scope["method"],
                route=route_template(scope),
                path=path,
                status=status,
                duration_ms=duration_ms,
                client_ip=client[0] if client else None,
            )
