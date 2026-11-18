from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://email_kb:email_kb_dev@localhost:5432/email_kb"
    database_url_sync: str = "postgresql://email_kb:email_kb_dev@localhost:5432/email_kb"

    es_hosts: list[str] = ["http://localhost:9200"]
    es_email_index: str = "email_index"
    es_knowledge_index: str = "knowledge_index"

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    celery_broker_url: str = "amqp://email_kb:email_kb_dev@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    reranker_max_candidates: int = 30
    reranker_top_k: int = 10

    search_bm25_top_n: int = 50
    search_category_top_n: int = 30
    search_knowledge_top_n: int = 20

    ingest_batch_size: int = 1000

    model_config = {"env_prefix": "EMAIL_KB_", "env_file": ".env"}


settings = Settings()
