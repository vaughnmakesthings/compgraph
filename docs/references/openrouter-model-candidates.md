# OpenRouter Model Candidates for CompGraph Enrichment

> Research date: 2026-02-20
> Source: OpenRouter API `/api/v1/models` endpoint

## Context

CompGraph's 2-pass enrichment pipeline needs cost-effective LLM models:
- **Pass 1** (Haiku-class): Classification, pay extraction, structured JSON — needs to be cheap
- **Pass 2** (Sonnet-class): Entity extraction, brand/retailer identification — needs more capability

Current production: Haiku 4.5 (Pass 1), Sonnet 4.5 (Pass 2) via direct Anthropic API.
Eval tool (`compgraph-eval`) routes through OpenRouter for multi-provider comparison.

## Current Eval Config (13 models)

| Alias | OpenRouter ID | $/M Input | $/M Output |
|-------|---------------|-----------|------------|
| haiku-3.5 | anthropic/claude-3.5-haiku | $0.80 | $4.00 |
| sonnet-3.5 | anthropic/claude-3.5-sonnet | $3.00 | $15.00 |
| sonnet-4 | anthropic/claude-sonnet-4 | $3.00 | $15.00 |
| haiku-4.5 | anthropic/claude-haiku-4-5 | $0.80 | $4.00 |
| sonnet-4.5 | anthropic/claude-sonnet-4-5 | $3.00 | $15.00 |
| gpt-4o-mini | openai/gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | openai/gpt-4o | $2.50 | $10.00 |
| gpt-4.1-mini | openai/gpt-4.1-mini | $0.40 | $1.60 |
| gpt-4.1 | openai/gpt-4.1 | $1.00 | $4.00 |
| gemini-flash | google/gemini-2.0-flash-001 | $0.10 | $0.40 |
| gemini-pro | google/gemini-2.5-pro-preview | $1.25 | $10.00 |
| deepseek-v3 | deepseek/deepseek-chat-v3-0324 | $0.27 | $1.10 |
| deepseek-r1 | deepseek/deepseek-r1 | $0.55 | $2.19 |

## Recommended Additions

### Ultra-Cheap Tier (Pass 1 candidates)

| Model | Provider | $/M Input | $/M Output | Context | Tools |
|-------|----------|-----------|------------|---------|-------|
| GLM-4.7-Flash | Zhipu | $0.06 | $0.40 | 202k | yes |
| Seed 1.6 Flash | ByteDance | $0.075 | $0.30 | 262k | yes |
| MiMo-V2-Flash | Xiaomi | $0.09 | $0.29 | 262k | yes |
| Step 3.5 Flash | StepFun | $0.10 | $0.30 | 256k | yes |
| Qwen 3.5 397B MoE | Alibaba | $0.15 | $1.00 | 262k | yes |
| Ministral 3 14B | Mistral | $0.20 | $0.20 | 262k | yes |
| Ministral 3 8B | Mistral | $0.15 | $0.15 | 262k | yes |
| Grok 4.1 Fast | xAI | $0.20 | $0.50 | 2M | yes |
| DeepSeek V3.2 | DeepSeek | $0.26 | $0.38 | 163k | yes |

### Mid-Tier (Pass 2 candidates)

| Model | Provider | $/M Input | $/M Output | Context | Tools |
|-------|----------|-----------|------------|---------|-------|
| Gemini 3 Flash | Google | $0.50 | $3.00 | 1M | yes |
| Mistral Large 3 | Mistral | $0.50 | $1.50 | 262k | yes |
| Qwen 3.5 Plus | Alibaba | $0.40 | $2.40 | 1M | yes |
| MiniMax M2.5 | MiniMax | $0.30 | $1.10 | 196k | yes |
| Kimi K2.5 | Moonshot | $0.23 | $3.00 | 262k | yes |

### Frontier (quality benchmarking)

| Model | Provider | $/M Input | $/M Output | Context | Tools |
|-------|----------|-----------|------------|---------|-------|
| GPT-5.1 | OpenAI | $1.25 | $10.00 | 400k | yes |
| Gemini 3 Pro | Google | $2.00 | $12.00 | 1M | yes |
| Claude Sonnet 4.6 | Anthropic | $3.00 | $15.00 | 1M | yes |

## Cost Projections

Per 1,000 postings (Pass 1, ~1,500 input + ~500 output tokens each):

| Model | Estimated Cost | vs Haiku 3.5 |
|-------|---------------|--------------|
| GLM-4.7-Flash | $0.29 | **13x cheaper** |
| Seed 1.6 Flash | $0.26 | **15x cheaper** |
| gemini-flash (2.0) | $0.35 | 11x cheaper |
| Ministral 3 8B | $0.30 | 13x cheaper |
| DeepSeek V3.2 | $0.58 | 7x cheaper |
| haiku-3.5 (baseline) | $3.80 | — |
| gpt-4.1-mini | $1.40 | 3x cheaper |

## Open Questions

- Model ID slugs need verification against OpenRouter's actual API routing
- Chinese-origin model quality on English job posting extraction is untested
- Rate limits per model on OpenRouter may affect batch throughput
- Some newer models may have inconsistent structured output adherence

## Sources

- [OpenRouter Models](https://openrouter.ai/models)
- [OpenRouter Pricing](https://openrouter.ai/pricing)
- [TeamDay Best Models Feb 2026](https://www.teamday.ai/blog/top-ai-models-openrouter-2026)
