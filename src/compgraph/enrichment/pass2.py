"""Pass 2 enrichment — Sonnet entity extraction."""

from __future__ import annotations

import uuid

import anthropic

from compgraph.config import settings
from compgraph.enrichment.prompts import PASS2_SYSTEM_PROMPT, build_pass2_messages
from compgraph.enrichment.retry import LLMCallResult, call_llm
from compgraph.enrichment.schemas import Pass2Result


async def enrich_posting_pass2(
    client: anthropic.AsyncAnthropic,
    posting_id: uuid.UUID,
    title: str,
    location: str,
    content_role_specific: str | None,
    full_text: str,
) -> LLMCallResult[Pass2Result]:
    messages = build_pass2_messages(title, location, content_role_specific, full_text)

    return await call_llm(
        client,
        posting_id=posting_id,
        model=settings.ENRICHMENT_MODEL_PASS2,
        max_tokens=1024,
        system_prompt=PASS2_SYSTEM_PROMPT,
        messages=messages,
        result_type=Pass2Result,
        pass_label="Pass 2",  # noqa: S106
    )
