"use client";

import React from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  /** Content rendered on the right side inside the input (e.g. show/hide toggle) */
  rightElement?: React.ReactNode;
}

export function Input({
  label,
  error,
  hint,
  rightElement,
  id,
  className: _className,
  style,
  ...props
}: InputProps) {
  const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      {label && (
        <label
          htmlFor={inputId}
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            fontWeight: 500,
            color: "var(--color-foreground, #2D3142)",
          }}
        >
          {label}
        </label>
      )}

      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        <input
          id={inputId}
          style={{
            width: "100%",
            padding: rightElement ? "10px 40px 10px 12px" : "10px 12px",
            fontSize: "14px",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-foreground, #2D3142)",
            backgroundColor: "var(--color-surface, #FFFFFF)",
            border: `1px solid ${error ? "var(--color-error, #8C2C23)" : "var(--color-border, #BFC0C0)"}`,
            borderRadius: "var(--radius-md, 6px)",
            outline: "none",
            transition: "border-color 150ms",
            ...style,
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = error
              ? "var(--color-error, #8C2C23)"
              : "var(--color-foreground, #2D3142)";
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = error
              ? "var(--color-error, #8C2C23)"
              : "var(--color-border, #BFC0C0)";
            props.onBlur?.(e);
          }}
          {...props}
        />
        {rightElement && (
          <div
            style={{
              position: "absolute",
              right: "10px",
              display: "flex",
              alignItems: "center",
              color: "var(--color-muted-foreground, #4F5D75)",
            }}
          >
            {rightElement}
          </div>
        )}
      </div>

      {(error ?? hint) && (
        <p
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "12px",
            color: error ? "var(--color-error, #8C2C23)" : "var(--color-muted-foreground, #4F5D75)",
            margin: 0,
          }}
        >
          {error ?? hint}
        </p>
      )}
    </div>
  );
}
