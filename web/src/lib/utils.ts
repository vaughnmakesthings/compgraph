/**
 * Converts a snake_case role archetype string to Title Case for display.
 * e.g. "brand_ambassador" → "Brand Ambassador"
 */
export function formatRoleArchetype(value: string | null | undefined): string {
  if (!value) return '—'
  return value
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
