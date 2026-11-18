from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Email
from src.models.email import EmailCreate


async def get_email(db: AsyncSession, email_id: int) -> Email | None:
    return await db.get(Email, email_id)


async def get_email_thread(db: AsyncSession, thread_id: str) -> list[Email]:
    result = await db.execute(
        select(Email)
        .where(Email.thread_id == thread_id)
        .order_by(Email.sent_at.asc())
    )
    return list(result.scalars().all())


async def create_email(db: AsyncSession, email_data: EmailCreate) -> Email:
    email = Email(**email_data.model_dump())
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return email


async def bulk_create_emails(
    db: AsyncSession,
    emails: list[EmailCreate],
) -> list[int]:
    db_emails = [Email(**e.model_dump()) for e in emails]
    db.add_all(db_emails)
    await db.commit()
    for e in db_emails:
        await db.refresh(e)
    return [e.id for e in db_emails]
