from datetime import datetime

from pydantic import BaseModel, Field


class EmailBase(BaseModel):
    message_id: str | None = None
    subject: str | None = None
    sender: str | None = None
    recipients: list[dict] | None = None
    body_text: str | None = None
    body_html: str | None = None
    sent_at: datetime | None = None
    received_at: datetime | None = None
    thread_id: str | None = None
    in_reply_to: str | None = None
    headers: dict | None = None
    attachments: list[dict] | None = None
    category: str | None = None
    subcategory: str | None = None
    tags: list[str] | None = None
    priority: int = 0
    language: str = "zh"


class EmailCreate(EmailBase):
    subject: str
    body_text: str


class EmailResponse(EmailBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailBulkImport(BaseModel):
    emails: list[EmailCreate] = Field(..., min_length=1, max_length=10000)


class EmailThread(BaseModel):
    thread_id: str
    emails: list[EmailResponse]
