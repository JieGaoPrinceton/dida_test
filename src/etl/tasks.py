import asyncio
import logging

from celery import Celery
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.db.models import Email, KnowledgeEntry
from src.etl.cleaner import clean_email_body
from src.etl.classifier import classify_email, extract_tags
from src.etl.extractor import extract_qa_pairs
from src.etl.indexer import email_to_es_doc
from src.services.es_service import bulk_index_emails, bulk_index_knowledge

logger = logging.getLogger(__name__)

celery_app = Celery(
    "email_kb",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=4,
)


def _get_sync_session() -> Session:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    engine = create_engine(settings.database_url_sync)
    return SyncSession(engine)


@celery_app.task(bind=True, max_retries=3)
def process_email_task(self, email_id: int):
    session = _get_sync_session()
    try:
        email = session.get(Email, email_id)
        if not email:
            logger.warning("Email %d not found", email_id)
            return

        if email.body_text:
            email.body_text = clean_email_body(email.body_text)

        if not email.category and email.subject and email.body_text:
            cat, subcat = classify_email(email.subject, email.body_text)
            email.category = cat
            email.subcategory = subcat

        if not email.tags and email.subject and email.body_text:
            email.tags = extract_tags(email.subject, email.body_text)

        session.commit()

        doc = email_to_es_doc(email)
        asyncio.get_event_loop().run_until_complete(bulk_index_emails([doc]))
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to process email %d", email_id)
        raise self.retry(exc=exc, countdown=60)
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3)
def process_batch_task(self, email_ids: list[int]):
    session = _get_sync_session()
    try:
        stmt = select(Email).where(Email.id.in_(email_ids))
        emails = list(session.execute(stmt).scalars().all())

        for email in emails:
            if email.body_text:
                email.body_text = clean_email_body(email.body_text)
            if not email.category and email.subject and email.body_text:
                cat, subcat = classify_email(email.subject, email.body_text)
                email.category = cat
                email.subcategory = subcat
            if not email.tags and email.subject and email.body_text:
                email.tags = extract_tags(email.subject, email.body_text)

        session.commit()

        docs = [email_to_es_doc(e) for e in emails]
        if docs:
            asyncio.get_event_loop().run_until_complete(bulk_index_emails(docs))
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to process batch")
        raise self.retry(exc=exc, countdown=60)
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3)
def extract_knowledge_task(self, email_id: int):
    session = _get_sync_session()
    try:
        email = session.get(Email, email_id)
        if not email or not email.body_text:
            return

        reply_body = None
        if email.in_reply_to:
            parent = session.execute(
                select(Email).where(Email.message_id == email.in_reply_to)
            ).scalar_one_or_none()
            if parent:
                reply_body = email.body_text
                email = parent

        pairs = asyncio.get_event_loop().run_until_complete(
            extract_qa_pairs(email.subject or "", email.body_text, reply_body)
        )

        entries = []
        for pair in pairs:
            entry = KnowledgeEntry(
                email_id=email.id,
                question=pair["question"],
                answer=pair["answer"],
                category=email.category,
                tags=email.tags,
                quality_score=0.5,
            )
            session.add(entry)
            entries.append(entry)

        session.commit()

        if entries:
            from src.etl.indexer import knowledge_to_es_doc

            docs = [knowledge_to_es_doc(e) for e in entries]
            asyncio.get_event_loop().run_until_complete(bulk_index_knowledge(docs))
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to extract knowledge from email %d", email_id)
        raise self.retry(exc=exc, countdown=60)
    finally:
        session.close()
