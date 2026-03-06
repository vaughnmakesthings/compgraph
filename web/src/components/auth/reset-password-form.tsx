"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { supabase } from "@/lib/supabase";

type Strength = "weak" | "fair" | "medium" | "strong";

function calcStrength(pw: string): Strength {
  if (pw.length === 0) return "weak";
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return "weak";
  if (score === 2) return "fair";
  if (score === 3) return "medium";
  return "strong";
}

const STRENGTH_META: Record<
  Strength,
  { label: string; width: string; color: string }
> = {
  weak: {
    label: "Weak",
    width: "20%",
    color: "var(--color-error, #8C2C23)",
  },
  fair: {
    label: "Fair",
    width: "40%",
    color: "var(--color-warning, #DCB256)",
  },
  medium: {
    label: "Medium",
    width: "65%",
    color: "var(--color-warning, #DCB256)",
  },
  strong: {
    label: "Strong",
    width: "100%",
    color: "var(--color-success, #1B998B)",
  },
};

function PasswordInput({
  label,
  placeholder,
  value,
  onChange,
  error,
}: {
  label: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <Input
      label={label}
      type={show ? "text" : "password"}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      autoComplete="new-password"
      error={error}
      rightElement={
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          aria-label={show ? "Hide password" : "Show password"}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            color: "var(--color-muted-foreground, #4F5D75)",
          }}
        >
          {show ? (
            <EyeSlashIcon style={{ width: 16, height: 16 }} />
          ) : (
            <EyeIcon style={{ width: 16, height: 16 }} />
          )}
        </button>
      }
    />
  );
}

export function ResetPasswordForm() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const strength = calcStrength(password);
  const strengthMeta = STRENGTH_META[strength];

  function validate() {
    const e: Record<string, string> = {};
    if (password.length < 8) e.password = "Password must be at least 8 characters";
    if (confirm !== password) e.confirm = "Passwords do not match";
    return e;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) {
      setErrors(errs);
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      if (!supabase) return;
      const { error } = await supabase.auth.updateUser({ password });
      if (error) {
        setErrors({ submit: error.message });
        return;
      }
      setSuccess(true);
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } finally {
      setLoading(false);
    }
  }

  if (success) {
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
          Password updated
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
          Your password has been changed. Redirecting to sign in...
        </p>
        <Link
          href="/login"
          style={{
            fontSize: "13px",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-primary, #EF8354)",
            textDecoration: "underline",
            textUnderlineOffset: "2px",
          }}
        >
          Go to sign in
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} noValidate>
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        {/* New password */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <PasswordInput
            label="New password"
            placeholder="Min 8 characters"
            value={password}
            onChange={setPassword}
            error={errors.password}
          />
          {password.length > 0 && (
            <>
              <div
                style={{
                  height: "3px",
                  backgroundColor: "var(--color-muted, #E8E8E4)",
                  borderRadius: "2px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: strengthMeta.width,
                    backgroundColor: strengthMeta.color,
                    borderRadius: "2px",
                    transition: "width 200ms, background-color 200ms",
                  }}
                />
              </div>
              <p
                style={{
                  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "11px",
                  color: strengthMeta.color,
                  margin: 0,
                }}
              >
                Strength: {strengthMeta.label}
              </p>
            </>
          )}
        </div>

        {/* Confirm password */}
        <PasswordInput
          label="Confirm password"
          placeholder="Re-enter password"
          value={confirm}
          onChange={setConfirm}
          error={errors.confirm}
        />

        {errors.submit && (
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
            {errors.submit}
          </p>
        )}

        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={loading}
          style={{ width: "100%", marginTop: "4px" }}
        >
          {loading ? "Updating..." : "Update password"}
        </Button>

        <div style={{ textAlign: "center" }}>
          <Link
            href="/login"
            style={{
              fontSize: "13px",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              color: "var(--color-muted-foreground, #4F5D75)",
              textDecoration: "underline",
              textUnderlineOffset: "2px",
            }}
          >
            Back to sign in
          </Link>
        </div>
      </div>
    </form>
  );
}
