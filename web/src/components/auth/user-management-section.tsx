"use client";

import { useState } from "react";
import { SectionCard } from "@/components/ui/section-card";
import { UserTable } from "./user-table";

export type UserRole = "admin" | "user";
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

const MOCK_USERS: AppUser[] = [
  { id: "u-1", firstName: "Alice", lastName: "Johnson", email: "alice@mosaicsales.com", role: "admin", status: "active", joinedAt: "2026-01-10T00:00:00Z", lastLoginAt: "2026-02-25T14:22:00Z", isCurrentUser: true },
  { id: "u-2", firstName: "Bob", lastName: "Martinez", email: "bob@mosaicsales.com", role: "user", status: "active", joinedAt: "2026-01-15T00:00:00Z", lastLoginAt: "2026-02-24T09:10:00Z" },
  { id: "u-3", firstName: "Carol", lastName: "Singh", email: "carol@mosaicsales.com", role: "user", status: "invite_sent", joinedAt: null, lastLoginAt: null },
  { id: "u-4", firstName: "Dan", lastName: "Lee", email: "dan@mosaicsales.com", role: "user", status: "active", joinedAt: "2026-02-01T00:00:00Z", lastLoginAt: "2026-02-22T17:45:00Z" },
];

function StatCell({ num, label, last }: { num: number; label: string; last?: boolean }) {
  return (
    <div style={{ flex: 1, padding: "10px 14px", borderRight: last ? "none" : "1px solid #E8E8E4", textAlign: "center" }}>
      <div style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", fontSize: 22, fontWeight: 700, color: "#2D3142" }}>{num}</div>
      <div style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: 10, color: "#4F5D75", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: 2 }}>{label}</div>
    </div>
  );
}

export function UserManagementSection() {
  const [users, setUsers] = useState<AppUser[]>(MOCK_USERS);

  const total = users.length;
  const active = users.filter((u) => u.status === "active").length;
  const pending = users.filter((u) => u.status === "invite_sent").length;
  const admins = users.filter((u) => u.role === "admin").length;

  const currentUser = users.find((u) => u.isCurrentUser);

  return (
    <SectionCard
      title="User Management"
      action={
        <span style={{ fontSize: 11, color: "#4F5D75", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}>
          🔒 Admin only
        </span>
      }
    >
      {/* Stats bar */}
      <div style={{ display: "flex", border: "1px solid #E8E8E4", borderRadius: 6, overflow: "hidden", marginBottom: 20 }}>
        <StatCell num={total} label="Total users" />
        <StatCell num={active} label="Active" />
        <StatCell num={pending} label="Pending" />
        <StatCell num={admins} label="Admins" last />
      </div>

      {/* Table (owns the Add/Edit dialogs and "Add user" button) */}
      <UserTable
        users={users}
        currentUserId={currentUser?.id}
        existingEmails={users.map((u) => u.email)}
        onUserUpdated={(updated) => setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))}
        onUserRemoved={(id) => setUsers((prev) => prev.filter((u) => u.id !== id))}
        onUserInvited={(user) => setUsers((prev) => [...prev, user])}
      />
    </SectionCard>
  );
}
