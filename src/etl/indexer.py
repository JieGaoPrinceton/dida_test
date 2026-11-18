from src.db.models import Email, KnowledgeEntry
from src.services.es_service import bulk_index_emails, bulk_index_knowledge


def email_to_es_doc(email: Email) -> dict:
    doc = {
        "email_id": email.id,
        "subject": email.subject or "",
        "body_text": email.body_text or "",
        "sender": email.sender,
        "category": email.category,
        "subcategory": email.subcategory,
        "tags": email.tags or [],
        "sent_at": email.sent_at.isoformat() if email.sent_at else None,
        "language": email.language,
        "quality_score": 0.0,
    }
    suggest_input = []
    if email.subject:
        suggest_input.append(email.subject)
    if email.tags:
        suggest_input.extend(email.tags)
    if suggest_input:
        doc["suggest"] = {"input": suggest_input}
    return doc


def knowledge_to_es_doc(entry: KnowledgeEntry) -> dict:
    doc = {
        "knowledge_id": entry.id,
        "question": entry.question or "",
        "answer": entry.answer or "",
        "category": entry.category,
        "tags": entry.tags or [],
        "quality_score": entry.quality_score,
        "usage_count": entry.usage_count,
    }
    suggest_input = []
    if entry.question:
        suggest_input.append(entry.question)
    if entry.tags:
        suggest_input.extend(entry.tags)
    if suggest_input:
        doc["suggest"] = {"input": suggest_input}
    return doc


async def index_email(email: Email) -> None:
    doc = email_to_es_doc(email)
    await bulk_index_emails([doc])


async def index_emails_batch(emails: list[Email]) -> None:
    docs = [email_to_es_doc(e) for e in emails]
    if docs:
        await bulk_index_emails(docs)
