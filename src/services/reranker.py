import json
import logging

import anthropic

from src.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def rerank_results(
    query: str,
    candidates: list[dict],
    top_k: int | None = None,
) -> list[dict]:
    top_k = top_k or settings.reranker_top_k
    if not candidates:
        return []

    truncated = candidates[: settings.reranker_max_candidates]

    numbered_list = []
    for i, c in enumerate(truncated):
        title = c.get("title") or c.get("subject") or c.get("question") or ""
        snippet = c.get("snippet") or c.get("body_text") or c.get("answer") or ""
        snippet = snippet[:300]
        numbered_list.append(f"[{i}] {title}\n{snippet}")

    prompt = (
        f"Given the customer query: \"{query}\"\n\n"
        "Rate each of the following excerpts on relevance to the query (0-10 scale).\n"
        "Return ONLY a JSON array of [index, score] pairs, e.g. [[0, 8], [1, 3], ...].\n"
        "No explanation, just the JSON array.\n\n"
        "Excerpts:\n" + "\n\n".join(numbered_list)
    )

    try:
        client = _get_client()
        message = await client.messages.create(
            model=settings.llm_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        scores = json.loads(text)
        score_map = {int(idx): float(score) for idx, score in scores}

        for i, c in enumerate(truncated):
            if i in score_map:
                c["_rerank_score"] = score_map[i]
            else:
                c["_rerank_score"] = 0.0

        truncated.sort(key=lambda x: x.get("_rerank_score", 0), reverse=True)
        return truncated[:top_k]

    except Exception:
        logger.exception("LLM reranking failed, returning original order")
        return truncated[:top_k]


async def generate_answer(query: str, top_results: list[dict]) -> str:
    if not top_results:
        return ""

    context_parts = []
    for i, r in enumerate(top_results[:5]):
        title = r.get("title") or r.get("subject") or r.get("question") or ""
        content = r.get("snippet") or r.get("body_text") or r.get("answer") or ""
        source_id = r.get("id") or r.get("email_id") or r.get("knowledge_id") or i
        context_parts.append(f"[Source {source_id}] {title}\n{content[:500]}")

    prompt = (
        f"Based on the following knowledge base entries, answer the customer query.\n\n"
        f"Query: \"{query}\"\n\n"
        "Knowledge base entries:\n" + "\n\n---\n\n".join(context_parts) + "\n\n"
        "Provide a helpful, concise answer. Cite sources using [Source ID] format. "
        "If the entries don't contain enough information, say so."
    )

    try:
        client = _get_client()
        message = await client.messages.create(
            model=settings.llm_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception:
        logger.exception("Answer generation failed")
        return ""
