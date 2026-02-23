"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/data/badge";
import { api } from "@/lib/api-client";
import type { DailyVelocity } from "@/lib/types";
import { COMPANIES, type Company } from "@/lib/constants";

function CompanyCard({
  company,
  activePostings,
  loading,
  onClick,
}: {
  company: Company;
  activePostings: number | null;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left"
      style={{ display: "block" }}
    >
      <div
        style={{
          backgroundColor: "#FFFFFF",
          border: "1px solid #BFC0C0",
          borderLeft: "3px solid #EF8354",
          borderRadius: "var(--radius-lg, 8px)",
          padding: "20px",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
          transition: "box-shadow 150ms ease",
          cursor: "pointer",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow =
            "var(--shadow-md, 0 4px 6px -1px rgb(0 0 0 / 0.08))";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow =
            "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))";
        }}
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2
            className="font-semibold"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "15px",
              color: "#2D3142",
              lineHeight: "1.3",
            }}
          >
            {company.name}
          </h2>
          <Badge variant="neutral" size="sm">
            {company.ats}
          </Badge>
        </div>
        <div className="flex items-baseline gap-1">
          <span
            style={{
              fontFamily:
                "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "24px",
              fontWeight: 600,
              color: loading ? "#BFC0C0" : "#2D3142",
              lineHeight: 1,
            }}
          >
            {loading ? "—" : (activePostings ?? 0).toLocaleString()}
          </span>
          <span
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              color: "#4F5D75",
            }}
          >
            active postings
          </span>
        </div>
      </div>
    </button>
  );
}

export default function CompetitorsPage() {
  const router = useRouter();
  const [velocity, setVelocity] = useState<DailyVelocity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await api.getVelocity();
        if (!cancelled) {
          setVelocity(data);
        }
      } catch {
        // Non-critical — cards show "0" if velocity unavailable
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const activeByCompanyName = useMemo(() => {
    const latestDate: Record<string, string> = {};
    const latestCount: Record<string, number> = {};
    for (const row of velocity) {
      const name = row.company_name ?? "";
      if (!(name in latestDate) || row.date > latestDate[name]) {
        latestDate[name] = row.date;
        latestCount[name] = row.active_postings;
      }
    }
    return latestCount;
  }, [velocity]);

  function resolveActivePostings(company: Company): number | null {
    const count = activeByCompanyName[company.name];
    return count !== undefined ? count : null;
  }

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
          }}
        >
          Competitors
        </h1>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground)",
          }}
        >
          Field marketing agencies in our competitive set
        </p>
      </div>

      <div
        className="grid gap-4"
        style={{
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
        }}
      >
        {COMPANIES.map((company) => (
          <CompanyCard
            key={company.slug}
            company={company}
            activePostings={resolveActivePostings(company)}
            loading={loading}
            onClick={() => router.push(`/competitors/${company.slug}`)}
          />
        ))}
      </div>
    </div>
  );
}
