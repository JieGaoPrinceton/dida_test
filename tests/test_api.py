from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_search(client):
    from src.models.knowledge import SearchResponse

    mock_response = SearchResponse(
        query="退款流程",
        results=[],
        generated_answer=None,
        total_candidates=0,
        response_time_ms=5,
    )
    with patch("src.services.search_service.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response
        resp = await client.post("/api/v1/search", json={"query": "退款流程"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "退款流程"
    assert isinstance(data["results"], list)


@pytest.mark.asyncio
async def test_search_suggest(client):
    with patch("src.api.search.suggest", new_callable=AsyncMock) as mock_suggest:
        mock_suggest.return_value = ["退款", "退货"]
        resp = await client.post("/api/v1/search/suggest", json={"prefix": "退"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_feedback(client):
    feedback_data = {
        "query_log_id": 1,
        "selected_id": 42,
        "feedback": 1,
    }
    with patch("src.api.feedback.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        async def fake_get_db():
            yield mock_db

        mock_get_db.side_effect = fake_get_db

        from src.db.database import get_db as real_get_db
        from src.main import app

        app.dependency_overrides[real_get_db] = fake_get_db
        try:
            resp = await client.post("/api/v1/feedback/", json=feedback_data)
        finally:
            app.dependency_overrides.clear()
    assert resp.status_code == 200
