"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
} from "@headlessui/react";
import { Dialog as TremorDialog, DialogPanel as TremorDialogPanel } from "@tremor/react";
import { ChevronDownIcon } from "@heroicons/react/20/solid";
import { MagnifyingGlassIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import type { AppUser, UserRole } from "./user-management-section";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SortColumn = "name" | "joined" | "lastLogin";
type SortDir = "asc" | "desc";

export interface UserTableProps {
  users: AppUser[];
  currentUserId?: string;
  existingEmails: string[];
  onUserUpdated: (user: AppUser) => void;
  onUserRemoved: (userId: string) => void;
  onUserInvited: (user: AppUser) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const BODY = "var(--font-body, 'DM Sans Variable', sans-serif)";
const MONO = "var(--font-mono, 'JetBrains Mono Variable', monospace)";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Status / Role pills
// ---------------------------------------------------------------------------

const STATUS_PILL: Record<AppUser["status"], { label: string; bg: string; color: string }> = {
  active: { label: "Active", bg: "#1B998B1A", color: "#1B998B" },
  invite_sent: { label: "Invite sent", bg: "#DCB2561A", color: "#A07820" },
  disabled: { label: "Disabled", bg: "#E8E8E4", color: "#4F5D75" },
};
const ROLE_PILL: Record<AppUser["role"], { label: string; bg: string; color: string }> = {
  admin: { label: "Admin", bg: "#2D31421A", color: "#2D3142" },
  user: { label: "User", bg: "#E8E8E4", color: "#4F5D75" },
};

function Pill({ bg, color, label }: { bg: string; color: string; label: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        backgroundColor: bg,
        color,
        borderRadius: 4,
        padding: "2px 8px",
        fontSize: 11,
        fontFamily: BODY,
        fontWeight: 600,
        whiteSpace: "nowrap",
        letterSpacing: "0.02em",
      }}
    >
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Filter controls
// ---------------------------------------------------------------------------

function SearchInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ position: "relative", flex: "1 1 200px", minWidth: 160 }}>
      <MagnifyingGlassIcon
        style={{
          position: "absolute",
          left: 10,
          top: "50%",
          transform: "translateY(-50%)",
          width: 14,
          height: 14,
          color: "#9CA3AF",
          pointerEvents: "none",
        }}
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search name or email…"
        className="w-full rounded-md border border-gray-300 bg-white py-2 pr-3 pl-8 text-sm text-gray-900 placeholder-gray-400 focus:border-gray-500 focus:outline-none"
      />
    </div>
  );
}

function FilterSelect({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-gray-300 bg-white py-2 pr-8 pl-3 text-sm text-gray-700 focus:border-gray-500 focus:outline-none"
      style={{ minWidth: 130, appearance: "auto", cursor: "pointer" }}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

// ---------------------------------------------------------------------------
// Sortable column header
// ---------------------------------------------------------------------------

function SortTh({
  label,
  column,
  sort,
  onSort,
  className = "",
}: {
  label: string;
  column: SortColumn;
  sort: { column: SortColumn; dir: SortDir } | null;
  onSort: (c: SortColumn) => void;
  className?: string;
}) {
  const isActive = sort?.column === column;
  const isAsc = isActive && sort?.dir === "asc";
  return (
    <th
      scope="col"
      className={`py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 ${className}`}
    >
      <button
        type="button"
        onClick={() => onSort(column)}
        className="group inline-flex items-center gap-1"
      >
        {label}
        <span
          className={[
            "ml-1 flex-none rounded",
            isActive
              ? "bg-gray-100 text-gray-700"
              : "invisible text-gray-400 group-hover:visible group-focus:visible",
          ].join(" ")}
        >
          <ChevronDownIcon
            aria-hidden
            className={`size-4 transition-transform ${isAsc ? "rotate-180" : ""}`}
          />
        </span>
      </button>
    </th>
  );
}

// ---------------------------------------------------------------------------
// Shared dialog field helpers
// ---------------------------------------------------------------------------

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label
        style={{
          fontFamily: BODY,
          fontSize: 11,
          fontWeight: 600,
          color: "#6B7280",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </label>
      <div>{children}</div>
    </div>
  );
}

function ReadonlyField({ value }: { value: string }) {
  return (
    <div
      style={{
        fontFamily: BODY,
        fontSize: 14,
        color: "#2D3142",
        padding: "9px 12px",
        backgroundColor: "#F7F7F5",
        border: "1px solid #E8E8E4",
        borderRadius: 6,
      }}
    >
      {value}
    </div>
  );
}

function RoleSelect({ value, onChange }: { value: UserRole; onChange: (r: UserRole) => void }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as UserRole)}
      style={{
        width: "100%",
        padding: "9px 28px 9px 12px",
        fontSize: 14,
        fontFamily: BODY,
        color: "#2D3142",
        backgroundColor: "#FFFFFF",
        border: "1px solid #BFC0C0",
        borderRadius: 6,
        outline: "none",
        appearance: "auto",
        cursor: "pointer",
        boxSizing: "border-box",
      }}
      onFocus={(e) => (e.currentTarget.style.borderColor = "#2D3142")}
      onBlur={(e) => (e.currentTarget.style.borderColor = "#BFC0C0")}
    >
      <option value="user">User</option>
      <option value="admin">Admin</option>
    </select>
  );
}

// ---------------------------------------------------------------------------
// AddUserDialog (centered modal — Tremor, kept as-is)
// ---------------------------------------------------------------------------

interface AddUserDialogProps {
  open: boolean;
  onClose: () => void;
  existingEmails: string[];
  onInvited: (user: AppUser) => void;
}

function AddUserDialog({ open, onClose, existingEmails, onInvited }: AddUserDialogProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("user");
  const [emailError, setEmailError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setEmail("");
    setRole("user");
    setEmailError("");
    setSubmitting(false);
  }

  function handleClose() {
    reset();
    onClose();
  }

  function validate() {
    const t = email.trim().toLowerCase();
    if (!t) { setEmailError("Email is required"); return false; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(t)) { setEmailError("Enter a valid email address"); return false; }
    if (existingEmails.map((e) => e.toLowerCase()).includes(t)) { setEmailError("This email is already in the system"); return false; }
    setEmailError("");
    return true;
  }

  async function handleSubmit() {
    if (!validate()) return;
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 700));
    const t = email.trim().toLowerCase();
    onInvited({
      id: `u-${Date.now()}`,
      firstName: t.split("@")[0] ?? "New",
      lastName: "User",
      email: t,
      role,
      status: "invite_sent",
      joinedAt: null,
      lastLoginAt: null,
    });
    toast.success(`Invite sent to ${t}`);
    handleClose();
  }

  return (
    <TremorDialog open={open} onClose={handleClose}>
      <TremorDialogPanel
        className="max-w-md w-full"
        style={{
          backgroundColor: "#FFFFFF",
          border: "1px solid #BFC0C0",
          borderRadius: 10,
          padding: 0,
          boxShadow: "0 20px 40px -8px rgb(0 0 0 / 0.18)",
          fontFamily: BODY,
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "20px 24px 16px",
            borderBottom: "1px solid #E8E8E4",
          }}
        >
          <div>
            <h3
              style={{
                fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
                fontSize: 16,
                fontWeight: 600,
                color: "#2D3142",
                margin: 0,
              }}
            >
              Add user
            </h3>
            <p style={{ fontFamily: BODY, fontSize: 13, color: "#4F5D75", margin: "3px 0 0" }}>
              Send a magic-link invite to a new team member.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#4F5D75", padding: 4, borderRadius: 4 }}
          >
            <XMarkIcon style={{ width: 18, height: 18 }} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
          <FieldRow label="Email address">
            <Input
              type="email"
              placeholder="colleague@company.com"
              value={email}
              onChange={(e) => { setEmail(e.target.value); if (emailError) setEmailError(""); }}
              error={emailError}
              autoComplete="email"
            />
          </FieldRow>
          <FieldRow label="Role">
            <RoleSelect value={role} onChange={setRole} />
            <p style={{ fontFamily: BODY, fontSize: 12, color: "#4F5D75", marginTop: 6 }}>
              <strong style={{ color: "#2D3142" }}>User</strong> — read-only access.{" "}
              <strong style={{ color: "#2D3142" }}>Admin</strong> — full access including user management.
            </p>
          </FieldRow>
          <p style={{ fontFamily: BODY, fontSize: 12, color: "#BFC0C0", margin: 0 }}>
            The recipient will receive a magic link by email. Link expires in 72 hours.
          </p>
        </div>

        <div
          style={{
            padding: "0 24px 20px",
            display: "flex",
            justifyContent: "flex-end",
            gap: 10,
            borderTop: "1px solid #E8E8E4",
            paddingTop: 16,
          }}
        >
          <button
            type="button"
            onClick={handleClose}
            style={{ fontFamily: BODY, fontSize: 14, padding: "8px 16px", borderRadius: 6, border: "1px solid #BFC0C0", color: "#4F5D75", background: "transparent", cursor: "pointer" }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={submitting}
            style={{ fontFamily: BODY, fontSize: 14, padding: "8px 16px", borderRadius: 6, border: "none", color: "#FFFFFF", backgroundColor: "#EF8354", cursor: submitting ? "not-allowed" : "pointer", opacity: submitting ? 0.5 : 1 }}
          >
            {submitting ? "Sending…" : "Send invite"}
          </button>
        </div>
      </TremorDialogPanel>
    </TremorDialog>
  );
}

// ---------------------------------------------------------------------------
// EditUserDialog — Headless UI slide-over drawer
// ---------------------------------------------------------------------------

interface EditUserDialogProps {
  user: AppUser | null;
  currentUserId?: string;
  onClose: () => void;
  onUserUpdated: (user: AppUser) => void;
  onUserRemoved: (userId: string) => void;
}

// Wrapper — renders nothing when no user is selected (keeps hooks clean)
function EditUserDialog(props: EditUserDialogProps) {
  if (!props.user) return null;
  return <EditUserDrawer {...props} user={props.user} />;
}

type DestructiveAction = "reset-password" | "disable" | "resend-invite" | "cancel-invite";

function EditUserDrawer({
  user,
  currentUserId,
  onClose,
  onUserUpdated,
  onUserRemoved,
}: EditUserDialogProps & { user: AppUser }) {
  const [role, setRole] = useState<UserRole>(user.role);
  const [confirmAction, setConfirmAction] = useState<DestructiveAction | null>(null);

  const isSelf = user.id === currentUserId;
  const isPending = user.status === "invite_sent";
  const roleChanged = role !== user.role;
  const name = `${user.firstName} ${user.lastName}`;
  const initials = `${user.firstName[0] ?? ""}${user.lastName[0] ?? ""}`.toUpperCase();

  function handleClose() {
    setRole(user.role);
    setConfirmAction(null);
    onClose();
  }

  async function handleSave() {
    if (!roleChanged) return;
    await new Promise((r) => setTimeout(r, 400));
    onUserUpdated({ ...user, role });
    toast.success(`${name}'s role updated to ${role}`);
    onClose();
  }

  async function handleConfirmAction() {
    await new Promise((r) => setTimeout(r, 600));
    if (confirmAction === "reset-password") {
      toast.success(`Password reset email sent to ${user.email}`);
    } else if (confirmAction === "disable") {
      onUserRemoved(user.id);
      toast.success(`${name} has been disabled`);
      onClose();
    } else if (confirmAction === "resend-invite") {
      toast.success(`Invite resent to ${user.email}`);
    } else if (confirmAction === "cancel-invite") {
      onUserRemoved(user.id);
      toast.success(`Invite cancelled for ${user.email}`);
      onClose();
    }
  }

  const confirmMeta: Record<DestructiveAction, { title: string; description: string; label: string; variant: "default" | "danger" }> = {
    "reset-password": {
      title: "Reset password?",
      description: `A password reset email will be sent to ${user.email}. The current password remains valid until they reset it.`,
      label: "Send reset email",
      variant: "default",
    },
    "disable": {
      title: `Disable ${name}?`,
      description: `${name} will immediately lose access to CompGraph. This cannot be undone without re-inviting them.`,
      label: "Disable user",
      variant: "danger",
    },
    "resend-invite": {
      title: "Resend invite?",
      description: `A new magic link will be sent to ${user.email}. The previous link will be invalidated.`,
      label: "Resend invite",
      variant: "default",
    },
    "cancel-invite": {
      title: `Cancel invite for ${user.email}?`,
      description: "The pending magic link will be invalidated. You can re-invite them at any time.",
      label: "Cancel invite",
      variant: "danger",
    },
  };

  return (
    <>
      {/* Slide-over drawer */}
      <Dialog open onClose={handleClose} className="relative z-40">
        {/* Transparent overlay (no backdrop blur) */}
        <div className="fixed inset-0" />

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10 sm:pl-16">
              <DialogPanel
                transition
                className="pointer-events-auto w-screen max-w-md transform transition duration-500 ease-in-out data-closed:translate-x-full sm:duration-700"
              >
                <div className="relative flex h-full flex-col overflow-y-auto bg-white shadow-xl">

                  {/* ── Coloured header band ─────────────────────── */}
                  <div style={{ backgroundColor: "#2D3142", padding: "24px 20px 20px 24px" }}>
                    <div className="flex items-center justify-between">
                      <DialogTitle
                        as="div"
                        className="flex items-center gap-3"
                      >
                        {/* Avatar */}
                        <div
                          style={{
                            width: 40,
                            height: 40,
                            borderRadius: "50%",
                            backgroundColor: "rgba(255,255,255,0.15)",
                            border: "1.5px solid rgba(255,255,255,0.3)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontFamily: BODY,
                            fontSize: 14,
                            fontWeight: 700,
                            color: "#FFFFFF",
                            flexShrink: 0,
                          }}
                        >
                          {initials}
                        </div>
                        <div>
                          <p
                            style={{
                              fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
                              fontSize: 16,
                              fontWeight: 600,
                              color: "#FFFFFF",
                              margin: 0,
                              lineHeight: 1.2,
                            }}
                          >
                            {name}
                          </p>
                          <p style={{ fontFamily: MONO, fontSize: 12, color: "rgba(255,255,255,0.55)", margin: "3px 0 0" }}>
                            {user.email}
                          </p>
                        </div>
                      </DialogTitle>

                      {/* Close */}
                      <div className="ml-3 flex h-7 items-center">
                        <button
                          type="button"
                          onClick={handleClose}
                          className="relative rounded-md text-white/60 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                        >
                          <span className="absolute -inset-2.5" />
                          <span className="sr-only">Close panel</span>
                          <XMarkIcon aria-hidden className="size-5" />
                        </button>
                      </div>
                    </div>

                    {/* Status + role pills under name */}
                    <div className="mt-3 flex items-center gap-2 flex-wrap">
                      <Pill {...STATUS_PILL[user.status]} />
                      <Pill {...ROLE_PILL[user.role]} />
                      {isSelf && (
                        <span
                          style={{
                            fontFamily: BODY,
                            fontSize: 11,
                            color: "rgba(255,255,255,0.5)",
                            fontStyle: "italic",
                          }}
                        >
                          (you)
                        </span>
                      )}
                    </div>
                  </div>

                  {/* ── Body ─────────────────────────────────────── */}
                  <div className="relative flex-1 px-6 py-6 space-y-5">

                    {/* Role */}
                    {!isSelf ? (
                      <FieldRow label="Role">
                        <RoleSelect value={role} onChange={setRole} />
                        <p style={{ fontFamily: BODY, fontSize: 12, color: "#6B7280", marginTop: 6 }}>
                          <strong style={{ color: "#2D3142" }}>Admin</strong> — full access including user management.
                        </p>
                      </FieldRow>
                    ) : (
                      <FieldRow label="Role">
                        <div style={{ paddingTop: 4 }}>
                          <Pill {...ROLE_PILL[user.role]} />
                          <p style={{ fontFamily: BODY, fontSize: 12, color: "#6B7280", marginTop: 6 }}>
                            You cannot change your own role.
                          </p>
                        </div>
                      </FieldRow>
                    )}

                    {/* Joined / Last Login */}
                    {!isPending && (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                        <FieldRow label="Joined">
                          <ReadonlyField value={formatDate(user.joinedAt)} />
                        </FieldRow>
                        <FieldRow label="Last login">
                          <ReadonlyField value={formatDate(user.lastLoginAt)} />
                        </FieldRow>
                      </div>
                    )}

                    {isPending && (
                      <div
                        style={{
                          backgroundColor: "#FDF8EC",
                          border: "1px solid #F0D98A",
                          borderRadius: 6,
                          padding: "10px 14px",
                          fontFamily: BODY,
                          fontSize: 13,
                          color: "#A07820",
                        }}
                      >
                        Waiting for the user to complete account setup via the invite link.
                      </div>
                    )}

                    {/* Danger actions */}
                    {!isSelf && (
                      <div
                        style={{
                          borderTop: "1px solid #E8E8E4",
                          paddingTop: 20,
                          marginTop: 8,
                        }}
                      >
                        <p
                          style={{
                            fontFamily: BODY,
                            fontSize: 11,
                            fontWeight: 600,
                            color: "#9CA3AF",
                            textTransform: "uppercase",
                            letterSpacing: "0.06em",
                            marginBottom: 12,
                          }}
                        >
                          {isPending ? "Invite actions" : "Account actions"}
                        </p>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                          {isPending ? (
                            <>
                              <DangerRow
                                label="Resend invite"
                                description="Send a new magic link. The previous link will be invalidated."
                                onClick={() => setConfirmAction("resend-invite")}
                                variant="neutral"
                              />
                              <DangerRow
                                label="Cancel invite"
                                description="Revoke the pending invite for this email address."
                                onClick={() => setConfirmAction("cancel-invite")}
                                variant="danger"
                              />
                            </>
                          ) : (
                            <>
                              <DangerRow
                                label="Reset password"
                                description="Send a password reset email to this user."
                                onClick={() => setConfirmAction("reset-password")}
                                variant="neutral"
                              />
                              <DangerRow
                                label="Disable user"
                                description="Immediately revoke access. Cannot be undone without re-inviting."
                                onClick={() => setConfirmAction("disable")}
                                variant="danger"
                              />
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* ── Footer ───────────────────────────────────── */}
                  <div
                    style={{
                      padding: "16px 24px",
                      borderTop: "1px solid #E8E8E4",
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: 10,
                      backgroundColor: "#FAFAFA",
                    }}
                  >
                    <button
                      type="button"
                      onClick={handleClose}
                      style={{ fontFamily: BODY, fontSize: 14, padding: "8px 16px", borderRadius: 6, border: "1px solid #BFC0C0", color: "#4F5D75", background: "transparent", cursor: "pointer" }}
                    >
                      {isSelf || isPending ? "Close" : "Cancel"}
                    </button>
                    {!isSelf && !isPending && (
                      <button
                        type="button"
                        onClick={() => void handleSave()}
                        disabled={!roleChanged}
                        style={{
                          fontFamily: BODY,
                          fontSize: 14,
                          padding: "8px 16px",
                          borderRadius: 6,
                          border: "none",
                          color: "#FFFFFF",
                          backgroundColor: "#EF8354",
                          cursor: !roleChanged ? "not-allowed" : "pointer",
                          opacity: !roleChanged ? 0.45 : 1,
                        }}
                      >
                        Save changes
                      </button>
                    )}
                  </div>
                </div>
              </DialogPanel>
            </div>
          </div>
        </div>
      </Dialog>

      {/* Nested confirm dialog for destructive actions */}
      {confirmAction && (
        <ConfirmDialog
          open={!!confirmAction}
          onOpenChange={(o) => { if (!o) setConfirmAction(null); }}
          title={confirmMeta[confirmAction].title}
          description={confirmMeta[confirmAction].description}
          confirmLabel={confirmMeta[confirmAction].label}
          confirmVariant={confirmMeta[confirmAction].variant}
          onConfirm={handleConfirmAction}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// DangerRow — action row inside the drawer
// ---------------------------------------------------------------------------

function DangerRow({
  label,
  description,
  onClick,
  variant,
}: {
  label: string;
  description: string;
  onClick: () => void;
  variant: "neutral" | "danger";
}) {
  const [hov, setHov] = useState(false);
  const color = variant === "danger" ? "#8C2C23" : "#2D3142";
  const hoverBg = variant === "danger" ? "rgba(140,44,35,0.05)" : "rgba(45,49,66,0.04)";

  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        width: "100%",
        textAlign: "left",
        padding: "10px 14px",
        borderRadius: 8,
        border: `1px solid ${hov ? color + "55" : "#E8E8E4"}`,
        backgroundColor: hov ? hoverBg : "transparent",
        cursor: "pointer",
        transition: "all 140ms",
      }}
    >
      <div>
        <p style={{ fontFamily: BODY, fontSize: 13, fontWeight: 600, color, margin: 0 }}>{label}</p>
        <p style={{ fontFamily: BODY, fontSize: 12, color: "#6B7280", margin: "2px 0 0" }}>{description}</p>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// UserTable
// ---------------------------------------------------------------------------

export function UserTable({
  users,
  currentUserId,
  existingEmails,
  onUserUpdated,
  onUserRemoved,
  onUserInvited,
}: UserTableProps) {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sort, setSort] = useState<{ column: SortColumn; dir: SortDir } | null>(null);
  const [addUserOpen, setAddUserOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<AppUser | null>(null);

  function handleSort(col: SortColumn) {
    setSort((prev) => ({
      column: col,
      dir: prev?.column === col && prev.dir === "asc" ? "desc" : "asc",
    }));
  }

  const displayedUsers = useMemo(() => {
    let result = users;
    const q = search.trim().toLowerCase();
    if (q) result = result.filter((u) => `${u.firstName} ${u.lastName}`.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
    if (roleFilter) result = result.filter((u) => u.role === roleFilter);
    if (statusFilter) result = result.filter((u) => u.status === statusFilter);
    if (sort) {
      result = [...result].sort((a, b) => {
        const aVal = sort.column === "name"
          ? `${a.firstName} ${a.lastName}`
          : sort.column === "joined"
          ? (a.joinedAt ?? "")
          : (a.lastLoginAt ?? "");
        const bVal = sort.column === "name"
          ? `${b.firstName} ${b.lastName}`
          : sort.column === "joined"
          ? (b.joinedAt ?? "")
          : (b.lastLoginAt ?? "");
        return sort.dir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      });
    }
    return result;
  }, [users, search, roleFilter, statusFilter, sort]);

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h2
            className="text-base font-semibold"
            style={{ fontFamily: "var(--font-display, 'Sora Variable', sans-serif)", color: "#2D3142" }}
          >
            Users
          </h2>
          <p className="mt-1 text-sm" style={{ fontFamily: BODY, color: "#4F5D75" }}>
            Manage team members, invite new users, and control access levels.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <button
            type="button"
            onClick={() => setAddUserOpen(true)}
            className="block rounded-md px-3 py-2 text-center text-sm font-semibold text-white shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{ backgroundColor: "#EF8354", fontFamily: BODY }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(239,131,84,0.85)")}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#EF8354")}
          >
            Add user
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <SearchInput value={search} onChange={setSearch} />
        <FilterSelect
          value={roleFilter}
          onChange={setRoleFilter}
          options={[
            { value: "", label: "All roles" },
            { value: "admin", label: "Admin" },
            { value: "user", label: "User" },
          ]}
        />
        <FilterSelect
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: "", label: "All statuses" },
            { value: "active", label: "Active" },
            { value: "invite_sent", label: "Invite sent" },
            { value: "disabled", label: "Disabled" },
          ]}
        />
      </div>

      {/* Table */}
      <div className="mt-6 flow-root">
        <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <SortTh label="Name" column="name" sort={sort} onSort={handleSort} className="pl-4 pr-3 sm:pl-0" />
                  <th scope="col" className="px-3 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Email
                  </th>
                  <th scope="col" className="px-3 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Role
                  </th>
                  <th scope="col" className="px-3 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <SortTh label="Joined" column="joined" sort={sort} onSort={handleSort} className="px-3" />
                  <SortTh label="Last Login" column="lastLogin" sort={sort} onSort={handleSort} className="px-3" />
                  <th scope="col" className="py-3.5 pl-3 pr-0">
                    <span className="sr-only">Edit</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {displayedUsers.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="py-8 text-center text-sm text-gray-400"
                      style={{ fontFamily: BODY }}
                    >
                      No users match your filters.
                    </td>
                  </tr>
                ) : (
                  displayedUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="py-4 pr-3 pl-4 align-top sm:pl-0">
                        <div className="text-sm font-semibold whitespace-nowrap text-gray-900" style={{ fontFamily: BODY }}>
                          {user.firstName} {user.lastName}
                        </div>
                        {user.id === currentUserId && (
                          <div className="text-xs text-gray-400" style={{ fontFamily: BODY }}>You</div>
                        )}
                      </td>
                      <td className="px-3 py-4 align-top">
                        <span className="text-sm whitespace-nowrap text-gray-500" style={{ fontFamily: MONO, fontSize: 12 }}>
                          {user.email}
                        </span>
                      </td>
                      <td className="px-3 py-4 align-top whitespace-nowrap">
                        <Pill {...ROLE_PILL[user.role]} />
                      </td>
                      <td className="px-3 py-4 align-top whitespace-nowrap">
                        <Pill {...STATUS_PILL[user.status]} />
                      </td>
                      <td className="px-3 py-4 align-top whitespace-nowrap">
                        <span className="text-sm text-gray-500" style={{ fontFamily: MONO, fontSize: 12 }}>
                          {formatDate(user.joinedAt)}
                        </span>
                      </td>
                      <td className="px-3 py-4 align-top whitespace-nowrap">
                        <span className="text-sm text-gray-500" style={{ fontFamily: MONO, fontSize: 12 }}>
                          {formatDate(user.lastLoginAt)}
                        </span>
                      </td>
                      <td className="py-4 pl-3 pr-4 text-right align-top whitespace-nowrap sm:pr-0">
                        <button
                          type="button"
                          onClick={() => setEditingUser(user)}
                          className="text-sm font-medium hover:underline underline-offset-2"
                          style={{ background: "none", border: "none", cursor: "pointer", color: "#EF8354", fontFamily: BODY, padding: "2px 0" }}
                        >
                          Edit<span className="sr-only">, {user.firstName} {user.lastName}</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Row count */}
      <p className="mt-2 text-right text-xs text-gray-400" style={{ fontFamily: BODY }}>
        {displayedUsers.length} of {users.length} user{users.length !== 1 ? "s" : ""} shown
      </p>

      {/* Dialogs */}
      <AddUserDialog
        open={addUserOpen}
        onClose={() => setAddUserOpen(false)}
        existingEmails={existingEmails}
        onInvited={onUserInvited}
      />
      <EditUserDialog
        user={editingUser}
        currentUserId={currentUserId}
        onClose={() => setEditingUser(null)}
        onUserUpdated={(u) => { onUserUpdated(u); setEditingUser(null); }}
        onUserRemoved={(id) => { onUserRemoved(id); setEditingUser(null); }}
      />
    </div>
  );
}
