"use client";

import { useState } from "react";
import {
  EyeIcon,
  EyeSlashIcon,
} from "@heroicons/react/24/outline";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [mode, setMode] = useState<"password" | "magic-link">("password");

  return (
    <form
      onSubmit={(e) => e.preventDefault()}
      noValidate
      style={{ display: "flex", flexDirection: "column", gap: "20px" }}
    >

      {/* Mode tabs */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid var(--color-border, #BFC0C0)",
          gap: "0",
        }}
      >
        {(["password", "magic-link"] as const).map((m) => {
          const label = m === "password" ? "Password" : "Magic link";
          const active = mode === m;
          return (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              style={{
                flex: 1,
                padding: "8px 0",
                fontSize: "13px",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontWeight: active ? 600 : 400,
                color: active
                  ? "var(--color-foreground, #2D3142)"
                  : "var(--color-muted-foreground, #4F5D75)",
                background: "transparent",
                border: "none",
                borderBottom: active
                  ? "2px solid var(--color-primary, #EF8354)"
                  : "2px solid transparent",
                cursor: "pointer",
                transition: "color 150ms, border-color 150ms",
                marginBottom: "-1px",
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Fields */}
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <Input
          label="Email address"
          type="email"
          placeholder="you@company.com"
          autoComplete="email"
          required
        />

        {mode === "password" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <Input
              label="Password"
              type={showPassword ? "text" : "password"}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              rightElement={
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  style={{
                    background: "none",
                    border: "none",
                    padding: "0",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    color: "var(--color-muted-foreground, #4F5D75)",
                  }}
                >
                  {showPassword ? (
                    <EyeSlashIcon style={{ width: 16, height: 16 }} />
                  ) : (
                    <EyeIcon style={{ width: 16, height: 16 }} />
                  )}
                </button>
              }
            />
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                type="button"
                style={{
                  background: "none",
                  border: "none",
                  padding: "0",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                  color: "var(--color-muted-foreground, #4F5D75)",
                  textDecoration: "underline",
                  textUnderlineOffset: "2px",
                }}
              >
                Forgot password?
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Submit */}
      <Button variant="primary" size="lg" style={{ width: "100%" }}>
        {mode === "password" ? "Sign in" : "Send magic link"}
      </Button>

      {/* Invite-only note */}
      <p
        style={{
          fontSize: "12px",
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          color: "var(--color-muted-foreground, #4F5D75)",
          textAlign: "center",
          margin: 0,
          lineHeight: 1.6,
        }}
      >
        Invite-only access — contact your admin to request an account.
      </p>
    </form>
  );
}
