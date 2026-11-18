import io
import json

import pandas as pd

from src.models.email import EmailCreate

COLUMN_MAP = {
    "message_id": "message_id",
    "subject": "subject",
    "sender": "sender",
    "from": "sender",
    "body": "body_text",
    "body_text": "body_text",
    "body_html": "body_html",
    "sent_at": "sent_at",
    "received_at": "received_at",
    "thread_id": "thread_id",
    "in_reply_to": "in_reply_to",
    "category": "category",
    "subcategory": "subcategory",
    "language": "language",
}


def parse_csv(file_content: bytes) -> list[dict]:
    df = pd.read_csv(io.BytesIO(file_content), dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    mapped = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    records = mapped.to_dict(orient="records")
    for rec in records:
        for key in list(rec.keys()):
            if rec[key] == "":
                rec[key] = None
        if "tags" in rec and isinstance(rec["tags"], str):
            rec["tags"] = [t.strip() for t in rec["tags"].split(",") if t.strip()]
        if "recipients" in rec and isinstance(rec["recipients"], str):
            rec["recipients"] = [{"email": r.strip()} for r in rec["recipients"].split(",")]
    return records


def parse_json(file_content: bytes) -> list[dict]:
    data = json.loads(file_content)
    if isinstance(data, dict) and "emails" in data:
        data = data["emails"]
    if not isinstance(data, list):
        raise ValueError("JSON must be an array of email objects or {emails: [...]}")
    normalized = []
    for item in data:
        mapped = {}
        for key, value in item.items():
            norm_key = key.strip().lower().replace(" ", "_")
            target = COLUMN_MAP.get(norm_key, norm_key)
            mapped[target] = value
        normalized.append(mapped)
    return normalized


def validate_email_data(data: dict) -> EmailCreate:
    return EmailCreate.model_validate(data)
