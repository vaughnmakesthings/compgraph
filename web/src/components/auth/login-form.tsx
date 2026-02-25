"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  EyeIcon,
  EyeSlashIcon,
} from "@heroicons/react/24/outline";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { supabase } from "@/lib/supabase";

export function LoginForm() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [mode, setMode] = useState<"password" | "magic-link">("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [magicLinkSent, setMagicLinkSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setError(null);
    setLoading(true);

    try {
      if (mode === "password") {
        const { error: authError } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (authError) {
          setError(authError.message);
          return;
        }
        router.push("/");
      } else {
        const { error: authError } = await supabase.auth.signInWithOtp({
          email: email.trim(),
        });
        if (authError) {
          setError(authError.message);
          return;
        }
        setMagicLinkSent(true);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotPassword() {
    if (!supabase || !email.trim()) {
      setError("Enter your email address first");
      return;
    }
    setError(null);
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(
      email.trim(),
    );
    if (resetError) {
      setError(resetError.message);
      return;
    }
    setError(null);
    setMagicLinkSent(true);
  }

  if (magicLinkSent) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "16px",
          textAlign: "center",
          padding: "20px 0",
        }}
      >
        <p
          style={{
            fontSize: "14px",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-foreground, #2D3142)",
            fontWeight: 500,
            margin: 0,
          }}
        >
          Check your email
        </p>
        <p
          style={{
            fontSize: "13px",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground, #4F5D75)",
            margin: 0,
            lineHeight: 1.6,
          }}
        >
          We sent a link to <strong>{email.trim()}</strong>. Click it to sign
          in.
        </p>
        <button
          type="button"
          onClick={() => setMagicLinkSent(false)}
          style={{
            background: "none",
            border: "none",
            padding: "0",
            cursor: "pointer",
            fontSize: "13px",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-primary, #EF8354)",
            textDecoration: "underline",
            textUnderlineOffset: "2px",
          }}
        >
          Back to sign in
        </button>
      </div>
    );
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
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

      {/* Error */}
      {error && (
        <p
          role="alert"
          style={{
            fontSize: "13px",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-error, #8C2C23)",
            margin: 0,
            padding: "8px 12px",
            backgroundColor: "rgba(140, 44, 35, 0.06)",
            borderRadius: "var(--radius-sm, 4px)",
          }}
        >
          {error}
        </p>
      )}

      {/* Fields */}
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <Input
          label="Email address"
          type="email"
          placeholder="you@company.com"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        {mode === "password" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <Input
              label="Password"
              type={showPassword ? "text" : "password"}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
                onClick={() => void handleForgotPassword()}
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
      <Button
        type="submit"
        variant="primary"
        size="lg"
        disabled={loading}
        style={{ width: "100%" }}
      >
        {loading
          ? "Signing in..."
          : mode === "password"
            ? "Sign in"
            : "Send magic link"}
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
