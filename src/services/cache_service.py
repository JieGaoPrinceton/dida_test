import hashlib
import json

from redis.asyncio import Redis

from src.config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

_SEARCH_CACHE_PREFIX = "search:"
_HOT_KNOWLEDGE_KEY = "hot_knowledge"


async def get_cached_search(query_hash: str) -> dict | None:
    raw = await redis_client.get(f"{_SEARCH_CACHE_PREFIX}{query_hash}")
    if raw:
        return json.loads(raw)
    return None


async def set_cached_search(
    query_hash: str,
    results: dict,
    ttl: int | None = None,
) -> None:
    ttl = ttl or settings.cache_ttl_seconds
    await redis_client.set(
        f"{_SEARCH_CACHE_PREFIX}{query_hash}",
        json.dumps(results, ensure_ascii=False, default=str),
        ex=ttl,
    )


async def get_hot_knowledge(limit: int = 10) -> list[dict]:
    items = await redis_client.zrevrange(_HOT_KNOWLEDGE_KEY, 0, limit - 1, withscores=True)
    results = []
    for member, score in items:
        try:
            entry = json.loads(member)
            entry["_score"] = score
            results.append(entry)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


async def update_hot_knowledge(knowledge_id: int, score: float) -> None:
    await redis_client.zincrby(_HOT_KNOWLEDGE_KEY, score, str(knowledge_id))


async def invalidate_search_cache() -> None:
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor, match=f"{_SEARCH_CACHE_PREFIX}*", count=100
        )
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break


def compute_query_hash(
    query: str,
    category: str | None = None,
    tags: list[str] | None = None,
) -> str:
    normalized = {
        "q": query.strip().lower(),
        "c": category or "",
        "t": sorted(tags) if tags else [],
    }
    raw = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
