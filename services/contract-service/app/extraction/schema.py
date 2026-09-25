"""The extraction result: a JSON schema sent to Claude (`output_config.format`) and the Pydantic
models that validate the response again (ADR-0002, CON-001 AC4/AC10).

The JSON schema is written out by hand so it stays within the structured-outputs subset
(no length/size keywords); `test_schema.py` checks it matches the Pydantic models field for field.
"""

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

TermCategory = Literal[
    "payment", "termination", "renewal", "liability", "confidentiality", "governing_law", "other"
]
Severity = Literal["high", "medium", "low"]

LIMITS = {"parties": 20, "key_dates": 40, "terms": 60, "risks": 40}
MAX_QUOTE_CHARS = 300


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Party(_Strict):
    name: str
    role: str


class KeyDate(_Strict):
    label: str
    date: dt.date
    source_text: str


class Term(_Strict):
    category: TermCategory
    summary: str
    source_text: str


class Risk(_Strict):
    severity: Severity
    title: str
    description: str
    source_text: str


class ContractExtraction(_Strict):
    title: str
    summary: str
    parties: list[Party]
    start_date: dt.date | None
    end_date: dt.date | None
    key_dates: list[KeyDate]
    terms: list[Term]
    risks: list[Risk]

    @field_validator("parties", "key_dates", "terms", "risks")
    @classmethod
    def _cap(cls, items: list[Any], info: Any) -> list[Any]:
        # The prompt asks for the most important items first, so keep the head of each list.
        return items[: LIMITS[info.field_name]]


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_TEXT = {"type": "string"}
_DATE = {"type": "string", "description": "ISO date, YYYY-MM-DD"}
_QUOTE = {
    "type": "string",
    "description": (
        f"A short verbatim quote (at most {MAX_QUOTE_CHARS} characters) from the contract"
    ),
}

JSON_SCHEMA: dict[str, Any] = _object(
    {
        "title": _TEXT,
        "summary": _TEXT,
        "parties": {"type": "array", "items": _object({"name": _TEXT, "role": _TEXT})},
        "start_date": _nullable(_DATE),
        "end_date": _nullable(_DATE),
        "key_dates": {
            "type": "array",
            "items": _object({"label": _TEXT, "date": _DATE, "source_text": _QUOTE}),
        },
        "terms": {
            "type": "array",
            "items": _object(
                {
                    "category": {"type": "string", "enum": list(TermCategory.__args__)},
                    "summary": _TEXT,
                    "source_text": _QUOTE,
                }
            ),
        },
        "risks": {
            "type": "array",
            "items": _object(
                {
                    "severity": {"type": "string", "enum": list(Severity.__args__)},
                    "title": _TEXT,
                    "description": _TEXT,
                    "source_text": _QUOTE,
                }
            ),
        },
    }
)
