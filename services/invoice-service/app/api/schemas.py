import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Rejection(BaseModel):
    row: int
    invoice_number: str | None
    reason: str


class Overwrite(BaseModel):
    row: int
    replaced_row: int
    invoice_number: str


class UploadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    uploaded_at: datetime
    status: Literal["completed", "no_valid_rows"]
    rows_total: int
    rows_created: int
    rows_updated: int
    rows_overwritten: int
    rows_rejected: int


class UploadSummary(UploadListItem):
    rejections: list[Rejection]
    overwrites: list[Overwrite]


class UploadPage(BaseModel):
    items: list[UploadListItem]
    total: int
    page: int
    page_size: int
