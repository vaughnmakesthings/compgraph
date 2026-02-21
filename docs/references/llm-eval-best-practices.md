# LLM Evaluation & Prompt Optimization Best Practices

> Research synthesized Feb 20, 2026. Covers eval frameworks, scoring, statistical rigor, prompt improvement from human feedback, and cost optimization.

## Table of Contents

1. [CompGraph-Eval: Purpose & Architecture](#compgraph-eval-purpose--architecture)
2. [Eval Frameworks & Tools](#eval-frameworks--tools)
3. [Scoring Methodologies](#scoring-methodologies)
4. [Statistical Rigor](#statistical-rigor)
5. [Ground Truth & Human Review](#ground-truth--human-review)
6. [Prompt Improvement from Human Feedback](#prompt-improvement-from-human-feedback)
7. [Error Taxonomy for Structured Output](#error-taxonomy-for-structured-output)
8. [Prompt Patching Strategies](#prompt-patching-strategies)
9. [Prompt Versioning & Regression Testing](#prompt-versioning--regression-testing)
10. [Cost Optimization](#cost-optimization)
11. [Closed-Loop Evaluation Systems](#closed-loop-evaluation-systems)
12. [DSPy & Programmatic Prompt Optimization](#dspy--programmatic-prompt-optimization)
13. [Recommended Implementation Path](#recommended-implementation-path)
14. [Sources](#sources)

---

## CompGraph-Eval: Purpose & Architecture

**What it is:** A standalone LLM evaluation tool that tests prompt/model combinations against CompGraph's enrichment pipeline to answer: *"Which prompt + model combo produces the best structured output for job posting analysis?"*

**Core Goals:**
1. **Prompt Quality Measurement** — field-level accuracy for role classification, pay parsing, entity extraction
2. **Model Comparison** — 13 models across 4 providers (Anthropic, OpenAI, Google, DeepSeek) via OpenRouter
3. **Regression Detection** — field-level regressions when prompts change, using human-reviewed ground truth
4. **Human-in-the-Loop Ground Truth** — curated dataset from field reviews with type-aware scoring

**Current Stack:** Python 3.12+, SQLite (aiosqlite), LiteLLM via OpenRouter, Streamlit + Next.js UIs, 70 tests passing.

**Key Design Decisions Already Made:**
- OpenRouter as unified API gateway
- SQLite for local-first evaluation (no cloud DB dependency)
- Pydantic schemas copied from CompGraph (manual sync)
- Type-aware comparison: pay fields ±5% tolerance, lists Jaccard ≥0.5
- Ground truth from human reviews (not separate labeling process)

---

## Eval Frameworks & Tools

### Leading Frameworks

| Framework | Type | Best For | Structured Output Support |
|-----------|------|----------|--------------------------|
| **[Promptfoo](https://promptfoo.dev/)** | OSS, YAML | CI/CD regression testing | `is-json`, Python assertions, derived metrics |
| **[DeepEval](https://deepeval.com/)** | OSS, Python | Pytest-native LLM testing | `LLMTestCase` with 60+ metrics, G-Eval, DAG |
| **[Braintrust](https://braintrust.dev/)** | Platform | End-to-end with versioning | Content-hash IDs, bidirectional git sync |
| **[Langfuse](https://langfuse.com/)** | OSS, self-host | Observability + cost tracking | Token/cost per model and prompt version |

### Recommendation for CompGraph

**Promptfoo** is the strongest fit: open-source, YAML configs in repo alongside prompts, CI/CD integration, per-field JSON assertions matching `field_reviews` structure, no vendor lock-in.

---

## Scoring Methodologies

### For Structured Output

- **Field Accuracy**: % of individual fields correctly extracted across all samples (finer-grained)
- **Output Accuracy**: % of samples where *every* field is correct (higher bar)
- **Entity F1**: Precision/Recall/F1 for brand mentions and retailers
- **Composite "5 Metric Rule"**: Maintain 1-2 custom + 2-3 system-specific metrics to avoid "evaluation blindness"

### LLM-as-Judge

- **G-Eval**: Chain-of-thought scoring on custom criteria, weighted by log-probabilities
- **DAG Metric**: Binary LLM judgments in directed graph (more deterministic)
- **Binary pass/fail** more reliable than numeric scales for LLM judges
- **[Cleanlab TLM](https://cleanlab.ai/blog/tlm-structured-outputs-benchmark/)**: Per-field trustworthiness scores, 25% better precision than LLM-as-judge

---

## Statistical Rigor

### Critical Finding

> "Don't Use the CLT in LLM Evals With Fewer Than a Few Hundred Datapoints" — [Bowyer et al., ICML 2025](https://arxiv.org/abs/2503.01747)

CLT-based confidence intervals **dramatically underestimate uncertainty** with small eval sets.

### Recommended Methods

**For single-model evaluation:**
```python
from scipy.stats import binomtest, beta

# Wilson Score interval (best frequentist)
result = binomtest(k=successes, n=total)
wilson_ci = result.proportion_ci("wilson", 0.95)

# Bayesian credible interval (best for small N)
posterior = beta(1 + successes, 1 + (total - successes))
bayes_ci = posterior.interval(confidence=0.95)
```

**For comparing two versions (paired tests):**

| Score Type | Test | Why |
|-----------|------|-----|
| Binary (pass/fail) | McNemar's test | Same test cases, both versions |
| Continuous (0-1) | Paired t-test | Same cases, normally distributed |
| Ordinal | Wilcoxon signed rank | Same cases, non-parametric |

### Minimum Sample Sizes

| Confidence | Margin | Expected Accuracy | Required N |
|-----------|--------|-------------------|-----------|
| 95% | 5% | 80% | 246 |
| 95% | 5% | 90% | 138 |
| 95% | 10% | 80% | 62 |

**Start with ~100 ground truth examples for directional signal, scale to 250+ for statistical confidence.**

### Non-Determinism

Run evaluations **n ≥ 10 times** to establish baseline variance. A change is meaningful only if it exceeds observed variance.

---

## Ground Truth & Human Review

### The "5 D's" Framework

1. **Defined Scope** — aligned with specific extraction tasks
2. **Demonstrative of Production** — mirrors actual job postings including edge cases
3. **Diverse** — covers all 4 ATS sources, pay formats, multi-brand postings
4. **Decontaminated** — distinct from prompt development data
5. **Dynamic** — updated as new failure modes emerge

### Human Review Best Practices

- **Inter-Annotator Agreement**: Cohen's Kappa ≥ 0.8 target (2 annotators); Krippendorff's Alpha for 3+
- **Gold set calibration**: 20-30 pre-annotated examples to test reviewer quality
- **Ambiguous cases**: Flag, calibrate, codify rules, weight by confidence: `n_selected_class / n_total_votes`
- **LLM-assisted annotation**: LLM generates initial labels, humans review/correct, disagreements → expert

### When to Add vs. Re-Review

| Situation | Action |
|-----------|--------|
| New ATS adapter added | Add 20-30 examples from that source |
| New role archetype discovered | Add 5-10 examples covering it |
| Accuracy drops after prompt change | Re-review 10 most affected examples |
| Ground truth > 3 months old | Re-review 10% sample |
| Reviewer disagreement > 20% on a field | Calibrate with explicit rules |
| Model upgrade | Re-evaluate entire test set |

### Dataset Size

- **Minimum viable**: 50-100 per field
- **Robust eval**: 200-500 per field, stratified across sources
- **Production quality**: 500+ per field, growing 10-20% per quarter
- **Active learning** reduces annotation needs by 50-80%

---

## Prompt Improvement from Human Feedback

### Automated Approaches

**1. ETGPO (Error Taxonomy-Guided Prompt Optimization)** — [arXiv](https://arxiv.org/html/2602.00997v1)
- Run LLM on validation set K=5 times, collect failed traces
- Optimizer LLM categorizes failures into error types
- Filter to categories appearing ≥2 times, select top G=10 by frequency
- Generate actionable guidance (pattern descriptions, correct/incorrect examples)
- Append guidance to prompt
- **Result**: +3pp average, **1/3 the token cost** of alternatives

**2. Prompt Learning (Arize)** — [arize-ai/prompt-learning](https://github.com/arize-ai/prompt-learning)
- Natural language feedback from failed evals → metaprompt generates prompt patches
- **Result**: 0% → 84% in 1 loop, 100% in 5 loops
- Open-source, production-tested

**3. DSPy GEPA** — [Stanford](https://dspy.ai/)
- Reflective text evolution with Pareto optimization
- **Result**: +22pp accuracy for ~$2-3 in API costs (~1,200 rollouts)
- See [DSPy section](#dspy--programmatic-prompt-optimization)

**4. PromptWizard (Microsoft)** — [Microsoft Research](https://microsoft.github.io/PromptWizard/)
- Self-evolving mechanism: LLM generates, critiques, and refines its own prompts
- Works with as few as 5 examples (only 5% drop vs. 25 examples)
- Outperformed DSPy, APE, PromptBreeder on 45+ tasks
- **Published at ACL 2025 Findings**

### Prioritization Framework

**Frequency × Impact × Fixability:**

| Priority | Criteria | Example |
|----------|----------|---------|
| P0 | High freq + high impact | role_archetype wrong on 30% of merchandiser postings |
| P1 | High freq + low impact | employment_type "contract" vs "temporary" confusion |
| P2 | Low freq + high impact | pay_min/pay_max swapped on commission roles |
| P3 | Low freq + low impact | rare edge case misclassifications |

### Diminishing Returns

- **First 3-5 iterations** deliver 60-80% of total gains
- **10-iteration rule**: if 10 focused iterations don't fix a failure mode, it's architectural
- **When to stop**: if 40 hours of iteration yields <5% improvement, stop

### Concrete Pattern for CompGraph

1. Query `field_reviews` where `is_correct = false`, grouped by `field_name`
2. For each field, collect (input_text, predicted_value, correct_value) triples
3. Feed batches to optimizer LLM to identify error categories
4. Filter to most frequent categories
5. Generate targeted prompt guidance for each category
6. Append to enrichment prompt as "known pitfalls" section

---

## Error Taxonomy for Structured Output

| Error Type | Description | CompGraph Example |
|------------|-------------|-------------------|
| **Misclassification** | Correct structure, wrong value | `role_archetype: "field_rep"` should be `"merchandiser"` |
| **Hallucination** | Value not in source text | `pay_max: 25.00` when no pay info in posting |
| **Omission** | Failed to extract existing value | `pay_min: null` when posting says "$15/hr" |
| **Boundary Error** | Numeric partially correct | `pay_min: 15` missing "$5 bonus" component |
| **Type Error** | Wrong data type/format | `employment_type: "full time"` not `"full_time"` |
| **Granularity Error** | Wrong specificity level | `role_archetype: "sales"` instead of `"brand_ambassador"` |
| **Conflation** | Merged distinct values | `pay_min: 17.50` averaging "$15-$20" range |
| **Source Confusion** | Extracted from wrong section | Pay from "benefits" instead of "compensation" |
| **Temporal Error** | Outdated/conditional value | "After 90 days" pay instead of starting pay |

### Auto-Classification from `field_reviews`

- Extracted ≠ null, correct_value ≠ null, values differ → **Misclassification** or **Boundary Error**
- Extracted ≠ null, correct_value = null → **Hallucination**
- Extracted = null, correct_value ≠ null → **Omission**
- Extracted value not in source text → **Hallucination**
- Extracted is broader/narrower term → **Granularity Error**

---

## Prompt Patching Strategies

### Hierarchy (lowest to highest risk)

**Level 1 — Targeted Few-Shot Examples**: Add 2-3 examples demonstrating the failure mode. Diminishing returns after 2-3 examples; over-prompting can degrade performance.

**Level 2 — Constraint Injection**: Add explicit rules without changing prompt structure. Example: "When a posting mentions 'merchandiser' in the title, classify as role_archetype='merchandiser', NOT 'field_rep'."

**Level 3 — Chain-of-Thought for Specific Fields**: Add reasoning steps only for problematic fields. Zero-shot verification-guided CoT with self-verification.

**Level 4 — Section Rewrite**: Rewrite the instruction for a specific field while keeping rest intact.

**Level 5 — Full Prompt Rewrite**: Only when patches are internally contradictory, or when switching models.

### Pay Extraction for Commission Roles

- Explicit instructions: "For commission-based roles, set pay_min to base/guaranteed amount only"
- 2 few-shot examples: base+commission, commission-only
- Document the convention in the prompt (base pay vs. total compensation is inherently ambiguous)

---

## Prompt Versioning & Regression Testing

### Maturity Levels

| Level | Approach | When |
|-------|----------|------|
| 1 | Prompts as Python constants + git diff | Current state, sufficient for small team |
| 2 | Decorator-based colocation ([Mirascope](https://mirascope.com/blog/prompt-versioning)) | When iteration speed increases |
| 3 | Dedicated registry ([MLflow](https://mlflow.org/docs/latest/genai/prompt-registry/)) | When tracking across environments |
| 4 | Platform with bidirectional sync ([Braintrust](https://braintrust.dev/)) | When team size grows |

### Regression Testing

- Every prompt change → run against fixed test corpus
- Compare to previous version's baseline
- Flag regressions when any metric drops beyond noise threshold
- Store eval results alongside prompt version for audit trail

---

## Cost Optimization

### Anthropic Batch API

- **50% discount** on all tokens, processed within 24 hours
- No minimum volume requirement
- Combine with prompt caching for up to **90% savings** on repeated system prompts

### Tracking

- **[Langfuse](https://langfuse.com/)**: Open-source, self-hostable, per-model cost dashboard
- **[Helicone](https://helicone.ai/)**: LLM cost calculator, 300+ models, generous free tier

### Strategy for Eval Runs

1. Batch all calls through Anthropic Batch API (50% savings)
2. Cache system prompts (up to 90% savings on that portion)
3. Track per-model cost to compare Haiku vs. Sonnet cost/quality tradeoff
4. Route by complexity: Haiku for classification, Sonnet for entity extraction
5. **Combined savings estimate: 60-80% reduction** vs. synchronous individual calls

---

## Closed-Loop Evaluation Systems

### Minimal Loop for CompGraph

```
1. Eval Runner
   - Pull ground truth from field_reviews
   - Run current prompt against test postings
   - Compute per-field accuracy, store results

2. Diff Reporter
   - Compare vs. previous run
   - Flag regressions (>2% drop) and improvements (>2% gain)
   - Generate human-readable report

3. Prompt Patcher (optional automation)
   - Analyze error patterns (ETGPO-style)
   - Generate candidate patches
   - Create PR for human review

4. Re-evaluator
   - Run patched prompt, confirm improvement
   - Check for regressions, merge or revert
```

### Velocity Tracking

- Record (prompt_version, field_name, accuracy, timestamp) per eval run
- Plot accuracy over time per field
- Track "days since last improvement" per field
- Alert if accuracy trends downward across 3+ consecutive runs

---

## DSPy & Programmatic Prompt Optimization

### Key Optimizers

| Optimizer | Method | Cost | Best For |
|-----------|--------|------|----------|
| **GEPA** | Reflective text evolution | ~$2-3 | Structured extraction |
| **MIPROv2** | Bayesian optimization | High | Multi-stage pipelines |
| **BootstrapFewShot** | Bootstrap from training data | Low | Quick baseline |
| **COPRO** | Coordinate ascent | Medium | Incremental improvement |

### GEPA on Structured Extraction

- **Task**: Financial entity extraction (7 categories)
- **Improvement**: 32.07% → 54.43% exact match (+22pp), mean field accuracy 91.62%
- **Cost**: ~$2-3 for ~1,200 rollouts
- **Optimized prompts**: stricter entity boundaries, disambiguation rules, implicit examples from training failures

### DSPy Signature for CompGraph

```python
class JobPostingExtraction(dspy.Signature):
    """Extract structured fields from a job posting."""
    posting_text: str = dspy.InputField()
    role_archetype: str = dspy.OutputField(desc="One of: merchandiser, brand_ambassador, ...")
    pay_min: float = dspy.OutputField(desc="Minimum pay in USD/hour")
    pay_max: float = dspy.OutputField(desc="Maximum pay in USD/hour")
    employment_type: str = dspy.OutputField(desc="One of: full_time, part_time, ...")
```

### Limitations

- Optimized prompts are model-specific (switching models requires re-optimization)
- CompGraph's 2-pass architecture needs each pass optimized independently
- Non-deterministic — always evaluate on held-out test set
- BAML adapter adds marginal improvement on simple schemas

### Alternatives

- **[AdalFlow](https://github.com/SylphAI-Inc/AdalFlow)**: PyTorch-like, DataClass for structured output, highest claimed accuracy
- **[PromptWizard](https://microsoft.github.io/PromptWizard/)**: Microsoft, ACL 2025 Findings, works with 5 examples, outperformed DSPy on 45+ tasks

---

## Recommended Implementation Path

### Phase 1 — Manual Error Analysis + Surgical Patches (Immediate)
- Classify errors from `field_reviews` using the error taxonomy
- Prioritize by frequency × impact
- Apply Level 1-2 patches (few-shot examples + constraints)
- Track per-field accuracy across prompt versions

### Phase 2 — Promptfoo Integration (Short-term)
- Define YAML test configs with per-field assertions against ground truth
- Wire into CI so every prompt change triggers evaluation
- Build regression detection into PR workflow

### Phase 3 — ETGPO-Style Automation (Medium-term)
- Automate error pattern analysis from `field_reviews`
- Generate candidate prompt patches programmatically
- Human reviews patches before deployment
- Most cost-efficient approach (~1/3 token cost of alternatives)

### Phase 4 — DSPy/GEPA Optimization (When dataset is large enough)
- Define DSPy signatures for each extraction field
- Use `field_reviews` as training data for GEPA optimization
- Run optimization per-pass (Pass 1 and Pass 2 separately)
- Expected: 15-22pp accuracy improvement, ~$2-3 per optimization run

### Key Numbers

| Metric | Value |
|--------|-------|
| GEPA accuracy gain | +22pp for $2-3 |
| ETGPO accuracy gain | +3pp at 1/3 token cost |
| Prompt Learning | 0% → 84% in 1 iteration |
| Few-shot diminishing returns | After 2-3 examples |
| Ground truth minimum | 50-100 per field |
| Active learning savings | 50-80% fewer annotations |
| 10-iteration rule | Stop if no fix → architectural |
| Statistical confidence | 246 samples for 95%/5% margin |

---

## Sources

### Frameworks & Tools
- [Promptfoo JSON Evaluation Guide](https://www.promptfoo.dev/docs/guides/evaluate-json/)
- [DeepEval Documentation](https://deepeval.com/docs/evaluation-introduction)
- [Braintrust Platform](https://www.braintrust.dev/articles/best-llm-evaluation-platforms-2025)
- [Langfuse Cost Tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking)
- [Cleanlab TLM Benchmark](https://cleanlab.ai/blog/tlm-structured-outputs-benchmark/)

### Statistical Methods
- [Don't Use CLT in LLM Evals (ICML 2025)](https://arxiv.org/abs/2503.01747)
- [Practical Guide for Evaluating LLMs](https://arxiv.org/html/2506.13023v1)

### Prompt Optimization
- [ETGPO Paper](https://arxiv.org/html/2602.00997v1)
- [Prompt Learning (Arize)](https://arize.com/blog/prompt-learning-using-english-feedback-to-optimize-llm-systems/)
- [DSPy Framework](https://dspy.ai/)
- [GEPA Structured Extraction Benchmark](https://kmad.ai/DSPy-Optimization)
- [PromptWizard (Microsoft)](https://microsoft.github.io/PromptWizard/)
- [AdalFlow](https://github.com/SylphAI-Inc/AdalFlow)
- [Diminishing Returns in Prompt Engineering](https://softcery.com/lab/the-ai-agent-prompt-engineering-trap-diminishing-returns-and-real-solutions)

### Human Review & Ground Truth
- [Beyond Agreement (arXiv)](https://arxiv.org/html/2508.00143v1)
- [Booking.com LLM Evaluation Tips](https://booking.ai/llm-evaluation-practical-tips-at-booking-com-1b038a0d6662)
- [Cohen's Kappa (Surge AI)](https://surge-ai.medium.com/inter-annotator-agreement-an-introduction-to-cohens-kappa-statistic-dcc15ffa5ac4)
- [Active Learning for LLMs](https://intuitionlabs.ai/articles/active-learning-hitl-llms)
- [Active Learning Survey (ACL 2025)](https://aclanthology.org/2025.acl-long.708/)

### Error Taxonomy
- [Taxonomy of Prompt Defects](https://arxiv.org/html/2509.14404v1)
- [Comprehensive Hallucination Taxonomy](https://arxiv.org/html/2508.01781)

### Prompt Techniques
- [Chain-of-Thought Prompting Guide](https://www.promptingguide.ai/techniques/cot)
- [Few-Shot Dilemma: Over-Prompting LLMs](https://arxiv.org/pdf/2509.13196)
- [Mirascope Prompt Versioning](https://mirascope.com/blog/prompt-versioning)
- [MLflow Prompt Registry](https://mlflow.org/docs/latest/genai/prompt-registry/)

### Cost & Pricing
- [Anthropic API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Helicone LLM Cost Calculator](https://www.helicone.ai/llm-cost)
