"""PDF / DOCX → plain text (CON-001 design "Text extraction"). Runs in a worker thread."""

from dataclasses import dataclass
from pathlib import Path

import docx
import pdfplumber
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.domain.file_types import FileType

MIN_VISIBLE_CHARS = 200
MAX_TEXT_CHARS = 500_000

NO_TEXT_MESSAGE = (
    "This file looks like a scanned image. Please upload a text-based PDF or Word document."
)


class TextExtractionError(Exception):
    """A document problem the user can act on; `message` is shown to them as-is."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ExtractedText:
    text: str
    pages: int | None
    # Non-whitespace characters from the document itself (page markers excluded).
    visible_chars: int


def _visible(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def _pdf_text(path: Path) -> ExtractedText:
    try:
        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:  # pdfminer raises many types; classify for the user
        if "password" in f"{type(exc).__name__} {exc}".lower():
            raise TextExtractionError(
                "FILE_PROTECTED",
                "This PDF is password-protected. Please remove the password and upload it again.",
            ) from exc
        raise TextExtractionError(
            "UNREADABLE",
            "We couldn't open this PDF. It may be damaged. Please try saving it again.",
        ) from exc
    text = "".join(f"\n\n[Page {number}]\n\n{content}" for number, content in enumerate(pages, 1))
    return ExtractedText(text.strip(), len(pages), sum(_visible(page) for page in pages))


def _docx_text(path: Path) -> ExtractedText:
    try:
        document = docx.Document(str(path))
    except Exception as exc:
        raise TextExtractionError(
            "UNREADABLE",
            "We couldn't open this Word file. It may be damaged. Please try saving it again.",
        ) from exc
    parts: list[str] = []
    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            if block.text.strip():
                parts.append(block.text)
        elif isinstance(block, Table):
            for row in block.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" · ".join(cells))
    text = "\n".join(parts)
    return ExtractedText(text, None, _visible(text))


def extract_text(path: Path, file_type: FileType) -> ExtractedText:
    extracted = _pdf_text(path) if file_type == "pdf" else _docx_text(path)
    if extracted.visible_chars < MIN_VISIBLE_CHARS:
        raise TextExtractionError("NO_TEXT", NO_TEXT_MESSAGE)
    if len(extracted.text) > MAX_TEXT_CHARS:
        raise TextExtractionError(
            "TOO_LONG",
            "This contract is too long to read automatically (over about 300 pages).",
        )
    return extracted
