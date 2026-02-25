"use client";

import { useState } from "react";
import { EnvelopeIcon } from "@heroicons/react/24/outline";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { api } from "@/lib/api-client";
import type { AppUser, UserRole } from "./user-management-section";

interface InviteUserFormProps {
  onInvited: (user: AppUser) => void;
  existingEmails: string[];
}

export function InviteUserForm({ onInvited, existingEmails }: InviteUserFormProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("user");
  const [emailError, setEmailError] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);

  function validate(): boolean {
    const trimmed = email.trim().toLowerCase();
    if (!trimmed) {
      setEmailError("Email is required");
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setEmailError("Enter a valid email address");
      return false;
    }
    if (existingEmails.map((e) => e.toLowerCase()).includes(trimmed)) {
      setEmailError("This email is already in the system");
      return false;
    }
    setEmailError("");
    return true;
  }

  function handleSubmitClick() {
    if (validate()) setConfirmOpen(true);
  }

  async function handleConfirm() {
    const trimmed = email.trim().toLowerCase();
    try {
      const response = await api.inviteUser({ email: trimmed, role });
      const newUser: AppUser = {
        id: response.user_id,
        firstName: trimmed.split("@")[0] ?? "New",
        lastName: "User",
        email: response.email,
        role: response.role as UserRole,
        status: "invite_sent",
        joinedAt: null,
        lastLoginAt: null,
      };
      onInvited(newUser);
      toast.success(`Invite sent to ${trimmed}`);
      setEmail("");
      setRole("user");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to send invite");
    }
  }

  return (
    <>
      <div
        style={{
          backgroundColor: "#F7F7F5",
          border: "1px solid #E8E8E4",
          borderRadius: "6px",
          padding: "14px 16px",
          marginBottom: "16px",
        }}
      >
        <p
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "12px",
            fontWeight: 600,
            color: "#2D3142",
            marginBottom: "10px",
          }}
        >
          ✉ Invite a new user
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 160px auto",
            gap: "10px",
            alignItems: "flex-start",
          }}
        >
          {/* Email input */}
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <div style={{ position: "relative" }}>
              <EnvelopeIcon
                style={{
                  position: "absolute",
                  left: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  width: 15,
                  height: 15,
                  color: "#4F5D75",
                  pointerEvents: "none",
                }}
              />
              <input
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (emailError) setEmailError("");
                }}
                placeholder="colleague@company.com"
                autoComplete="email"
                style={{
                  width: "100%",
                  padding: "9px 12px 9px 32px",
                  fontSize: "13px",
                  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                  color: "#2D3142",
                  backgroundColor: "#FFFFFF",
                  border: `1px solid ${emailError ? "#8C2C23" : "#BFC0C0"}`,
                  borderRadius: "var(--radius-md, 6px)",
                  outline: "none",
                  boxSizing: "border-box",
                }}
                onFocus={(e) =>
                  (e.currentTarget.style.borderColor = emailError ? "#8C2C23" : "#2D3142")
                }
                onBlur={(e) =>
                  (e.currentTarget.style.borderColor = emailError ? "#8C2C23" : "#BFC0C0")
                }
              />
            </div>
            {emailError && (
              <p
                style={{
                  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "12px",
                  color: "#8C2C23",
                  margin: 0,
                }}
              >
                {emailError}
              </p>
            )}
          </div>

          {/* Role select */}
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            style={{
              padding: "9px 28px 9px 10px",
              fontSize: "13px",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              color: "#2D3142",
              backgroundColor: "#FFFFFF",
              border: "1px solid #BFC0C0",
              borderRadius: "var(--radius-md, 6px)",
              outline: "none",
              appearance: "auto",
              cursor: "pointer",
              boxSizing: "border-box",
              width: "100%",
            }}
            onFocus={(e) => (e.currentTarget.style.borderColor = "#2D3142")}
            onBlur={(e) => (e.currentTarget.style.borderColor = "#BFC0C0")}
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>

          {/* Send button */}
          <Button variant="primary" size="md" onClick={handleSubmitClick}>
            Send Invite
          </Button>
        </div>

        <p
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "11px",
            color: "#BFC0C0",
            marginTop: "8px",
          }}
        >
          The recipient will receive a magic link by email. Link expires in 72 hours.
        </p>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Send invite?"
        description={`An invite email will be sent to ${email.trim()}. They'll be assigned the "${role}" role and can complete account setup via the magic link.`}
        confirmLabel="Send invite"
        onConfirm={handleConfirm}
      />
    </>
  );
}
