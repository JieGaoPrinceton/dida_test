from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import KnowledgeEntry
from src.models.knowledge import KnowledgeCreate


async def get_knowledge(db: AsyncSession, knowledge_id: int) -> KnowledgeEntry | None:
    return await db.get(KnowledgeEntry, knowledge_id)


async def create_knowledge(
    db: AsyncSession,
    data: KnowledgeCreate,
) -> KnowledgeEntry:
    entry = KnowledgeEntry(**data.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def search_knowledge(
    db: AsyncSession,
    category: str | None = None,
    limit: int = 20,
) -> list[KnowledgeEntry]:
    stmt = select(KnowledgeEntry).order_by(KnowledgeEntry.quality_score.desc())
    if category:
        stmt = stmt.where(KnowledgeEntry.category == category)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def increment_usage(db: AsyncSession, knowledge_id: int) -> None:
    await db.execute(
        update(KnowledgeEntry)
        .where(KnowledgeEntry.id == knowledge_id)
        .values(usage_count=KnowledgeEntry.usage_count + 1)
    )
    await db.commit()
