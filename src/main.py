from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api import emails, feedback, ingest, knowledge, search
from src.db.database import engine
from src.services.cache_service import redis_client
from src.services.es_service import es_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()
    await es_client.close()
    await redis_client.aclose()


app = FastAPI(
    title="Email Knowledge Base",
    description="千万级邮件知识库客服系统 - 基于BM25全文检索 + LLM重排序",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(emails.router, prefix="/api/v1/emails", tags=["emails"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["ingest"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
