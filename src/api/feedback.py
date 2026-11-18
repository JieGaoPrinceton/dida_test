from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import QueryLog
from src.models.knowledge import FeedbackRequest

router = APIRouter()


@router.post("/", status_code=200)
async def submit_feedback(req: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(QueryLog)
        .where(QueryLog.id == req.query_log_id)
        .values(selected_id=req.selected_id, feedback=req.feedback)
    )
    await db.commit()
    return {"status": "ok"}
