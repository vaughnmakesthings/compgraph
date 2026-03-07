"use client";

import { useState, useEffect } from "react";
import { SectionCard } from "@/components/ui/section-card";
import { UserTable } from "./user-table";
import { api } from "@/lib/api-client";
import type { AuthUser as AuthUserType } from "@/lib/types";

export type UserRole = "admin" | "user" | "viewer";
export type UserStatus = "active" | "invite_sent" | "disabled";

export interface AppUser {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  joinedAt: string | null;
  lastLoginAt: string | null;
  isCurrentUser?: boolean;
}

function authUserToAppUser(u: AuthUserType): AppUser {
  const emailPrefix = u.email.split("@")[0] ?? "";
  const parts = emailPrefix.split(/[._-]/);
  const firstName = parts[0] ? parts[0].charAt(0).toUpperCase() + parts[0].slice(1) : "User";
  const lastName = parts[1] ? parts[1].charAt(0).toUpperCase() + parts[1].slice(1) : "";

  let status: UserStatus = "active";
  if (!u.confirmed_at) {
    status = "invite_sent";
  }

  const role: UserRole = (u.role === "admin" || u.role === "user" || u.role === "viewer") ? u.role : "viewer";

  return {
    id: u.id,
    firstName,
    lastName: lastName || "User",
    email: u.email,
    role,
    status,
    joinedAt: u.confirmed_at ?? u.created_at,
    lastLoginAt: u.last_sign_in_at,
  };
}

function StatCell({ num, label, last }: { num: number; label: string; last?: boolean }) {
  return (
    <div style={{ flex: 1, padding: "10px 14px", borderRight: last ? "none" : "1px solid #E8E8E4", textAlign: "center" }}>
      <div style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", fontSize: 22, fontWeight: 700, color: "#2D3142" }}>{num}</div>
      <div style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: 10, color: "#4F5D75", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: 2 }}>{label}</div>
    </div>
  );
}

export function UserManagementSection() {
  const [users, setUsers] = useState<AppUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAuthUsers()
      .then((authUsers) => {
        setUsers(authUsers.map(authUserToAppUser));
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load users");
      })
      .finally(() => setLoading(false));
  }, []);

  const total = users.length;
  const active = users.filter((u) => u.status === "active").length;
  const pending = users.filter((u) => u.status === "invite_sent").length;
  const admins = users.filter((u) => u.role === "admin").length;

  return (
    <SectionCard
      title="User Management"
      action={
        <span style={{ fontSize: 11, color: "#4F5D75", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}>
          Admin only
        </span>
      }
    >
      {loading ? (
        <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: 13, color: "#4F5D75" }}>Loading users...</p>
      ) : error ? (
        <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: 13, color: "#8C2C23" }}>{error}</p>
      ) : (
        <>
          <div style={{ display: "flex", border: "1px solid #E8E8E4", borderRadius: 6, overflow: "hidden", marginBottom: 20 }}>
            <StatCell num={total} label="Total users" />
            <StatCell num={active} label="Active" />
            <StatCell num={pending} label="Pending" />
            <StatCell num={admins} label="Admins" last />
          </div>

          <UserTable
            users={users}
            currentUserId={undefined}
            existingEmails={users.map((u) => u.email)}
            onUserUpdated={(updated) => setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))}
            onUserRemoved={(id) => setUsers((prev) => prev.filter((u) => u.id !== id))}
            onUserInvited={(user) => setUsers((prev) => [...prev, user])}
          />
        </>
      )}
    </SectionCard>
  );
}
