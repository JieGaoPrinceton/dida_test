from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.cache_service import compute_query_hash


class TestCacheService:
    def test_compute_query_hash_consistent(self):
        h1 = compute_query_hash("退款", None, None)
        h2 = compute_query_hash("退款", None, None)
        assert h1 == h2

    def test_compute_query_hash_different_queries(self):
        h1 = compute_query_hash("退款", None, None)
        h2 = compute_query_hash("登录", None, None)
        assert h1 != h2

    def test_compute_query_hash_with_category(self):
        h1 = compute_query_hash("退款", "订单问题", None)
        h2 = compute_query_hash("退款", None, None)
        assert h1 != h2

    def test_compute_query_hash_with_tags(self):
        h1 = compute_query_hash("退款", None, ["urgent"])
        h2 = compute_query_hash("退款", None, None)
        assert h1 != h2

    def test_compute_query_hash_tag_order_insensitive(self):
        h1 = compute_query_hash("退款", None, ["a", "b"])
        h2 = compute_query_hash("退款", None, ["b", "a"])
        assert h1 == h2


@pytest.mark.asyncio
async def test_search_service_pipeline():
    with (
        patch("src.services.search_service.cache_service") as mock_cache,
        patch("src.services.search_service.es_service") as mock_es,
        patch("src.services.search_service.reranker") as mock_reranker,
    ):
        mock_cache.compute_query_hash = MagicMock(return_value="abc123")
        mock_cache.get_cached_search = AsyncMock(return_value=None)
        mock_cache.set_cached_search = AsyncMock()
        mock_cache.get_hot_knowledge = AsyncMock(return_value=[])

        mock_es.search_emails_bm25 = AsyncMock(
            return_value=[
                {
                    "email_id": 1,
                    "subject": "退款流程说明",
                    "body_text": "退款需要3-5个工作日...",
                    "category": "订单问题",
                    "tags": ["退款"],
                    "_score": 5.0,
                }
            ]
        )
        mock_es.search_knowledge_bm25 = AsyncMock(return_value=[])
        mock_es.search_by_category = AsyncMock(return_value=[])

        mock_reranker.rerank_results = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "source": "email",
                    "title": "退款流程说明",
                    "snippet": "退款需要3-5个工作日...",
                    "score": 9.0,
                    "category": "订单问题",
                    "tags": ["退款"],
                }
            ]
        )
        mock_reranker.generate_answer = AsyncMock(return_value="退款一般需要3-5个工作日处理。")

        from src.models.knowledge import SearchRequest
        from src.services.search_service import search

        request = SearchRequest(query="退款流程", use_reranker=True)
        result = await search(request)

        assert result.query == "退款流程"
        assert isinstance(result.results, list)
        mock_es.search_emails_bm25.assert_awaited_once()
        mock_es.search_knowledge_bm25.assert_awaited_once()


@pytest.mark.asyncio
async def test_reranker_mock():
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '[{"id": 1, "score": 9}, {"id": 2, "score": 7}]'

    with patch("src.services.reranker.anthropic") as mock_anthropic_mod:
        mock_client = AsyncMock()
        mock_anthropic_mod.AsyncAnthropic.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        from src.services.reranker import rerank_results

        candidates = [
            {"id": 2, "source": "email", "title": "B", "snippet": "bbb", "score": 3.0},
            {"id": 1, "source": "email", "title": "A", "snippet": "aaa", "score": 5.0},
        ]
        result = await rerank_results("退款", candidates, top_k=2)
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_reranker_fallback_on_error():
    with patch("src.services.reranker.anthropic") as mock_anthropic_mod:
        mock_client = AsyncMock()
        mock_anthropic_mod.AsyncAnthropic.return_value = mock_client
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

        from src.services.reranker import rerank_results

        candidates = [
            {"id": 1, "source": "email", "title": "A", "snippet": "aaa", "score": 5.0},
        ]
        result = await rerank_results("test", candidates, top_k=1)
        assert len(result) == 1
        assert result[0]["id"] == 1
