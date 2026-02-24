# Postgres JSONB Deep-Diffing for Eval Comparison

Reference for comparing `parsed_result` JSONB between Model A and Model B in eval runs, highlighting field-level differences for a UI comparison view.

**CompGraph context:** `eval_results.parsed_result` (JSONB) contains extracted fields from LLM enrichment (brand names, pay data, role type, archetype, location). The eval tool compares outputs across models/prompts. `EvalComparison` links two `EvalResult` rows; the UI needs a side-by-side diff table showing per-field agreement.

---

## Quick Reference

| Need | Approach | Best For |
|------|----------|----------|
| Flat field diff in SQL | `jsonb_each()` + FULL OUTER JOIN | <100 fields, simple values |
| Detect added/removed keys | `jsonb_object_keys()` set difference | Schema drift detection |
| Deep nested diff | Python `deepdiff` | Arrays, nested objects, type coercion |
| Simple patch output | Python `dictdiffer` | Lightweight, tuple-based diffs |
| Custom scoring | Manual recursive diff | Weighted field matching, tolerances |

**Recommendation:** Python-side diff with `deepdiff` for the comparison logic, SQL only for bulk filtering (e.g., "find all postings where models disagree"). Avoids custom PL/pgSQL functions and handles nested JSONB (brand arrays) correctly.

---

## SQL Approach: Field-by-Field Comparison

### `jsonb_each()` + FULL OUTER JOIN

Compare two `parsed_result` values side-by-side:

```sql
-- Compare two eval results for the same posting
SELECT
  COALESCE(a.key, b.key) AS field,
  a.value AS model_a,
  b.value AS model_b,
  (a.value IS NOT DISTINCT FROM b.value) AS match
FROM
  jsonb_each(
    (SELECT parsed_result FROM eval_results WHERE id = :result_a_id)
  ) a
FULL OUTER JOIN
  jsonb_each(
    (SELECT parsed_result FROM eval_results WHERE id = :result_b_id)
  ) b ON a.key = b.key
ORDER BY COALESCE(a.key, b.key);
```

**Output:**

| field | model_a | model_b | match |
|-------|---------|---------|-------|
| pay_min | "25.00" | "28.00" | false |
| role_type | "brand_ambassador" | "brand_ambassador" | true |
| archetype | "retail_demo" | "field_marketing" | false |

### Detect Added/Removed Keys

```sql
-- Keys in A but not B
SELECT jsonb_object_keys(a.parsed_result)
EXCEPT
SELECT jsonb_object_keys(b.parsed_result)
FROM eval_results a, eval_results b
WHERE a.id = :result_a_id AND b.id = :result_b_id;
```

### Custom `jsonb_diff` Function

Postgres has no built-in diff. Minimal custom function:

```sql
CREATE OR REPLACE FUNCTION jsonb_diff(l JSONB, r JSONB)
RETURNS JSONB AS $$
  SELECT COALESCE(jsonb_object_agg(
    COALESCE(a.key, b.key),
    jsonb_build_object('a', a.value, 'b', b.value)
  ), '{}'::jsonb)
  FROM jsonb_each(l) a
  FULL OUTER JOIN jsonb_each(r) b ON a.key = b.key
  WHERE a.value IS DISTINCT FROM b.value;
$$ LANGUAGE sql IMMUTABLE;

-- Usage:
SELECT jsonb_diff(a.parsed_result, b.parsed_result)
FROM eval_results a, eval_results b
WHERE a.id = :result_a_id AND b.id = :result_b_id;
```

**Limitation:** Only compares top-level keys. Nested objects (e.g., `brands: [{name: "X"}]`) are compared as opaque JSONB values --- array element reordering causes false mismatches.

---

## Python Approach: Deep Comparison

### `deepdiff` (Recommended)

```bash
uv add deepdiff  # v8.6.1+
```

```python
from deepdiff import DeepDiff

diff = DeepDiff(
    result_a["parsed_result"],
    result_b["parsed_result"],
    ignore_order=True,              # list order doesn't matter for brands
    ignore_type_in_groups=[(str, int, float)],  # "25" vs 25
    significant_digits=2,           # pay tolerance: $25.001 == $25.00
    verbose_level=2,                # include old+new values in output
)

# diff.to_dict() keys:
# "values_changed"   -> {"root['pay_min']": {"new_value": 28, "old_value": 25}}
# "dictionary_item_added"   -> ["root['new_field']"]
# "dictionary_item_removed" -> ["root['old_field']"]
# "iterable_item_added"     -> nested list additions
```

**Handling type mismatches:** `ignore_type_in_groups=[(str, int, float)]` treats `"25"` and `25` as comparable. For stricter control, use `number_to_string_func` to normalize before comparison.

### `dictdiffer` (Lightweight Alternative)

```python
from dictdiffer import diff

changes = list(diff(result_a["parsed_result"], result_b["parsed_result"]))
# [('change', 'pay_min', ('25.00', '28.00')),
#  ('add', '', [('new_field', 'value')]),
#  ('remove', '', [('old_field', 'value')])]
```

Simpler API, tuple output. No type coercion or nested array handling --- preprocess first.

### Manual Recursive Diff (CompGraph-Specific)

Tailored for the eval UI output format:

```python
from typing import Any

# Fields that matter more for scoring
FIELD_WEIGHTS: dict[str, float] = {
    "role_type": 2.0, "archetype": 2.0, "brands": 3.0,
    "pay_min": 1.5, "pay_max": 1.5, "pay_type": 1.0,
    "location_city": 1.0, "location_state": 1.0,
}

def compare_parsed_results(
    a: dict[str, Any], b: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare two parsed_result dicts, return UI-ready diff rows."""
    all_keys = sorted(set((a or {}).keys()) | set((b or {}).keys()))
    rows = []
    for key in all_keys:
        val_a, val_b = (a or {}).get(key), (b or {}).get(key)
        match = _values_match(key, val_a, val_b)
        rows.append({
            "field": key,
            "model_a": _serialize(val_a),
            "model_b": _serialize(val_b),
            "match": match,
            "weight": FIELD_WEIGHTS.get(key, 1.0),
        })
    return rows

def _values_match(field: str, a: Any, b: Any) -> bool:
    """Type-aware comparison with tolerances."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    # Numeric tolerance for pay fields
    if field.startswith("pay_") and _is_numeric(a) and _is_numeric(b):
        return abs(float(a) - float(b)) / max(float(a), 0.01) < 0.05  # 5%
    # List comparison (brands, retailers) --- Jaccard similarity
    if isinstance(a, list) and isinstance(b, list):
        set_a = {_normalize(x) for x in a}
        set_b = {_normalize(x) for x in b}
        if not set_a and not set_b:
            return True
        jaccard = len(set_a & set_b) / len(set_a | set_b)
        return jaccard >= 0.5
    # String: case-insensitive, strip whitespace
    return str(a).strip().lower() == str(b).strip().lower()

def _is_numeric(v: Any) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False

def _normalize(x: Any) -> str:
    """Normalize list items for set comparison."""
    if isinstance(x, dict):
        return str(sorted(x.items())).lower()
    return str(x).strip().lower()

def _serialize(v: Any) -> str | None:
    """Serialize value for UI display."""
    if v is None:
        return None
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)
```

### Weighted Scoring

```python
def compute_match_score(diff_rows: list[dict]) -> float:
    """Weighted field-level match rate (0.0-1.0)."""
    total_weight = sum(r["weight"] for r in diff_rows)
    if total_weight == 0:
        return 1.0
    matched_weight = sum(r["weight"] for r in diff_rows if r["match"])
    return round(matched_weight / total_weight, 4)
```

---

## Performance: SQL vs Python

| Scenario | SQL (in-DB) | Python (app-side) |
|----------|-------------|-------------------|
| 100 results | ~5ms | ~15ms (fetch + diff) |
| 500 results | ~20ms | ~60ms |
| Nested arrays | Cannot diff correctly | Full support |
| Type coercion | Manual CAST only | `deepdiff` handles it |
| Custom scoring | Requires PL/pgSQL | Native Python |

**Verdict:** Use SQL for bulk filtering ("which postings differ?"), Python for per-posting detailed diff. At 100-500 results per run, Python overhead is negligible.

### Bulk Mismatch Detection (SQL, for Filtering)

```sql
-- Find postings where models disagree (fast filter before Python diff)
SELECT a.posting_id
FROM eval_results a
JOIN eval_results b ON a.posting_id = b.posting_id
WHERE a.run_id = :run_a_id
  AND b.run_id = :run_b_id
  AND a.parsed_result IS DISTINCT FROM b.parsed_result;
```

---

## UI Output Format

The comparison endpoint should return:

```json
{
  "posting_id": "posting_abc123",
  "model_a": "claude-3-5-haiku-20241022",
  "model_b": "gpt-4o-mini",
  "match_score": 0.72,
  "fields": [
    {"field": "role_type", "model_a": "brand_ambassador", "model_b": "brand_ambassador", "match": true, "weight": 2.0},
    {"field": "pay_min", "model_a": "25.00", "model_b": "28.00", "match": false, "weight": 1.5},
    {"field": "brands", "model_a": "Nike, Adidas", "model_b": "Nike", "match": false, "weight": 3.0}
  ]
}
```

---

## Handling Nested JSONB

The `parsed_result` contains arrays like `brands: [{name: "Nike", role: "primary"}]`.

| Strategy | Approach |
|----------|----------|
| **Flatten before diff** | Extract `brands` → `brand_names: ["Nike", "Adidas"]` before comparing |
| **DeepDiff `ignore_order`** | Handles array reordering; set `ignore_order=True` |
| **Jaccard on extracted names** | `set(a_brands) & set(b_brands) / set(a_brands) | set(b_brands)` |

**Recommendation:** Flatten brand/retailer arrays to name lists before diffing. The UI cares about "did both models find the same brands?" not "did they format the JSON identically?"

---

## PostgreSQL 17 Notes

- **`JSON_TABLE` (SQL/JSON standard):** Available since PG 15, improved in 17. Can destructure JSONB into relational rows, but adds complexity over `jsonb_each()` for simple diffs.
- **`jsonb_strip_nulls()`:** Useful for pre-cleaning before comparison --- removes null fields that one model includes and another omits.
- **No built-in `jsonb_diff`:** Still not available in PG 17. The custom function above remains necessary for SQL-side diffing.
- **`@>` containment operator:** Fast for "does A contain all of B?" checks, but not bidirectional diff.

---

## Gotchas & Limitations

| Issue | Mitigation |
|-------|------------|
| SQL `jsonb_each()` only expands top level | Use Python for nested diffs |
| Array order causes false mismatches in SQL | `ignore_order=True` in `deepdiff`, or sort arrays before INSERT |
| `"25"` vs `25` type mismatch | `deepdiff` `ignore_type_in_groups` or normalize on write |
| NULL vs missing key | `jsonb_strip_nulls()` before comparison, or treat both as absent |
| Large `raw_response` text in same table | Only SELECT `parsed_result`, not `raw_response`, for diff queries |
| `deepdiff` output paths use `root['key']` | Parse with regex or use `.to_dict()` and extract field names |

---

## Sources

- [A Simple JSON Difference Function (thebuild.com)](https://thebuild.com/blog/2016/01/21/a-simple-json-difference-function/)
- [PostgreSQL jsonb_diff Gist (jarppe)](https://gist.github.com/jarppe/f3cdd32ec58a4bdfb29daa67ef6c3b78)
- [DeepDiff GitHub](https://github.com/seperman/deepdiff)
- [DeepDiff Ignore Types Documentation](https://zepworks.com/deepdiff/current/ignore_types_or_values.html)
- [Dictdiffer GitHub (inveniosoftware)](https://github.com/inveniosoftware/dictdiffer)
- [PostgreSQL 18 JSON Functions Documentation](https://www.postgresql.org/docs/current/functions-json.html)
- [LLM Comparator (Google PAIR)](https://github.com/PAIR-code/llm-comparator)
