"use client";

import React from "react";

export type BadgeVariant = "success" | "warning" | "error" | "neutral" | "info";

interface BadgeProps {
  variant: BadgeVariant;
  children: React.ReactNode;
  size?: "sm" | "md";
}

const variantStyles: Record<
  BadgeVariant,
  { bg: string; text: string }
> = {
  success: {
    bg: "#1B998B1A",
    text: "#1B998B",
  },
  warning: {
    bg: "#DCB2561A",
    text: "#DCB256",
  },
  error: {
    bg: "#8C2C231A",
    text: "#8C2C23",
  },
  neutral: {
    bg: "#E8E8E4",
    text: "#4F5D75",
  },
  // info maps to neutral semantics — use neutral for new code
  info: {
    bg: "#4F5D751A",
    text: "#4F5D75",
  },
};

const sizeStyles: Record<"sm" | "md", { fontSize: string; padding: string }> =
  {
    sm: { fontSize: "10px", padding: "1px 6px" },
    md: { fontSize: "11px", padding: "2px 8px" },
  };

export function Badge({ variant, children, size = "md" }: BadgeProps) {
  const colors = variantStyles[variant];
  const sizing = sizeStyles[size];

  return (
    <span
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
        borderRadius: "var(--radius-sm, 4px)",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
        fontSize: sizing.fontSize,
        fontWeight: 500,
        padding: sizing.padding,
        display: "inline-flex",
        alignItems: "center",
        lineHeight: "1.4",
      }}
    >
      {children}
    </span>
  );
}
