"use client";

import { useState, useSyncExternalStore, useCallback } from "react";
import { cn } from "@/lib/utils";
import { SIDEBAR_WIDTH, SIDEBAR_WIDTH_COLLAPSED } from "@/lib/constants";
import { Sidebar } from "@/components/sidebar";
import { Header } from "@/components/header";

const SIDEBAR_KEY = "sidebar-collapsed";
const emptySubscribe = () => () => {};

interface AppShellProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export function AppShell({ title, subtitle, children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      return localStorage.getItem(SIDEBAR_KEY) === "true";
    } catch {
      return false;
    }
  });
  const hydrated = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );

  const handleToggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_KEY, String(next));
      } catch {
        // localStorage unavailable — toggle still works in-memory
      }
      return next;
    });
  }, []);

  return (
    <div className={cn("min-h-screen bg-background", !hydrated && "opacity-0")} aria-busy={!hydrated}>
      <Sidebar collapsed={collapsed} onToggle={handleToggle} />
      <div
        className="flex min-h-screen flex-col transition-[padding] duration-200 ease-in-out"
        style={{ paddingLeft: collapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH }}
      >
        <Header title={title} subtitle={subtitle} />
        <main id="main-content" className="noise-bg flex-1 bg-surface-content p-6">
          <div className="relative z-[1]">{children}</div>
        </main>
      </div>
    </div>
  );
}
