from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_search(client):
    mock_response = {
        "query": "退款流程",
        "results": [],
        "generated_answer": None,
        "total_candidates": 0,
        "response_time_ms": 5,
    }
    with patch("src.api.search.search_service.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response
        resp = await client.post("/api/v1/search", json={"query": "退款流程"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "退款流程"
    assert isinstance(data["results"], list)


@pytest.mark.asyncio
async def test_search_suggest(client):
    with patch("src.api.search.es_service.suggest", new_callable=AsyncMock) as mock_suggest:
        mock_suggest.return_value = ["退款", "退货"]
        resp = await client.post("/api/v1/search/suggest", json={"prefix": "退"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ingest_single_email(client):
    email_data = {
        "subject": "关于订单退款的问题",
        "body_text": "您好，我想咨询一下订单退款流程。",
        "sender": "customer@example.com",
        "category": "订单问题",
    }
    with (
        patch("src.api.ingest.get_db") as mock_get_db,
        patch("src.api.ingest.email_service.create_email", new_callable=AsyncMock) as mock_create,
        patch("src.api.ingest.indexer.index_email", new_callable=AsyncMock),
    ):
        mock_db = AsyncMock()
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_db]))
        mock_email = AsyncMock()
        mock_email.id = 1
        mock_email.message_id = None
        mock_email.subject = email_data["subject"]
        mock_email.sender = email_data["sender"]
        mock_email.recipients = None
        mock_email.body_text = email_data["body_text"]
        mock_email.body_html = None
        mock_email.sent_at = None
        mock_email.received_at = None
        mock_email.thread_id = None
        mock_email.in_reply_to = None
        mock_email.headers = None
        mock_email.attachments = None
        mock_email.category = email_data["category"]
        mock_email.subcategory = None
        mock_email.tags = None
        mock_email.priority = 0
        mock_email.language = "zh"
        mock_email.created_at = "2024-01-01T00:00:00"
        mock_create.return_value = mock_email
        resp = await client.post("/api/v1/ingest/email", json=email_data)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_feedback(client):
    feedback_data = {
        "query_log_id": 1,
        "selected_id": 42,
        "feedback": 1,
    }
    with patch("src.api.feedback.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_db]))
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        resp = await client.post("/api/v1/feedback", json=feedback_data)
    assert resp.status_code == 200
