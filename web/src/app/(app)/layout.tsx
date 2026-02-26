"use client";

import { redirect } from "next/navigation";
import { Shell } from "@/components/layout";
import { useAuth } from "@/lib/auth-context";
import { SkeletonBox } from "@/components/ui/skeleton";

/** Check if URL hash contains a Supabase auth token (invite/recovery/magic link) */
function hasAuthHash(): boolean {
  if (typeof window === "undefined") return false;
  const hash = window.location.hash;
  return hash.includes("access_token=") || hash.includes("type=invite") || hash.includes("type=recovery");
}

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { session, loading } = useAuth();

  // Show loading while auth is initializing or while Supabase processes hash tokens
  if (loading || (!session && hasAuthHash())) {
    return (
      <div
        role="status"
        aria-busy="true"
        aria-label="Loading application"
        style={{
          display: "flex",
          height: "100vh",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <SkeletonBox style={{ width: 200, height: 24 }} />
      </div>
    );
  }

  if (!session) {
    redirect("/login");
  }

  return <Shell>{children}</Shell>;
}
