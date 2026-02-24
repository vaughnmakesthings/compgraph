"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { COMPANIES } from "@/lib/constants";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// Breadcrumb derivation from pathname
interface Crumb {
  label: string;
  href?: string;
}

function deriveCrumbs(pathname: string): Crumb[] {
  if (pathname === "/") {
    return [{ label: "Dashboard", href: "/" }, { label: "Pipeline Health" }];
  }

  // Competitor dossier: /competitors/[slug]
  const competitorMatch = /^\/competitors\/([^/]+)$/.exec(pathname);
  if (competitorMatch) {
    const slug = competitorMatch[1];
    const company = COMPANIES.find((c) => c.slug === slug);
    return [
      { label: "Competitors", href: "/competitors" },
      { label: company?.name ?? slug },
    ];
  }

  const ROUTE_MAP: Record<string, Crumb[]> = {
    "/competitors":    [{ label: "Competitors" }],
    "/prospects":      [{ label: "Prospects" }],
    "/market":         [{ label: "Market Overview" }],
    "/hiring":         [{ label: "Job Feed" }],
    "/eval":           [{ label: "Eval" }],
    "/eval/runs":      [{ label: "Eval", href: "/eval" }, { label: "Runs" }],
    "/eval/review":    [{ label: "Eval", href: "/eval" }, { label: "Review" }],
    "/eval/accuracy":  [{ label: "Eval", href: "/eval" }, { label: "Accuracy" }],
    "/eval/leaderboard": [{ label: "Eval", href: "/eval" }, { label: "Leaderboard" }],
    "/eval/prompt-diff": [{ label: "Eval", href: "/eval" }, { label: "Run Diff" }],
    "/settings":       [{ label: "Settings" }],
  };

  return ROUTE_MAP[pathname] ?? [{ label: pathname.replace("/", "").replace(/-/g, " ") }];
}

type ApiStatus = "checking" | "ok" | "error";

export function Header() {
  const pathname = usePathname();
  const crumbs = deriveCrumbs(pathname);

  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(5000) })
      .then((r) => {
        if (!cancelled) setApiStatus(r.ok ? "ok" : "error");
      })
      .catch(() => {
        if (!cancelled) setApiStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const dotColor =
    apiStatus === "ok" ? "#1B998B" : apiStatus === "error" ? "#8C2C23" : "#BFC0C0";
  const dotLabel =
    apiStatus === "ok" ? "API connected" : apiStatus === "error" ? "API unreachable" : "Checking API…";

  return (
    <header
      className="flex h-14 shrink-0 items-center justify-between border-b px-6"
      style={{
        backgroundColor: "var(--color-surface)",
        borderColor: "var(--color-border)",
      }}
    >
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb">
        <ol className="flex items-center gap-1.5">
          {crumbs.map((crumb, i) => {
            const isLast = i === crumbs.length - 1;
            return (
              <li key={i} className="flex items-center gap-1.5">
                {i > 0 && (
                  <span
                    className="text-xs"
                    style={{ color: "rgba(79,93,117,0.4)" }}
                    aria-hidden="true"
                  >
                    ›
                  </span>
                )}
                {!isLast && crumb.href ? (
                  <Link
                    href={crumb.href}
                    className="text-[13px] transition-colors duration-150 hover:opacity-80"
                    style={{
                      fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                      color: "var(--color-muted-foreground)",
                    }}
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span
                    className="text-[13px]"
                    style={{
                      fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                      color: isLast
                        ? "var(--color-foreground)"
                        : "var(--color-muted-foreground)",
                      fontWeight: isLast ? 500 : 400,
                    }}
                  >
                    {crumb.label}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </nav>

      {/* API status indicator */}
      <div className="flex items-center gap-2">
        <span
          className="h-2 w-2 rounded-full transition-colors duration-300"
          style={{ backgroundColor: dotColor }}
          aria-hidden="true"
        />
        <span
          className="text-xs"
          style={{ color: "var(--color-muted-foreground)" }}
        >
          {dotLabel}
        </span>
      </div>
    </header>
  );
}
