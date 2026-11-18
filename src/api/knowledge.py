from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.knowledge import KnowledgeCreate, KnowledgeResponse
from src.services.knowledge_service import create_knowledge, get_knowledge, search_knowledge

router = APIRouter()


@router.post("/", response_model=KnowledgeResponse, status_code=201)
async def create_entry(data: KnowledgeCreate, db: AsyncSession = Depends(get_db)):
    entry = await create_knowledge(db, data)
    return entry


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def read_entry(knowledge_id: int, db: AsyncSession = Depends(get_db)):
    entry = await get_knowledge(db, knowledge_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.get("/", response_model=list[KnowledgeResponse])
async def list_entries(
    category: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await search_knowledge(db, category=category, limit=limit)
