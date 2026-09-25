"""Upload checks for contracts (CON-001 AC3): size cap and file type by content, not extension."""

import hashlib
import zipfile
from pathlib import Path
from typing import Literal

from app.core.errors import AppError

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
FileType = Literal["pdf", "docx"]

_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # legacy .doc, or a password-protected .docx
_ENCRYPTION_STREAM = "EncryptionInfo".encode("utf-16-le")


def file_too_large() -> AppError:
    return AppError(
        "FILE_TOO_LARGE",
        "This file is larger than 20 MB. Please upload a smaller file.",
        status=413,
        details={"max_bytes": MAX_UPLOAD_BYTES},
    )


def _invalid(extra: str = "") -> AppError:
    return AppError("INVALID_FILE_TYPE", f"Please upload a PDF or Word (.docx) file.{extra}")


def detect_file_type(path: Path) -> FileType:
    with path.open("rb") as handle:
        head = handle.read(8)
    if head.startswith(_PDF_MAGIC):
        return "pdf"
    if head.startswith(_ZIP_MAGIC):
        try:
            with zipfile.ZipFile(path) as archive:
                if "word/document.xml" in archive.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            pass
        raise _invalid()
    if head.startswith(_OLE_MAGIC):
        if _ENCRYPTION_STREAM in path.read_bytes():
            raise AppError(
                "FILE_PROTECTED",
                "This file is password-protected. Please remove the password and try again.",
            )
        raise _invalid(" Older Word files (.doc) can be opened in Word and saved as .docx.")
    raise _invalid()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
