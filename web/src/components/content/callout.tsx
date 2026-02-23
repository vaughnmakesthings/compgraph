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
    borderColor: "#4F5D75",
    bg: "#4F5D750D",
    titleColor: "#4F5D75",
  },
  positive: {
    borderColor: "#1B998B",
    bg: "#1B998B0D",
    titleColor: "#1B998B",
  },
  risk: {
    borderColor: "#8C2C23",
    bg: "#8C2C230D",
    titleColor: "#8C2C23",
  },
  caution: {
    borderColor: "#DCB256",
    bg: "#DCB2560D",
    titleColor: "#A07D28",
  },
};

export function Callout({ variant, title, children }: CalloutProps) {
  const styles = variantStyles[variant];

  return (
    <div
      style={{
        borderLeft: `4px solid ${styles.borderColor}`,
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
