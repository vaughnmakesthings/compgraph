"use client";

import React from "react";

export type ButtonVariant = "primary" | "secondary" | "destructive" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, React.CSSProperties> = {
  primary: {
    backgroundColor: "#EF8354",
    color: "#FFFFFF",
    border: "none",
  },
  secondary: {
    backgroundColor: "#FFFFFF",
    color: "#2D3142",
    border: "1px solid #BFC0C0",
  },
  destructive: {
    backgroundColor: "#8C2C23",
    color: "#FFFFFF",
    border: "none",
  },
  ghost: {
    backgroundColor: "transparent",
    color: "#4F5D75",
    border: "none",
  },
};

const variantHoverBg: Record<ButtonVariant, string> = {
  primary: "rgba(239,131,84,0.85)",
  secondary: "#FAFAF7",
  destructive: "rgba(140,44,35,0.85)",
  ghost: "#E8E8E4",
};

const sizeStyles: Record<ButtonSize, React.CSSProperties> = {
  sm: { fontSize: "12px", padding: "4px 12px" },
  md: { fontSize: "14px", padding: "8px 16px" },
  lg: { fontSize: "15px", padding: "10px 20px" },
};

export function Button({
  variant = "secondary",
  size = "md",
  children,
  disabled,
  style,
  onMouseEnter,
  onMouseLeave,
  ...props
}: ButtonProps) {
  const [hovered, setHovered] = React.useState(false);

  const baseStyle: React.CSSProperties = {
    ...variantStyles[variant],
    ...sizeStyles[size],
    borderRadius: "var(--radius-md, 6px)",
    fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
    fontWeight: 500,
    lineHeight: "1.4",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.5 : 1,
    transition: "background-color 150ms, opacity 150ms",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "6px",
    whiteSpace: "nowrap",
    ...(hovered && !disabled
      ? { backgroundColor: variantHoverBg[variant] }
      : {}),
    ...style,
  };

  return (
    <button
      type="button"
      disabled={disabled}
      style={baseStyle}
      onMouseEnter={(e) => {
        setHovered(true);
        onMouseEnter?.(e);
      }}
      onMouseLeave={(e) => {
        setHovered(false);
        onMouseLeave?.(e);
      }}
      {...props}
    >
      {children}
    </button>
  );
}
