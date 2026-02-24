"use client";

import React from "react";

export type CalloutVariant = "finding" | "positive" | "risk" | "caution";

interface CalloutProps {
  variant: CalloutVariant;
  title: string;
  children: React.ReactNode;
}

const variantStyles: Record<
  CalloutVariant,
  { borderColor: string; bg: string; titleColor: string }
> = {
  finding: {
    borderColor: "#EF8354",
    bg: "rgba(239,131,84,0.10)",
    titleColor: "#EF8354",
  },
  positive: {
    borderColor: "#1B998B",
    bg: "rgba(27,153,139,0.10)",
    titleColor: "#1B998B",
  },
  risk: {
    borderColor: "#8C2C23",
    bg: "rgba(140,44,35,0.10)",
    titleColor: "#8C2C23",
  },
  caution: {
    borderColor: "#DCB256",
    bg: "rgba(220,178,86,0.10)",
    titleColor: "#DCB256",
  },
};

export function Callout({ variant, title, children }: CalloutProps) {
  const styles = variantStyles[variant];

  return (
    <div
      style={{
        borderLeft: `3px solid ${styles.borderColor}`,
        backgroundColor: styles.bg,
        borderRadius: "var(--radius-lg, 8px)",
        padding: "1rem",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
      }}
    >
      <p
        style={{
          color: styles.titleColor,
          fontSize: "13px",
          fontWeight: 600,
          marginBottom: "4px",
        }}
      >
        {title}
      </p>
      <div
        style={{
          color: "#2D3142",
          fontSize: "14px",
          lineHeight: "1.5",
        }}
      >
        {children}
      </div>
    </div>
  );
}
