"""Model configuration for LLM evaluation."""

MODELS: dict[str, str] = {
    # Anthropic (via OpenRouter)
    "haiku-3.5": "openrouter/anthropic/claude-3.5-haiku",
    "sonnet-3.5": "openrouter/anthropic/claude-3.5-sonnet",
    "sonnet-4": "openrouter/anthropic/claude-sonnet-4",
    "haiku-4.5": "openrouter/anthropic/claude-haiku-4-5",
    "sonnet-4.5": "openrouter/anthropic/claude-sonnet-4-5",
    "sonnet-4.6": "openrouter/anthropic/claude-sonnet-4-6",
    "opus-4.6": "openrouter/anthropic/claude-opus-4-6",
    # OpenAI (via OpenRouter)
    "gpt-4o-mini": "openrouter/openai/gpt-4o-mini",
    "gpt-4o": "openrouter/openai/gpt-4o",
    "gpt-4.1-mini": "openrouter/openai/gpt-4.1-mini",
    "gpt-4.1": "openrouter/openai/gpt-4.1",
    "o3": "openrouter/openai/o3",
    "o3-mini": "openrouter/openai/o3-mini",
    # Google (via OpenRouter)
    "gemini-flash": "openrouter/google/gemini-2.0-flash-001",
    "gemini-pro": "openrouter/google/gemini-2.5-pro-preview",
    # DeepSeek (via OpenRouter)
    "deepseek-v3": "openrouter/deepseek/deepseek-chat-v3-0324",
    "deepseek-r1": "openrouter/deepseek/deepseek-r1",
}

DEFAULT_CONCURRENCY = 5
DEFAULT_MAX_TOKENS_PASS1 = 2048
DEFAULT_MAX_TOKENS_PASS2 = 1024
