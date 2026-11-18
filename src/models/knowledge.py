from datetime import datetime

from pydantic import BaseModel


class KnowledgeBase(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    quality_score: float = 0.0


class KnowledgeCreate(KnowledgeBase):
    email_id: int | None = None
    question: str
    answer: str


class KnowledgeResponse(KnowledgeBase):
    id: int
    email_id: int | None = None
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    category: str | None = None
    tags: list[str] | None = None
    top_k: int = 10
    use_reranker: bool = True


class SearchResult(BaseModel):
    id: int
    source: str
    title: str
    snippet: str
    score: float
    category: str | None = None
    tags: list[str] | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    generated_answer: str | None = None
    total_candidates: int
    response_time_ms: int


class SuggestRequest(BaseModel):
    prefix: str
    limit: int = 10


class FeedbackRequest(BaseModel):
    query_log_id: int
    selected_id: int
    feedback: int
