"""LLM provider wrapper using LiteLLM."""

from __future__ import annotations

import time
from dataclasses import dataclass

import litellm

from eval.config import MODELS

litellm.suppress_debug_info = True

# Models that support extended thinking (adaptive reasoning)
THINKING_MODELS = {"opus-4.6", "sonnet-4.6"}
DEFAULT_THINKING_BUDGET = 10000


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


async def call_llm(
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    *,
    thinking_budget: int | None = None,
) -> LLMResponse:
    """Call an LLM via LiteLLM and return standardized response.

    Args:
        model: Model alias from config.MODELS (e.g. "haiku-4.5")
        system_prompt: System prompt text
        user_message: User message text
        max_tokens: Max output tokens
        thinking_budget: Token budget for extended thinking (auto-set for thinking models)
    """
    model_id = MODELS[model]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    kwargs: dict = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
    }

    if model in THINKING_MODELS:
        budget = thinking_budget or DEFAULT_THINKING_BUDGET
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
        # Thinking models don't accept temperature
    else:
        kwargs["temperature"] = 0.1

    start = time.perf_counter()
    response = await litellm.acompletion(**kwargs)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    content = response.choices[0].message.content or ""
    cost = response._hidden_params.get("response_cost", 0.0) or 0.0

    return LLMResponse(
        content=content,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        cost_usd=cost,
        latency_ms=elapsed_ms,
    )
