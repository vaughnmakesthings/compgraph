# LiteLLM + OpenRouter: Concurrency & Resilience

Reference for batch LLM evaluation (5+ concurrent calls) via LiteLLM Router + OpenRouter. Covers retry logic, fallback chains, concurrency control, cost tracking, and known issues.

**CompGraph context:** Prompt Evaluation Tool (#128) will run 5-20 concurrent LLM calls per eval batch. LiteLLM is the planned provider abstraction (M7 Phase B). OpenRouter gives access to multiple providers (DeepInfra, Together, etc.) behind a single API.

---

## Quick Reference

| Setting | Value | Notes |
|---------|-------|-------|
| `num_retries` | `3` | Global retry count (default: 2) |
| `retry_after` | `5` | Min seconds between retries |
| `cooldown_time` | `60` | Seconds to sideline a failed deployment |
| `allowed_fails` | `3` | Fails/min before cooldown triggers |
| `timeout` | `30` | Per-request timeout (seconds) |
| Concurrency | `asyncio.Semaphore(5)` | Wrap `router.acompletion()` calls |

---

## S1 Router Setup with Fallbacks

```python
from litellm import Router
from litellm.router import RetryPolicy, AllowedFailsPolicy

model_list = [
    {
        "model_name": "eval-fast",
        "litellm_params": {
            "model": "openrouter/google/gemini-2.0-flash-001",
            "api_key": "sk-or-...",
            "rpm": 60,
        },
    },
    {
        "model_name": "eval-fast",  # same name = load-balanced
        "litellm_params": {
            "model": "openrouter/meta-llama/llama-3.3-70b-instruct",
            "api_key": "sk-or-...",
            "rpm": 60,
        },
    },
    {
        "model_name": "eval-strong",
        "litellm_params": {
            "model": "openrouter/anthropic/claude-sonnet-4",
            "api_key": "sk-or-...",
            "rpm": 20,
        },
    },
]

retry_policy = RetryPolicy(
    RateLimitErrorRetries=3,
    TimeoutErrorRetries=2,
    ContentPolicyViolationErrorRetries=0,  # don't retry content blocks
    AuthenticationErrorRetries=0,          # fail fast on bad keys
    BadRequestErrorRetries=1,
)

allowed_fails_policy = AllowedFailsPolicy(
    RateLimitErrorAllowedFails=5,    # tolerate bursts before cooldown
    ContentPolicyViolationErrorAllowedFails=1000,  # never cooldown for this
)

router = Router(
    model_list=model_list,
    fallbacks=[{"eval-fast": ["eval-strong"]}],  # fast fails -> try strong
    retry_policy=retry_policy,
    allowed_fails_policy=allowed_fails_policy,
    num_retries=3,
    retry_after=5,             # min 5s between retries
    cooldown_time=60,          # sideline failed deployment for 60s
    timeout=30,
)
```

---

## S2 Concurrent Batch Execution

LiteLLM has no built-in concurrency limiter for `acompletion`. Use `asyncio.Semaphore`.

```python
import asyncio
from litellm.types.utils import ModelResponse

CONCURRENCY = 5  # max parallel LLM calls

async def run_eval_batch(
    router: Router,
    prompts: list[list[dict]],  # list of message lists
    model: str = "eval-fast",
) -> list[ModelResponse]:
    sem = asyncio.Semaphore(CONCURRENCY)

    async def _call(messages: list[dict]) -> ModelResponse:
        async with sem:
            return await router.acompletion(
                model=model,
                messages=messages,
            )

    results = await asyncio.gather(
        *[_call(msgs) for msgs in prompts],
        return_exceptions=True,
    )
    # Separate successes from failures
    successes = [r for r in results if isinstance(r, ModelResponse)]
    failures = [r for r in results if isinstance(r, BaseException)]
    if failures:
        logger.warning("Batch had %d failures out of %d", len(failures), len(results))
    return successes
```

---

## S3 OpenRouter Error Codes

| HTTP Code | Meaning | LiteLLM Exception | Retry? |
|-----------|---------|-------------------|--------|
| 429 | Rate limited (OpenRouter or upstream) | `RateLimitError` | Yes, with backoff |
| 401 | Invalid/expired API key | `AuthenticationError` | No |
| 402 | Insufficient credits | `AuthenticationError` | No |
| 408 | Request timeout | `Timeout` | Yes |
| 502 | Provider down | `ServiceUnavailableError` | Yes (fallback) |
| 503 | No provider meets routing constraints | `ServiceUnavailableError` | Yes (fallback) |

**OpenRouter error metadata structure:**
```json
{
  "error": {
    "code": 429,
    "message": "Provider returned error",
    "metadata": {
      "provider_name": "DeepInfra",
      "raw": "model is temporarily rate-limited upstream"
    }
  }
}
```

Key distinction: OpenRouter 429 can mean **OpenRouter-level** rate limit OR **upstream provider** rate limit. The `metadata.provider_name` field tells you which. LiteLLM maps both to `RateLimitError`.

---

## S4 OpenRouter Rate Limits

| Tier | Requests/min | Requests/day | Condition |
|------|-------------|-------------|-----------|
| Free (no credits) | 20 | 50 | `:free` model variants only |
| Free (10+ credits bought) | 20 | 1,000 | `:free` model variants only |
| Paid | 1 req/credit/sec | No daily limit | Up to ~500 req/s surge |

Check limits programmatically: `GET https://openrouter.ai/api/v1/key`

---

## S5 Cost Tracking

```python
import litellm

cumulative_cost: float = 0.0

def track_cost(kwargs, completion_response, start_time, end_time):
    global cumulative_cost
    cost = kwargs.get("response_cost", 0)
    model = kwargs.get("model", "unknown")
    cumulative_cost += cost
    logger.info("model=%s cost=$%.6f cumulative=$%.4f", model, cost, cumulative_cost)

litellm.success_callback = [track_cost]

# Or use completion_cost() for ad-hoc calculation:
from litellm import completion_cost
cost = completion_cost(completion_response=response)
```

For structured tracking, subclass `litellm.integrations.custom_logger.CustomLogger` and override `log_success_event` / `log_failure_event`.

---

## S6 Gotchas & Limitations

| Issue | Impact | Mitigation |
|-------|--------|------------|
| LiteLLM doesn't always retry OpenRouter 429s ([#8448](https://github.com/BerriAI/litellm/issues/8448)) | Silent failures, empty responses | Set explicit `RetryPolicy(RateLimitErrorRetries=3)` on Router |
| Free model 429s treated as empty replies ([#9035](https://github.com/BerriAI/litellm/issues/9035)) | `RateLimitError` not raised | Avoid `:free` model variants for eval workloads |
| `retry_after` ignored in `usage-based-routing-v2` ([#7669](https://github.com/BerriAI/litellm/issues/7669)) | Immediate retry → cascading failures | Use default routing strategy, not `usage-based-routing-v2` |
| Streaming 429 not retried ([#8648](https://github.com/BerriAI/litellm/issues/8648)) | Stream fails without retry | Use non-streaming for eval (no `stream=True`) |
| Per-deployment `num_retries` ignored ([#18968](https://github.com/BerriAI/litellm/issues/18968)) | Router-level setting wins | Set retries at Router level, not per-deployment |
| Cooldown is per-deployment, not per-model-group | Healthy deployments in same group keep serving | Correct behavior -- no action needed |

---

## S7 Recommended Eval Configuration for CompGraph

```python
# Eval-specific settings (conservative for reliability over speed)
EVAL_ROUTER_CONFIG = {
    "num_retries": 3,
    "retry_after": 5,
    "cooldown_time": 60,
    "allowed_fails": 3,
    "timeout": 45,             # eval prompts can be longer
    "routing_strategy": "simple-shuffle",  # avoid routing bugs
}
EVAL_CONCURRENCY = 5           # start conservative, increase to 10 if stable
EVAL_BATCH_SIZE = 20           # prompts per batch
```

**Decision:** Use `asyncio.Semaphore` for concurrency (not LiteLLM's batch_completion) because:
1. `batch_completion` is synchronous internally
2. Semaphore gives explicit control over parallelism
3. Pairs naturally with `asyncio.gather` + error isolation

---

## Sources

- [LiteLLM Reliability Docs (Fallbacks)](https://docs.litellm.ai/docs/proxy/reliability)
- [LiteLLM Router (Load Balancing)](https://docs.litellm.ai/docs/routing)
- [LiteLLM Retry/Fallback Completions](https://docs.litellm.ai/docs/completion/reliable_completions)
- [LiteLLM Cost Tracking](https://docs.litellm.ai/docs/completion/token_usage)
- [LiteLLM Custom Callbacks](https://docs.litellm.ai/docs/observability/custom_callback)
- [OpenRouter Error Handling](https://openrouter.ai/docs/api/reference/errors-and-debugging)
- [OpenRouter Rate Limits](https://openrouter.ai/docs/api/reference/limits)
- [LiteLLM #8448: Not handling 429s from OpenRouter](https://github.com/BerriAI/litellm/issues/8448)
- [LiteLLM #9035: Free model 429s not honored](https://github.com/BerriAI/litellm/issues/9035)
- [LiteLLM #7669: retry_after not respected](https://github.com/BerriAI/litellm/issues/7669)
- [LiteLLM #8648: Streaming retry inconsistency](https://github.com/BerriAI/litellm/issues/8648)
- [LiteLLM #18968: Per-deployment retries ignored](https://github.com/BerriAI/litellm/issues/18968)
