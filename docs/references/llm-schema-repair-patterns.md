# LLM Schema Repair vs Nullification Patterns

> Reference doc for handling Pydantic v2 validation failures on LLM-extracted data.
> Researched: 2026-02-24. CompGraph enrichment pipeline context.

## Quick Reference

| Pattern | When to Use | Cost | Data Loss |
|---------|-------------|------|-----------|
| **A: Repair Prompt** | High-value fields, low volume | +1 LLM call (~$0.003) | None |
| **B: Safe Nullification** | Optional fields, high volume | Zero | Field-level |
| **C: Tiered Validation** | Mixed — soft warn + hard reject | Zero | Configurable |
| **D: Pre-validation Transform** | Known business rule transforms | Zero | None (clamped) |

**Recommended for CompGraph:** Pattern C (tiered) as the default, with Pattern A (repair) reserved for entity extraction (Pass 2) where brand names have high downstream value.

---

## Pattern A: Repair Prompt

Catch `ValidationError`, send back to LLM with error context, request correction.

```python
from pydantic import ValidationError

async def extract_with_repair(
    client, messages: list, result_type: type[T], *, max_repairs: int = 1
) -> T:
    raw = await call_llm(client, messages)
    for attempt in range(max_repairs + 1):
        try:
            return result_type.model_validate_json(raw)
        except ValidationError as e:
            if attempt >= max_repairs:
                raise
            # Build repair prompt from structured errors
            field_errors = [
                f"- {'.'.join(str(l) for l in err['loc'])}: {err['msg']} (got: {err['input']!r})"
                for err in e.errors()
            ]
            repair_msg = (
                "Your previous output had validation errors:\n"
                + "\n".join(field_errors)
                + "\n\nPlease fix ONLY the invalid fields and return the full JSON."
            )
            raw = await call_llm(client, messages + [{"role": "user", "content": repair_msg}])
    raise RuntimeError("unreachable")
```

**Tradeoffs:**
- Extra LLM call: ~$0.003 (Haiku) or ~$0.018 (Sonnet) per repair
- Latency: +500-2000ms per retry
- Use when: field has high downstream value (brand names, entity types)
- Avoid when: batch processing thousands of postings (costs compound)

---

## Pattern B: Safe Nullification

Set invalid field to `None`, log the original value, keep the record intact.

```python
import logging
from typing import Annotated, Any
from pydantic import WrapValidator, ValidatorFunctionWrapHandler, ValidationError

logger = logging.getLogger(__name__)

def nullify_on_error(v: Any, handler: ValidatorFunctionWrapHandler, info) -> Any:
    """WrapValidator: attempt validation, return None on failure."""
    try:
        return handler(v)
    except ValidationError:
        logger.warning(
            "Nullified field %s: invalid value %r",
            info.field_name, v
        )
        return None

NullableFloat = Annotated[float | None, WrapValidator(nullify_on_error)]
```

**This is what CompGraph already does** for categorical fields via `_coerce_literal()` in `schemas.py`. Extend to numeric fields.

---

## Pattern C: Tiered Validation (Recommended)

Separate hard constraints (reject) from soft constraints (warn + keep).

```python
from pydantic import BaseModel, field_validator, model_validator
import logging

logger = logging.getLogger(__name__)

# Tier definitions
PAY_HARD_MAX_HOURLY = 500.0   # Reject: almost certainly hallucinated
PAY_SOFT_MAX_HOURLY = 150.0   # Warn: unusual but valid (medical, specialized)
PAY_HARD_MAX_ANNUAL = 1_000_000.0
PAY_SOFT_MAX_ANNUAL = 300_000.0

class Pass1Result(BaseModel):
    pay_min: float | None = None
    pay_max: float | None = None
    pay_frequency: str | None = None
    _warnings: list[str] = []  # not serialized, available post-parse

    @model_validator(mode="after")
    def _tiered_pay_check(self) -> "Pass1Result":
        for field_name in ("pay_min", "pay_max"):
            val = getattr(self, field_name)
            if val is None:
                continue
            hard_max = (PAY_HARD_MAX_HOURLY if self.pay_frequency == "hour"
                        else PAY_HARD_MAX_ANNUAL)
            soft_max = (PAY_SOFT_MAX_HOURLY if self.pay_frequency == "hour"
                        else PAY_SOFT_MAX_ANNUAL)
            if val > hard_max:
                logger.warning("HARD reject %s=%.2f (max %.2f) — nullifying", field_name, val, hard_max)
                setattr(self, field_name, None)
            elif val > soft_max:
                logger.info("SOFT flag %s=%.2f exceeds soft max %.2f — keeping", field_name, val, soft_max)
                self._warnings.append(f"{field_name}={val} exceeds soft limit {soft_max}")
        return self
```

**Key insight for CompGraph:** Current hard cap at $150/hr is too restrictive. Medical demo specialists, licensed pharmacists, and technical specialists legitimately earn $150-250/hr. Recommended tiers:

| Pay Type | Soft Max (warn + keep) | Hard Max (nullify) |
|----------|------------------------|-------------------|
| Hourly | $150 | $500 |
| Annual | $300K | $1M |

---

## Pattern D: Pre-validation Transform

Apply deterministic business logic before Pydantic sees the data.

```python
from pydantic import model_validator
from typing import Any

class Pass1Result(BaseModel):
    pay_min: float | None = None
    pay_max: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_pay(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Swap if min > max (common LLM mistake)
        pay_min = data.get("pay_min")
        pay_max = data.get("pay_max")
        if pay_min is not None and pay_max is not None and pay_min > pay_max:
            data["pay_min"], data["pay_max"] = pay_max, pay_min
        # Negative pay = hallucination
        for f in ("pay_min", "pay_max"):
            if data.get(f) is not None and data[f] < 0:
                data[f] = None
        return data
```

---

## Logging Strategy

Track nullified/flagged fields for periodic review:

```python
# In orchestrator, after parsing each posting:
if result._warnings:
    await log_enrichment_flags(
        posting_id=posting_id,
        flags=result._warnings,
        raw_values=raw_llm_output,
    )

# Weekly: query flags to detect systematic issues
# SELECT flag_type, COUNT(*) FROM enrichment_flags GROUP BY flag_type
```

Store flags in a lightweight `enrichment_flags` table or structured log (CloudWatch/stdout JSON). Avoid a separate DB table until volume justifies it — structured logging (`logger.warning(..., extra={"posting_id": ..., "field": ..., "raw": ...})`) is sufficient initially.

---

## Gotchas & Limitations

- **`WrapValidator` + `model_validate_json()`**: In Pydantic v2 < 2.5, `WrapValidator` receives `str` not parsed types when using `model_validate_json()`. Use `model_validate(json.loads(...))` instead (which CompGraph already does).
- **`mode='before'` validators receive `Any`**: Always guard with `isinstance(data, dict)` — Pydantic may pass model instances during internal validation.
- **Repair prompts cache-bust**: The repair message changes the input, so prompt caching won't help. Each repair call pays full input token cost.
- **`_warnings` private attrs**: Use `model_config = ConfigDict(arbitrary_types_allowed=True)` or `PrivateAttr` if the list needs to survive serialization round-trips.

---

## Sources

- [Pydantic v2 Validators docs](https://docs.pydantic.dev/latest/concepts/validators/)
- [Pydantic v2 WrapValidator API](https://docs.pydantic.dev/latest/api/functional_validators/)
- [Instructor retry mechanisms](https://python.useinstructor.com/learning/validation/retry_mechanisms/)
- [Pydantic fallback/default on validation failure (Discussion #7867)](https://github.com/pydantic/pydantic/discussions/7867)
- [5 Steps to Handle LLM Output Failures](https://latitude.so/blog/5-steps-to-handle-llm-output-failures)
