export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// --- Design Token Colors ---
// Named semantic colors extracted from the CompGraph brand palette.
// Matches CSS variables in globals.css @theme block.

export const COLORS = {
  jetBlack: "#2D3142",
  coral: "#EF8354",
  coralHover: "#D86D3F",
  blueSlate: "#4F5D75",
  silver: "#BFC0C0",
  tealJade: "#1B998B",
  chestnut: "#8C2C23",
  warmGold: "#DCB256",
  background: "#F4F4F0",
  surface: "#FFFFFF",
  bone: "#E8E8E4",
  offWhite: "#FAFAF7",
} as const;

// Alpha variants for backgrounds/borders
export const COLORS_ALPHA = {
  chestnutBg: "#8C2C231A",
  chestnutBorder: "#8C2C2333",
  chestnutHoverBg: "#8C2C230D",
  coralBg: "#EF83541A",
  coralBorderLight: "#EF835433",
  coralBgSubtle: "#EF835405",
  tealBg: "#1B998B1A",
  tealBorder: "#1B998B33",
  goldBg: "#DCB2561A",
  goldBorder: "#DCB25633",
  boneFaint: "#E8E8E41A",
} as const;

// Chevron-down SVG data URI for select dropdowns
export const SELECT_CHEVRON_SVG = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%234F5D75' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")`;

// Valid Claude model IDs for eval runs
export const EVAL_MODELS = [
  { id: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" },
  { id: "claude-sonnet-4-5-20241022", label: "Claude Sonnet 4.5" },
  { id: "claude-opus-4-5-20250414", label: "Claude Opus 4.5" },
] as const;
