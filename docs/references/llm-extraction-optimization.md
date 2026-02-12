# LLM Extraction Optimization for Job Postings

> Source: Compass research report (Feb 2026). Covers pricing, prompt patterns, pipeline architecture, and validation for entity extraction from job postings using Claude Haiku/Sonnet.

## Section Index

| Section | Lines | Load when |
|---------|-------|-----------|
| Pricing & Cost Math | §1 | Estimating enrichment costs, model selection |
| Structured Output API | §2 | Implementing extraction calls |
| Prompt Patterns | §3 | Writing enrichment prompts |
| Haiku vs Sonnet Quality | §4 | Routing decisions, understanding failure modes |
| Cost Optimization Stack | §5 | Batch API, caching, pre-filtering |
| Pipeline Architecture | §6 | Routing, validation, retry, monitoring |

---

## §1 Pricing & Cost Math

### Per-Million-Token Pricing

| Model | Input | Output | Batch Input | Batch Output | Cache Read |
|-------|-------|--------|-------------|--------------|------------|
| Haiku 3.5 | $0.80 | $4.00 | $0.40 | $2.00 | $0.08 |
| Haiku 4.5 | $1.00 | $5.00 | $0.50 | $2.50 | $0.10 |
| Sonnet 4/4.5 | $3.00 | $15.00 | $1.50 | $7.50 | $0.30 |

- Cache writes: 1.25x base (5-min TTL) or 2x base (1-hour TTL)
- Cache reads: 0.1x base (90% savings)
- Batch + cache discounts **stack**: cached Sonnet batch reads = $0.15/MTok (95% off standard $3)

### Per-Posting Cost (~2K input tokens after cleanup, ~1.5K cached system prompt, ~500 output)

| Configuration | Per Posting |
|---------------|-------------|
| Haiku 4.5, optimized (cache + batch) | ~$0.003 |
| Sonnet, unoptimized | ~$0.018 |
| **6x difference** compounds at scale |

### Monthly Projections (50K postings)

| Scenario | Cost |
|----------|------|
| Sonnet, no optimization | ~$900 |
| Haiku 4.5, no optimization | ~$300 |
| Haiku 4.5 + Batch | ~$175 |
| Haiku 4.5 + Batch + Cache | ~$145 |
| + pre-filter (30% volume reduction) | ~$100 |

**CompGraph actual load (~1,275 postings/month):** ~$4-8/month fully optimized. Backfill ~1,000 postings: ~$3-6.

---

## §2 Structured Output API

### Recommended Pattern (Haiku 4.5 / Sonnet 4.5)

```python
from anthropic import Anthropic, transform_schema

response = client.messages.parse(
    model="claude-haiku-4-5",
    max_tokens=2048,
    system=[{
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral", "ttl": "1h"}
    }],
    messages=[{"role": "user", "content": f"Extract:\n<document>\n{text}\n</document>"}],
    output_config={
        "format": {"type": "json_schema", "schema": transform_schema(MyPydanticModel)}
    }
)
result = response.parsed_output  # Typed Pydantic object, guaranteed valid JSON
```

### Key Behaviors

- First request with new schema: **100-300ms compilation overhead** (cached 24hrs)
- Set generous `max_tokens` — truncation produces invalid output even with constrained decoding
- Monitor `stop_reason`: only `"end_turn"` guarantees valid model. `"max_tokens"` = truncated. `"refusal"` = safety-rejected.
- `ge`/`le` Pydantic constraints are **described but not enforced** by grammar — validate post-response
- Supported: Haiku 4.5, Sonnet 4.5, Opus 4.1/4.5

### Alternative: Tool Use Workaround (Haiku 3.5 only)

For models without native structured outputs, define a dummy tool with extraction schema + `tool_choice` to force use. ~99%+ JSON validity but not mathematically guaranteed.

---

## §3 Prompt Patterns

### System Prompt Structure

- **XML tags** for structural delineation (Claude responds exceptionally well to these)
- **Field descriptions in Pydantic schema ARE read and used** — schema design = prompt engineering
- **3-5 diverse few-shot examples** optimal. Cover: clean postings, messy postings, agency vs direct-hire, missing fields
- **Must include at least one null-output example** — without this, Claude hallucinates to fill empty fields
- **Temperature 0.0-0.2** for extraction. 0.0 for batch consistency.

### When to Use Chain-of-Thought

- **Skip CoT** for straightforward extraction (explicit entity types, structured format)
- **Use CoT** for: employer vs client disambiguation, geographic resolution, implicit hiring signals
- Practical: classify complexity first, apply CoT only to complex subset
- `reasoning` field in Pydantic model positioned BEFORE answer fields forces chain-of-thought

---

## §4 Haiku vs Sonnet Quality

### Haiku Is Good Enough For

- Well-structured postings with explicit entity mentions
- Simple NER (names, dates, locations, emails)
- Template-based extraction from standardized ATS formats
- Binary classification tasks

Practitioner data: replaced 3 Sonnet sub-agents with Haiku, costs $890/day → $180/day (80% savings), accuracy 96.4% → 91.2%, improved to 94.8% with retry logic.

### Where the Quality Cliff Appears

| Failure Mode | Impact on CompGraph |
|-------------|---------------------|
| **Relationship inference** | Haiku can't determine employer vs client without explicit "on behalf of" language. Critical for Pass 2 entity classification. |
| **Entity hallucination** | Haiku 4.5 fabricates plausible company names not in source text. Most dangerous failure for competitive intelligence — a missing entity is noticeable, a fabricated one is not. |
| **Instruction following** | Haiku 3.5: ~60%. Haiku 4.5: ~90%. Sonnet: ~95%+. Impacts schema compliance. |
| **Output verbosity** | Haiku produces 33-75% more output tokens than Sonnet, narrowing effective cost gap from 3x to 2-2.4x. |

### CompGraph Implication

Pass 1 (section tagging, classification, pay extraction) → **Haiku 4.5** — entities are explicit, schema is straightforward.
Pass 2 (brand/retailer entity extraction, relationship classification) → **Sonnet 4.5** — relationship inference + hallucination risk justify the premium.
**Source text verification is non-negotiable on both passes.**

---

## §5 Cost Optimization Stack

Ordered by impact. Each technique stacks on others.

### 1. Pre-filter Before LLM (highest ROI)

Strip HTML/CSS/JS boilerplate (40-60% of input tokens), remove navigation/footer/header, deduplicate postings, skip non-matching content. Can cut volume 30-50%.

### 2. Prompt Caching (1-hour TTL)

Cache the system prompt (extraction rules + schema + few-shot examples, ~1,500-2,000 tokens). Break-even: 2 API calls. For batch processing, 1-hour TTL is critical (default 5-min TTL expires mid-batch).

```python
system=[{
    "type": "text",
    "text": EXTRACTION_SYSTEM_PROMPT,
    "cache_control": {"type": "ephemeral", "ttl": "1h"}
}]
```

### 3. Batch API (50% Discount)

- Up to 100,000 requests per batch or 256 MB
- Most complete in <1 hour (24-hour max)
- Separate throughput from standard API limits (no competition)
- Cache hits within batches: 30-98% depending on traffic
- Results in JSONL with `custom_id` for correlation

### 4. Schema Design

Use terse enums (`"H"/"M"/"L"` not `"high"/"medium"/"low"`), avoid free-text description fields, constrain output space. Outsized impact on Haiku (33% more verbose than Sonnet).

---

## §6 Pipeline Architecture

### Routing Pattern

```
Posting → Pre-process (strip HTML, normalize, dedup)
  → Classify complexity (rule-based, 5-10 rules):
    - Length < 500 tokens + structured format → SIMPLE
    - Ambiguous agency language → COMPLEX
    - Multiple companies mentioned → COMPLEX
    - Default → SIMPLE
  → SIMPLE (70-80%) → Haiku 4.5 + structured outputs
  → COMPLEX (20-30%) → Sonnet 4.5 + structured outputs
  → Validate → Retry with error feedback → Escalate if still failing
```

### 5-Layer Validation Stack

1. **Schema validation** — structured outputs + Pydantic (type checking, required fields, constraints)
2. **Cross-field validation** — logical consistency (`is_staffing_agency=true` → `client_company` should be non-null)
3. **Source verification** — extracted entity names must appear in source text (**critical anti-hallucination check**)
4. **Domain validation** — entities against known taxonomies (company names, job title patterns, valid locations)
5. **Confidence thresholding** — `confidence` field in schema, route <0.7 to Sonnet or human review

### Retry Strategy

- Retry with validation error in prompt (Claude self-corrects when told what's wrong)
- Haiku: 1 retry → escalate to Sonnet
- Sonnet: 2 retries → flag for human review
- ~~Instructor library automates Pydantic error → re-prompt loop~~ — **Decision (Feb 2026): Do NOT use Instructor.** Native Anthropic structured output uses constrained decoding (grammar-level guarantee), eliminating the need for validation retries entirely. Instructor's provider agnosticism is irrelevant (we're 100% Anthropic) and its tool-use workaround adds latency vs native `output_config`. Native also supports Batch API (50% savings on backfills). See `docs/references/similar-projects-research.md`.

### Production Monitoring Metrics

| Metric | Target | Alert On |
|--------|--------|----------|
| Schema compliance rate | ~100% | Any drop (API issue) |
| Source verification pass rate | >95% | Declining (hallucination drift) |
| Confidence score distribution | Stable | Shift (data/model drift) |
| Cache hit rate | >90% | <80% (TTL issue) |
| Cost per extraction | Stable | >2x spike |
| Retry/escalation rate | <10% | Rising (prompt/data quality) |
