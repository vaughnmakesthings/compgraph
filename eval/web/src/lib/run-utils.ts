import type { Run } from "@/lib/api-client";

/**
 * Canonical run label: "haiku-3.5 / pass1_v1 · Pass 1 · #42"
 * Used consistently across all run selectors and tables.
 */
export function formatRunLabel(run: Run): string {
  return `${run.model} / ${run.prompt_version} \u00B7 Pass ${run.pass_number} \u00B7 #${run.id}`;
}
