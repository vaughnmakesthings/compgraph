import type { CSSProperties } from "react";

/** Standard card container style — white background, silver border, subtle shadow */
export const cardStyle: CSSProperties = {
  backgroundColor: "#FFFFFF",
  borderColor: "#BFC0C0",
  boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
};

/** Display font (Sora) — used for page headings */
export const fontDisplay: CSSProperties = {
  fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
};

/** Body font (DM Sans) — used for most UI text */
export const fontBody: CSSProperties = {
  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
};

/** Monospace font (JetBrains Mono) — used for code, numbers, IDs */
export const fontMono: CSSProperties = {
  fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
};
