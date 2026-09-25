"""Checks that the AI's quotes really appear in the document (CON-001 AC10, CON-002 AC6)."""

import re

_TRANSLATE = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‚": "'",
        "′": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "″": '"',
        "–": "-",
        "—": "-",
        "−": "-",
        " ": " ",
    }
)
_SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Lower-case, ASCII quotes and dashes, single spaces: formatting doesn't break a match."""
    return _SPACE.sub(" ", text.translate(_TRANSLATE)).strip().lower()


class QuoteChecker:
    def __init__(self, document_text: str) -> None:
        self._document = normalise(document_text)

    def verified(self, quote: str) -> bool:
        needle = normalise(quote).strip(" \"'.")
        return bool(needle) and needle in self._document
