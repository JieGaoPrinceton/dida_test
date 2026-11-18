from typing import Any

from elasticsearch import AsyncElasticsearch

from src.config import settings

es_client = AsyncElasticsearch(hosts=settings.es_hosts)

EMAIL_INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 5,
        "number_of_replicas": 1,
    },
    "mappings": {
        "properties": {
            "email_id": {"type": "long"},
            "subject": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "fields": {"en": {"type": "text", "analyzer": "standard"}},
            },
            "body_text": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "fields": {"en": {"type": "text", "analyzer": "standard"}},
            },
            "sender": {"type": "keyword"},
            "category": {"type": "keyword"},
            "subcategory": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "sent_at": {"type": "date"},
            "language": {"type": "keyword"},
            "quality_score": {"type": "float"},
            "suggest": {
                "type": "completion",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
            },
        }
    },
}

KNOWLEDGE_INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
    },
    "mappings": {
        "properties": {
            "knowledge_id": {"type": "long"},
            "question": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "fields": {"en": {"type": "text", "analyzer": "standard"}},
            },
            "answer": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
                "fields": {"en": {"type": "text", "analyzer": "standard"}},
            },
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "quality_score": {"type": "float"},
            "usage_count": {"type": "integer"},
            "suggest": {
                "type": "completion",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
            },
        }
    },
}


async def ensure_indices():
    for index_name, body in [
        (settings.es_email_index, EMAIL_INDEX_SETTINGS),
        (settings.es_knowledge_index, KNOWLEDGE_INDEX_SETTINGS),
    ]:
        if not await es_client.indices.exists(index=index_name):
            await es_client.indices.create(index=index_name, body=body)


async def bulk_index_emails(docs: list[dict]) -> dict:
    actions = []
    for doc in docs:
        actions.append({"index": {"_index": settings.es_email_index}})
        actions.append(doc)
    if actions:
        return await es_client.bulk(body=actions, refresh="wait_for")
    return {}


async def bulk_index_knowledge(docs: list[dict]) -> dict:
    actions = []
    for doc in docs:
        actions.append({"index": {"_index": settings.es_knowledge_index}})
        actions.append(doc)
    if actions:
        return await es_client.bulk(body=actions, refresh="wait_for")
    return {}


async def search_emails_bm25(
    query: str,
    category: str | None = None,
    tags: list[str] | None = None,
    top_n: int | None = None,
) -> list[dict]:
    top_n = top_n or settings.search_bm25_top_n
    must: list[dict[str, Any]] = [
        {
            "multi_match": {
                "query": query,
                "fields": ["subject^3", "subject.en^2", "body_text", "body_text.en"],
                "type": "best_fields",
            }
        }
    ]
    body: dict[str, Any] = {
        "query": {"bool": {"must": must, "filter": _build_filters(category, tags)}},
        "size": top_n,
        "_source": ["email_id", "subject", "body_text", "category", "tags", "quality_score"],
    }
    resp = await es_client.search(index=settings.es_email_index, body=body)
    return _extract_hits(resp)


async def search_knowledge_bm25(
    query: str,
    category: str | None = None,
    tags: list[str] | None = None,
    top_n: int | None = None,
) -> list[dict]:
    top_n = top_n or settings.search_knowledge_top_n
    must: list[dict[str, Any]] = [
        {
            "multi_match": {
                "query": query,
                "fields": ["question^3", "question.en^2", "answer", "answer.en"],
                "type": "best_fields",
            }
        }
    ]
    body: dict[str, Any] = {
        "query": {"bool": {"must": must, "filter": _build_filters(category, tags)}},
        "size": top_n,
        "_source": [
            "knowledge_id", "question", "answer", "category", "tags", "quality_score",
        ],
    }
    resp = await es_client.search(index=settings.es_knowledge_index, body=body)
    return _extract_hits(resp)


async def search_by_category(
    query: str,
    category: str,
    top_n: int | None = None,
) -> list[dict]:
    top_n = top_n or settings.search_category_top_n
    body: dict[str, Any] = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "subject^3", "subject.en^2", "body_text", "body_text.en",
                            ],
                        }
                    }
                ],
                "filter": [{"term": {"category": category}}],
            }
        },
        "size": top_n,
        "_source": ["email_id", "subject", "body_text", "category", "tags", "quality_score"],
    }
    resp = await es_client.search(index=settings.es_email_index, body=body)
    return _extract_hits(resp)


async def suggest(prefix: str, limit: int = 10) -> list[str]:
    suggestions: set[str] = set()
    for index_name in [settings.es_email_index, settings.es_knowledge_index]:
        body = {
            "suggest": {
                "kb-suggest": {
                    "prefix": prefix,
                    "completion": {"field": "suggest", "size": limit},
                }
            }
        }
        resp = await es_client.search(index=index_name, body=body)
        for option in (
            resp.get("suggest", {}).get("kb-suggest", [{}])[0].get("options", [])
        ):
            suggestions.add(option["text"])
    return sorted(suggestions)[:limit]


def _build_filters(
    category: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    filters: list[dict] = []
    if category:
        filters.append({"term": {"category": category}})
    if tags:
        filters.append({"terms": {"tags": tags}})
    return filters


def _extract_hits(resp: dict) -> list[dict]:
    results = []
    for hit in resp.get("hits", {}).get("hits", []):
        item = hit["_source"]
        item["_score"] = hit["_score"]
        results.append(item)
    return results
