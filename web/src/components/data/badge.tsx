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
  { bg: string; text: string; border: string }
> = {
  success: {
    bg: "#1B998B1A",
    text: "#1B998B",
    border: "#1B998B33",
  },
  warning: {
    bg: "#DCB2561A",
    text: "#A07D28",
    border: "#DCB25633",
  },
  error: {
    bg: "#8C2C231A",
    text: "#8C2C23",
    border: "#8C2C2333",
  },
  neutral: {
    bg: "#E8E8E4",
    text: "#4F5D75",
    border: "#BFC0C0",
  },
  info: {
    bg: "#4F5D751A",
    text: "#4F5D75",
    border: "#4F5D7533",
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
        border: `1px solid ${colors.border}`,
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
