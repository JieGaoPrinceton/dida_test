from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.email import EmailResponse, EmailThread
from src.services.email_service import get_email, get_email_thread

router = APIRouter()


@router.get("/{email_id}", response_model=EmailResponse)
async def read_email(email_id: int, db: AsyncSession = Depends(get_db)):
    email = await get_email(db, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@router.get("/{email_id}/thread", response_model=EmailThread)
async def read_email_thread(email_id: int, db: AsyncSession = Depends(get_db)):
    email = await get_email(db, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if not email.thread_id:
        return EmailThread(thread_id=str(email_id), emails=[EmailResponse.model_validate(email)])
    emails = await get_email_thread(db, email.thread_id)
    return EmailThread(
        thread_id=email.thread_id,
        emails=[EmailResponse.model_validate(e) for e in emails],
    )
