"use client";

import { useState } from "react";
import { EyeIcon, EyeSlashIcon, LockClosedIcon } from "@heroicons/react/24/outline";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AccountSetupFormProps {
  email: string;
}

type Strength = "weak" | "fair" | "medium" | "strong";

function calcStrength(pw: string): Strength {
  if (pw.length === 0) return "weak";
  let score = 0;
  if (pw.length >= 8)  score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return "weak";
  if (score === 2) return "fair";
  if (score === 3) return "medium";
  return "strong";
}

const STRENGTH_META: Record<Strength, { label: string; width: string; color: string }> = {
  weak:   { label: "Weak",   width: "20%",  color: "var(--color-error, #8C2C23)" },
  fair:   { label: "Fair",   width: "40%",  color: "var(--color-warning, #DCB256)" },
  medium: { label: "Medium", width: "65%",  color: "var(--color-warning, #DCB256)" },
  strong: { label: "Strong", width: "100%", color: "var(--color-success, #1B998B)" },
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

export function AccountSetupForm({ email }: AccountSetupFormProps) {
  const [firstName, setFirstName] = useState("");
  const [lastName,  setLastName]  = useState("");
  const [password,  setPassword]  = useState("");
  const [confirm,   setConfirm]   = useState("");
  const [errors,    setErrors]    = useState<Record<string, string>>({});
  const [loading,   setLoading]   = useState(false);

  const strength = calcStrength(password);
  const strengthMeta = STRENGTH_META[strength];

  function validate() {
    const e: Record<string, string> = {};
    if (!firstName.trim()) e.firstName = "First name is required";
    if (!lastName.trim())  e.lastName  = "Last name is required";
    if (password.length < 8) e.password = "Password must be at least 8 characters";
    if (confirm !== password) e.confirm = "Passwords do not match";
    return e;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    try {
      // TODO: wire up Supabase auth.updateUser({ password, data: { first_name, last_name } })
      await new Promise((r) => setTimeout(r, 800));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} noValidate>
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

        {/* First / Last name */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <Input
            label="First name"
            placeholder="e.g. Jordan"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            autoComplete="given-name"
            error={errors.firstName}
          />
          <Input
            label="Last name"
            placeholder="e.g. Smith"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            autoComplete="family-name"
            error={errors.lastName}
          />
        </div>

        {/* Locked email */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              fontWeight: 500,
              color: "var(--color-foreground, #2D3142)",
            }}
          >
            Email address{" "}
            <span
              style={{
                fontWeight: 400,
                color: "var(--color-muted-foreground, #4F5D75)",
                fontSize: "12px",
              }}
            >
              (locked)
            </span>
          </label>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 12px",
              border: "1px solid var(--color-border, #BFC0C0)",
              borderRadius: "var(--radius-md, 6px)",
              backgroundColor: "var(--color-muted, #E8E8E4)",
              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "13px",
              color: "var(--color-muted-foreground, #4F5D75)",
            }}
          >
            <LockClosedIcon style={{ width: 14, height: 14, flexShrink: 0 }} />
            {email}
          </div>
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              color: "var(--color-muted-foreground, #4F5D75)",
              margin: 0,
            }}
          >
            This is the email your invite was sent to — it cannot be changed here.
          </p>
        </div>

        {/* Create password */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <PasswordInput
            label="Create password"
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

        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={loading}
          style={{ width: "100%", marginTop: "4px" }}
        >
          {loading ? "Creating account…" : "Create Account"}
        </Button>
      </div>
    </form>
  );
}
