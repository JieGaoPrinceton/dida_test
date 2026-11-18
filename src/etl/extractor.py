import json
import logging

import anthropic

from src.config import settings

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a knowledge extraction assistant. Given an email conversation, extract question-answer pairs that could be useful for a customer service knowledge base.

Subject: {subject}

Email body:
{body}

{reply_section}

Extract all meaningful Q&A pairs from this conversation. Return a JSON array where each element has:
- "question": the customer's question or issue (rewritten clearly)
- "answer": the resolution or answer provided

Return ONLY the JSON array, no other text. If no Q&A pairs can be extracted, return [].
"""


async def extract_qa_pairs(
    subject: str,
    body: str,
    reply_body: str | None = None,
) -> list[dict]:
    if not settings.anthropic_api_key:
        logger.warning("No Anthropic API key configured, skipping QA extraction")
        return []

    reply_section = ""
    if reply_body:
        reply_section = f"Reply/Resolution:\n{reply_body}"

    prompt = EXTRACT_PROMPT.format(
        subject=subject,
        body=body,
        reply_section=reply_section,
    )

    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model=settings.llm_model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        pairs = json.loads(response_text)
        if not isinstance(pairs, list):
            return []
        return [p for p in pairs if isinstance(p, dict) and "question" in p and "answer" in p]
    except Exception:
        logger.exception("Failed to extract QA pairs")
        return []
