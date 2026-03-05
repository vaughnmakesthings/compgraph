from __future__ import annotations

MODELS: dict[str, str] = {
    "haiku-4.5": "claude-haiku-4-5-20251001",
    "sonnet-4.5": "claude-sonnet-4-5-20251001",
    "sonnet-4.6": "claude-sonnet-4-6",
    "opus-4.6": "claude-opus-4-6",
}

SUPPORTED_MODELS: list[dict[str, str]] = [
    {"id": "claude-haiku-4-5-20251001", "label": "Haiku 4.5 (fast, cheap)"},
    {"id": "claude-sonnet-4-5-20251001", "label": "Sonnet 4.5 (balanced)"},
    {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6 (latest)"},
    {"id": "claude-opus-4-6", "label": "Opus 4.6 (highest quality)"},
    {"id": "openrouter/anthropic/claude-haiku-4-5", "label": "OpenRouter: Haiku 4.5"},
    {"id": "openrouter/anthropic/claude-sonnet-4-5", "label": "OpenRouter: Sonnet 4.5"},
    {"id": "openrouter/anthropic/claude-sonnet-4-6", "label": "OpenRouter: Sonnet 4.6"},
    {"id": "openrouter/anthropic/claude-opus-4-6", "label": "OpenRouter: Opus 4.6"},
    {"id": "openrouter/openai/gpt-4o-mini", "label": "OpenRouter: GPT-4o Mini"},
    {"id": "openrouter/openai/gpt-4o", "label": "OpenRouter: GPT-4o"},
    {"id": "openrouter/openai/gpt-4.1-mini", "label": "OpenRouter: GPT-4.1 Mini"},
    {"id": "openrouter/openai/gpt-4.1", "label": "OpenRouter: GPT-4.1"},
    {"id": "openrouter/google/gemini-2.0-flash-001", "label": "OpenRouter: Gemini 2.0 Flash"},
    {"id": "openrouter/google/gemini-2.5-pro-preview", "label": "OpenRouter: Gemini 2.5 Pro"},
    {"id": "openrouter/deepseek/deepseek-chat-v3-0324", "label": "OpenRouter: DeepSeek V3"},
    {"id": "openrouter/deepseek/deepseek-r1", "label": "OpenRouter: DeepSeek R1"},
]

SUPPORTED_MODEL_IDS: set[str] = {m["id"] for m in SUPPORTED_MODELS}
