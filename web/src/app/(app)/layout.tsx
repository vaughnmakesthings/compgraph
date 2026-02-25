"use client";

import { redirect } from "next/navigation";
import { Shell } from "@/components/layout";
import { useAuth } from "@/lib/auth-context";
import { SkeletonBox } from "@/components/ui/skeleton";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { session, loading } = useAuth();

  if (loading) {
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
