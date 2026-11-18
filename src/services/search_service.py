import asyncio
import logging
import time

from src.models.knowledge import SearchRequest, SearchResponse, SearchResult
from src.services import cache_service, es_service, reranker

logger = logging.getLogger(__name__)


async def search(request: SearchRequest) -> SearchResponse:
    start = time.monotonic()

    query_hash = cache_service.compute_query_hash(
        request.query, request.category, request.tags
    )
    cached = await cache_service.get_cached_search(query_hash)
    if cached:
        cached["response_time_ms"] = int((time.monotonic() - start) * 1000)
        return SearchResponse(**cached)

    recall_tasks = [
        es_service.search_emails_bm25(request.query, request.category, request.tags),
        es_service.search_knowledge_bm25(request.query, request.category, request.tags),
        cache_service.get_hot_knowledge(limit=10),
    ]
    if request.category:
        recall_tasks.append(
            es_service.search_by_category(request.query, request.category)
        )

    recall_results = await asyncio.gather(*recall_tasks, return_exceptions=True)

    candidates: list[dict] = []
    for result in recall_results:
        if isinstance(result, Exception):
            logger.warning("Recall channel failed: %s", result)
            continue
        if isinstance(result, list):
            candidates.extend(result)

    candidates = _merge_and_deduplicate(candidates)
    total_candidates = len(candidates)

    generated_answer: str | None = None
    if request.use_reranker and candidates:
        candidates = await reranker.rerank_results(
            request.query, candidates, top_k=request.top_k
        )
        generated_answer = await reranker.generate_answer(request.query, candidates)
    else:
        candidates = candidates[: request.top_k]

    results = [_to_search_result(c) for c in candidates]

    elapsed_ms = int((time.monotonic() - start) * 1000)
    response = SearchResponse(
        query=request.query,
        results=results,
        generated_answer=generated_answer,
        total_candidates=total_candidates,
        response_time_ms=elapsed_ms,
    )

    await cache_service.set_cached_search(query_hash, response.model_dump())

    return response


def _merge_and_deduplicate(candidates: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for c in candidates:
        source = "knowledge" if "knowledge_id" in c else "email"
        doc_id = c.get("knowledge_id") or c.get("email_id") or id(c)
        key = f"{source}:{doc_id}"
        existing = seen.get(key)
        if existing is None or c.get("_score", 0) > existing.get("_score", 0):
            c["_source_type"] = source
            c["_doc_id"] = doc_id
            seen[key] = c
    merged = sorted(seen.values(), key=lambda x: x.get("_score", 0), reverse=True)
    return merged


def _to_search_result(c: dict) -> SearchResult:
    source = c.get("_source_type", "email")
    if source == "knowledge":
        title = c.get("question", "")
        snippet = (c.get("answer") or "")[:500]
        doc_id = c.get("knowledge_id", 0)
    else:
        title = c.get("subject", "")
        snippet = (c.get("body_text") or "")[:500]
        doc_id = c.get("email_id", 0)

    return SearchResult(
        id=doc_id,
        source=source,
        title=title,
        snippet=snippet,
        score=c.get("_rerank_score", c.get("_score", 0.0)),
        category=c.get("category"),
        tags=c.get("tags"),
    )
