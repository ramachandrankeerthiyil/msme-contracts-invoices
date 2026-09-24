"""Structured JSON logging (PLT-002 AC1, AC5, AC9).

Every line is one JSON object on stdout with at least: timestamp, level, service,
request_id (when inside a request), event, message.

Call sites log a stable machine name as the event and a human message:
    log.info("invoice_upload.completed", message="Invoice upload processed", rows_created=3)
"""

import logging
import sys
from typing import IO, Any

import structlog
from structlog.types import EventDict, Processor

REDACTED = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {"api_key", "authorization", "password", "document_text", "raw_extraction", "rows", "content"}
)
MAX_VALUE_LENGTH = 500


def redact_sensitive(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    """Mask sensitive keys and truncate very long strings (AC5)."""
    for key, value in event_dict.items():
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = REDACTED
        elif isinstance(value, str) and len(value) > MAX_VALUE_LENGTH:
            event_dict[key] = value[:MAX_VALUE_LENGTH] + "…[truncated]"
    return event_dict


def _ensure_message(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    event_dict.setdefault("message", event_dict.get("event", ""))
    return event_dict


def _normalise_foreign(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    """Records from stdlib loggers (uvicorn, sqlalchemy …) carry free text as the event."""
    event_dict["message"] = event_dict.get("event", "")
    event_dict["event"] = "library.log"
    record = event_dict.get("_record")
    if record is not None:
        event_dict["logger"] = record.name
    return event_dict


def _add_service(service: str) -> Processor:
    def add_service(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
        event_dict["service"] = service
        return event_dict

    return add_service


def _shared_processors(service: str) -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        _add_service(service),
    ]


def build_formatter(service: str) -> structlog.stdlib.ProcessorFormatter:
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[*_shared_processors(service), _normalise_foreign, redact_sensitive],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
    )


def configure_logging(service: str, level: str = "INFO", stream: IO[str] | None = None) -> None:
    structlog.configure(
        processors=[
            *_shared_processors(service),
            _ensure_message,
            redact_sensitive,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )

    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(build_formatter(service))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Route uvicorn's own loggers through the root JSON handler. Its access log is replaced
    # by AccessLogMiddleware, so it is switched off to avoid duplicate lines.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers.clear()
        lib_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger(name)
