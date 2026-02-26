import type { EvalRun, EvalResult } from "@/lib/types";

/**
 * Shared field list for eval pages — the enrichment fields compared across runs.
 */
export const EVAL_FIELDS = [
  "role_archetype",
  "role_level",
  "employment_type",
  "pay_type",
  "pay_frequency",
  "pay_min",
  "pay_max",
  "has_commission",
  "has_benefits",
  "travel_required",
  "store_count",
  "tools_mentioned",
  "kpis_mentioned",
] as const;

/**
 * Human-readable label for an eval run: "model / prompt_version · Pass N"
 */
export function formatRunLabel(run: EvalRun): string {
  return `${run.model} / ${run.prompt_version} \u00B7 Pass ${run.pass_number}`;
}

/**
 * Safely extract parsed_result as a Record from an EvalResult.
 * Handles string JSON, object, null, and malformed data.
 */
export function getParsedResult(result: EvalResult): Record<string, unknown> {
  if (!result.parsed_result) return {};
  if (typeof result.parsed_result === "object")
    return result.parsed_result as Record<string, unknown>;
  try {
    return JSON.parse(String(result.parsed_result)) as Record<string, unknown>;
  } catch {
    return {};
  }
}

/**
 * Format a field value for display. Handles null, arrays, booleans, objects.
 */
export function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined) return "\u2014";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value))
    return value.length === 0 ? "\u2014" : value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
