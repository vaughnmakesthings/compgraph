# High-Speed Labeling UX Patterns

> Reference for CompGraph's Prompt Evaluation Tool (Issue #128). Admin labels ground truth for LLM eval samples — ~100 samples, 15+ fields each.

## Quick Reference

| Metric | Target |
|---|---|
| Fields per sample | 15+ (brand names, pay, role_type, archetype, location, etc.) |
| Samples per batch | ~100 |
| Naive interactions | 100 x 15 = 1,500 clicks |
| Target interactions | <500 (via pre-fill + keyboard + diff review) |
| Stack | Next.js + React (existing frontend) |

## Pattern Comparison

| Pattern | Interaction Reduction | Best For | Complexity |
|---|---|---|---|
| **A: Keyboard-First** | ~30% (Tab/Enter flow) | Any field type, power users | Low |
| **B: Pre-filled Confirmation** | ~60-70% (accept defaults) | High LLM accuracy fields | Medium |
| **C: Diff-Based Review** | ~80% (mark correct/incorrect) | Fields with >90% LLM accuracy | Medium |
| **D: Active Learning** | ~50% fewer samples needed | Large eval corpora | High |

**Recommended: B + A hybrid** — LLM pre-fills all fields, keyboard-first navigation for corrections.

## Pattern B: Pre-filled Confirmation (Primary)

LLM output pre-populates every field. Human reviews and corrects only what's wrong.

### Interaction Math

- If LLM is 85% accurate across fields: 100 samples x 15 fields x 15% error = **225 corrections**
- Add navigation overhead (~1 action per sample): **325 total interactions**
- vs 1,500 naive = **78% reduction**

### React Implementation

```tsx
// Field with pre-filled value — green border if confirmed, yellow if modified
interface PrefilledFieldProps {
  label: string;
  llmValue: string | number | null;
  groundTruth: string | number | null;  // null = not yet reviewed
  onConfirm: (value: string | number) => void;
  fieldType: "text" | "number" | "categorical";
  options?: string[];  // for categorical
}

function PrefilledField({ label, llmValue, groundTruth, onConfirm, fieldType, options }: PrefilledFieldProps) {
  const isReviewed = groundTruth !== null;
  const isModified = isReviewed && groundTruth !== llmValue;

  return (
    <div className={cn(
      "border-l-4 px-3 py-1.5",
      !isReviewed && "border-l-gray-300",
      isReviewed && !isModified && "border-l-emerald-500",
      isModified && "border-l-amber-500",
    )}>
      <label className="text-xs font-medium text-gray-500">{label}</label>
      {fieldType === "categorical" ? (
        <select
          value={groundTruth ?? llmValue ?? ""}
          onChange={(e) => onConfirm(e.target.value)}
          onFocus={(e) => e.target.select()}
        >
          {options?.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input
          type={fieldType === "number" ? "number" : "text"}
          defaultValue={llmValue ?? ""}
          onBlur={(e) => onConfirm(e.target.value)}
        />
      )}
    </div>
  );
}
```

## Pattern A: Keyboard-First Navigation

### Key Bindings (Consistent Across Tools)

| Key | Action |
|---|---|
| `Tab` / `Shift+Tab` | Next / previous field |
| `Enter` | Confirm current field value (accept pre-fill or edit) |
| `Ctrl+Enter` | Submit entire sample, advance to next |
| `Ctrl+S` | Save draft (persist progress) |
| `Ctrl+Z` | Undo last field change |
| `Escape` | Skip sample (mark for later) |
| `1-9` | Select categorical option by index |
| `y` / `n` | Boolean fields (e.g., "is_remote") |
| `ArrowUp` / `ArrowDown` | Navigate categorical dropdowns |

### Focus Management in React

```tsx
// Auto-advance focus after confirming a field
function useLabelingKeyboard(fieldRefs: React.RefObject<HTMLElement>[]) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.ctrlKey) {
        e.preventDefault();
        // Confirm current, advance to next
        const next = Math.min(activeIndex + 1, fieldRefs.length - 1);
        setActiveIndex(next);
        fieldRefs[next]?.current?.focus();
      }
      if (e.key === "Enter" && e.ctrlKey) {
        e.preventDefault();
        // Submit sample — parent handles save + advance
        document.dispatchEvent(new CustomEvent("submit-sample"));
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [activeIndex, fieldRefs]);

  return { activeIndex, setActiveIndex };
}
```

## Pattern C: Diff-Based Review (Secondary)

For fields with very high LLM accuracy (>90%), show only the diff:

```
Sample #42 — "Brand Ambassador - Samsung at Best Buy"
┌──────────────────────────────────────────────┐
│ brand_names:  Samsung, Best Buy         [✓][✗] │
│ pay_min:      $18.00                    [✓][✗] │
│ pay_max:      $22.00                    [✓][✗] │
│ role_type:    brand_ambassador          [✓][✗] │
│ archetype:    in_store_demo             [✓][✗] │  ← click ✗ to edit
│ location:     Chicago, IL              [✓][✗] │
└──────────────────────────────────────────────┘
  [Accept All] (Ctrl+Enter)    3 of 100 complete
```

Clicking the check icon confirms the field; clicking the X icon expands an inline editor. "Accept All" confirms every field in one action.

## Session & Progress

| Feature | Implementation |
|---|---|
| **Auto-save** | Debounced save to API on every field confirm (optimistic UI via `useOptimistic`) |
| **Resume** | Store `last_sample_index` + per-field completion state in DB |
| **Progress bar** | `{completed}/{total}` with time estimate based on rolling average per-sample time |
| **Batch mode** | Load 10 samples at a time, prefetch next batch while user works on current |
| **Undo stack** | Per-sample undo history (last 10 actions), `Ctrl+Z` to step back |
| **Skip & return** | `Escape` marks sample as skipped, filterable in sidebar for later review |

## Tool Comparison (Lessons Learned)

| Tool | Key UX Insight | Apply to CompGraph |
|---|---|---|
| **Prodigy** | Binary accept/reject with `a`/`x` keys reduces complex decisions to simple ones | Use for boolean fields; pre-fill + confirm for others |
| **Argilla** | "Suggestions" (sparkle icon) show model confidence alongside pre-filled values | Show LLM confidence scores per field to guide reviewer attention |
| **Label Studio** | Customizable hotkeys via `Shortcut` tag; outliner panel for multi-region work | Define consistent keymap; show sample context in sidebar |
| **Roboflow** | Smart snapping reduces clicks for geometric annotations | N/A (text/categorical fields) |

## Accessibility & Ergonomics

- All interactive elements must have `aria-label` with field name + current value
- Focus ring visible on every field (no `outline-none` without replacement)
- Color coding is supplemental — never the only indicator (add icons for colorblind users)
- Support `prefers-reduced-motion` — disable auto-advance animations
- Min touch target 44x44px if tablet use is ever needed
- Dark mode: important for long labeling sessions to reduce eye strain

## Gotchas & Limitations

| Issue | Detail |
|---|---|
| **Pre-fill accuracy** | If LLM accuracy is <70%, pre-fills create confirmation bias — reviewers accept wrong values. Monitor agreement rates. |
| **Keyboard trap** | Custom key handlers can break native browser shortcuts. Always check `e.target.tagName` before capturing `Enter` in text inputs. |
| **Optimistic save failure** | If API save fails, the user has already moved on. Queue failed saves and show a persistent banner, not a modal. |
| **Field ordering** | Put high-confidence fields first (categorical) and low-confidence last (free text). Reviewers fatigue — catch errors early. |
| **Batch size** | >20 samples without a break increases error rate. Add a "take a break" prompt at configurable intervals. |
| **Active learning complexity** | Pattern D (active learning) requires a feedback loop to the LLM — defer until eval corpus is established. |

Sources:
- [Prodigy Annotation Tool — Active Learning](https://explosion.ai/blog/prodigy-annotation-tool-active-learning)
- [Argilla Annotation How-To Guide](https://docs.argilla.io/latest/how_to_guides/annotate/)
- [Label Studio Hotkeys Documentation](https://labelstud.io/guide/hotkeys)
- [Label Studio Shortcut Tag](https://labelstud.io/tags/shortcut)
- [Best Data Labeling UI — Labellerr](https://www.labellerr.com/blog/best-data-labeling-user-interface-tools-features-and-best-practices/)
- [React useOptimistic Hook](https://react.dev/reference/react/useOptimistic)
- [TanStack Form Focus Management](https://tanstack.com/form/v1/docs/framework/react/guides/focus-management)
- [focus-graph — React Keyboard Navigation](https://github.com/santiagomuscolo/focus-graph)
- [Custom Annotation Interfaces — Hugging Face](https://huggingface.co/blog/burtenshaw/custom-interface-data-labeling-annotation-html-css)
- [Human-in-the-Loop ML — Manning](https://www.manning.com/books/human-in-the-loop-machine-learning)
