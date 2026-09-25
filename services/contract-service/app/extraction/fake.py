"""A deterministic stand-in for Claude (CONTRACT_EXTRACTOR=fake): tests and e2e, no API, no cost.

It builds plausible results from the text with simple patterns, and quotes real sentences, so
quote verification, statuses and the UI can all be exercised. A file name containing "fail"
makes every attempt fail, to exercise the failure path.
"""

import re
from datetime import date, datetime

from app.extraction.base import ExtractionFailed, ExtractionResult
from app.extraction.schema import ContractExtraction, KeyDate, Party, Risk, Term

_DATE = re.compile(
    r"\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|"
    r"November|December) (\d{4})\b"
)
_PARTY = re.compile(
    r"\b([A-Z][\w&.]*(?: [A-Z][\w&.]*)*? (?:Private Limited|Pvt Ltd|Limited|LLP|Works|Traders))\b"
)
_ROLE = re.compile(r'\(the "([A-Z][A-Za-z ]+)"\)')
_SENTENCE = re.compile(r"[^.\n]+[.\n]")

_RISK_CUES = [
    ("without limit", "high", "Unlimited indemnity", "You could have to cover losses with no cap."),
    (
        "seven (7) days",
        "high",
        "Provider can leave at short notice",
        "The other side can end the contract almost immediately.",
    ),
    (
        "automatically renew",
        "medium",
        "Automatic renewal",
        "The contract renews unless you give notice in time.",
    ),
    ("24% per annum", "medium", "High late-payment interest", "Late payments become expensive."),
]
_TERM_CUES = [
    ("payable", "payment"),
    ("pay each invoice", "payment"),
    ("terminate", "termination"),
    ("renew", "renewal"),
    ("liability", "liability"),
    ("confidential", "confidentiality"),
    ("laws of India", "governing_law"),
]


def _sentence_with(text: str, cue: str) -> str | None:
    for match in _SENTENCE.finditer(text):
        sentence = match.group().strip()
        if cue.lower() in sentence.lower():
            return sentence[:300]
    return None


class FakeExtractor:
    model = "fake-extractor"

    async def extract(self, contract_text: str, file_name: str) -> ExtractionResult:
        if "fail" in file_name.lower():
            raise ExtractionFailed("fake extractor: forced failure")

        lines = [line.strip() for line in contract_text.splitlines() if line.strip()]
        title = next((line for line in lines if not line.startswith("[Page")), file_name)[:120]

        dates = list(
            dict.fromkeys(  # distinct, in order of first mention
                datetime.strptime(" ".join(m.groups()), "%d %B %Y").date()
                for m in _DATE.finditer(contract_text)
            )
        )
        start, end = (dates[0], dates[1]) if len(dates) >= 2 else (None, None)

        names = list(dict.fromkeys(m.group(1) for m in _PARTY.finditer(contract_text)))[:2]
        roles = _ROLE.findall(contract_text) + ["Party", "Party"]
        parties = [Party(name=name, role=roles[i]) for i, name in enumerate(names)]

        risks = (
            [
                Risk(severity=sev, title=t, description=d, source_text=quote)  # type: ignore[arg-type]
                for cue, sev, t, d in _RISK_CUES
                if (quote := _sentence_with(contract_text, cue))
            ]
            or [
                Risk(
                    severity="low",
                    title="Standard terms",
                    description="No unusual terms found.",
                    source_text=lines[min(1, len(lines) - 1)][:300],
                )
            ]
        )
        terms = [
            Term(
                category=category,
                summary=f"{category.replace('_', ' ').title()} clause",  # type: ignore[arg-type]
                source_text=quote,
            )
            for cue, category in _TERM_CUES
            if (quote := _sentence_with(contract_text, cue))
        ]
        key_dates = [
            KeyDate(label=label, date=value, source_text=_date_quote(contract_text, value))
            for label, value in (("Start", start), ("End", end))
            if value is not None
        ]
        data = ContractExtraction(
            title=title,
            summary=f"{title} between {' and '.join(names) or 'the parties'}.",
            parties=parties,
            start_date=start,
            end_date=end,
            key_dates=key_dates,
            terms=terms,
            risks=risks,
        )
        return ExtractionResult(data=data, model=self.model)


def _date_quote(text: str, value: date) -> str:
    return f"{value.day} {value:%B %Y}" if f"{value.day} {value:%B %Y}" in text else text[:40]
