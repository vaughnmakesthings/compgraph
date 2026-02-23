"use client";

import { useEffect, useMemo, useState } from "react";
import { KpiCard } from "@/components/data/kpi-card";
import { BarChart } from "@/components/charts/bar-chart";
import { api } from "@/lib/api-client";
import type { PipelineStatus, DailyVelocity } from "@/lib/types";

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function pipelineCardVariant(
  status: PipelineStatus["status"]
): "default" | "success" | "warning" {
  if (status === "idle") return "default";
  return "warning";
}


function SkeletonBox({ className }: { className?: string }) {
  return (
    <div
      className={className}
      style={{
        backgroundColor: "#E8E8E4",
        borderRadius: "var(--radius-lg, 8px)",
        animation: "pulse 1.5s ease-in-out infinite",
      }}
      aria-hidden="true"
    />
  );
}

interface DashboardData {
  status: PipelineStatus;
  velocity: DailyVelocity[];
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [status, velocity] = await Promise.all([
          api.getPipelineStatus(),
          api.getVelocity({ days: 14 }),
        ]);
        if (!cancelled) {
          setData({ status, velocity });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard data");
        }
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

  const derived = useMemo(() => {
    if (!data) return null;

    const { status, velocity } = data;

    const latestByCompany: Record<string, number> = {};
    for (const row of velocity) {
      latestByCompany[row.company_id] = row.active_postings;
    }
    const totalActive = Object.values(latestByCompany).reduce((s, n) => s + n, 0);

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);
    const newThisWeek = velocity
      .filter((r) => new Date(r.date) >= cutoff)
      .reduce((s, r) => s + r.new_postings, 0);

    const pass1 = status.enrich.current_run?.pass1_completed ?? 0;
    const pass2 = status.enrich.current_run?.pass2_completed ?? 0;
    const enrichmentPct =
      pass1 > 0 ? Math.round((pass2 / pass1) * 100) : null;

    const companies = [...new Set(velocity.map((r) => r.company_id))].sort();

    const chartRows: Record<string, unknown>[] = [];
    const dateMap = new Map<string, Record<string, number>>();
    for (const row of velocity) {
      if (!dateMap.has(row.date)) {
        dateMap.set(row.date, {});
      }
      dateMap.get(row.date)![row.company_id] = row.new_postings;
    }
    const sortedDates = [...dateMap.keys()].sort();
    for (const date of sortedDates) {
      const entry: Record<string, unknown> = { date };
      for (const co of companies) {
        entry[co] = dateMap.get(date)?.[co] ?? 0;
      }
      chartRows.push(entry);
    }

    const bars = companies.map((co) => {
      const sample = velocity.find((r) => r.company_id === co);
      return {
        dataKey: co,
        name: sample?.company_name ?? co,
      };
    });

    return {
      totalActive,
      newThisWeek,
      enrichmentPct,
      chartRows,
      bars,
      pipelineStatus: status.status,
      lastUpdated: status.scrape.last_completed_at,
    };
  }, [data]);

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display, 'Sora Variable', sans-serif)" }}
        >
          Pipeline Health
        </h1>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground)",
          }}
        >
          Hiring activity across tracked competitors
        </p>
      </div>

      {error && (
        <div
          className="mb-6 rounded-lg border px-4 py-3 text-sm"
          style={{
            backgroundColor: "#8C2C231A",
            borderColor: "#8C2C2333",
            color: "#8C2C23",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          }}
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="grid grid-cols-4 gap-4 mb-6">
        {loading ? (
          <>
            <SkeletonBox className="h-[96px]" />
            <SkeletonBox className="h-[96px]" />
            <SkeletonBox className="h-[96px]" />
            <SkeletonBox className="h-[96px]" />
          </>
        ) : derived ? (
          <>
            <KpiCard
              label="Active Postings"
              value={derived.totalActive.toLocaleString()}
            />
            <KpiCard
              label="New This Week"
              value={derived.newThisWeek.toLocaleString()}
            />
            <KpiCard
              label="Enriched"
              value={derived.enrichmentPct !== null ? `${derived.enrichmentPct}%` : "—"}
            />
            <KpiCard
              label="Pipeline Status"
              value={derived.pipelineStatus}
              variant={pipelineCardVariant(derived.pipelineStatus)}
            />
          </>
        ) : null}
      </div>

      <div
        className="rounded-lg border p-4 mb-4"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
        }}
      >
        <p
          className="text-sm font-medium mb-4"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "#2D3142",
          }}
        >
          Daily Posting Velocity
        </p>
        {loading ? (
          <SkeletonBox className="h-[280px]" />
        ) : derived && derived.chartRows.length > 0 ? (
          <BarChart
            data={derived.chartRows}
            bars={derived.bars}
            xDataKey="date"
            height={280}
          />
        ) : (
          <div
            className="flex items-center justify-center h-[280px] text-sm"
            style={{
              color: "var(--color-muted-foreground)",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            }}
          >
            No velocity data available
          </div>
        )}
      </div>

      {!loading && derived && (
        <div className="flex justify-end">
          <p
            className="text-xs"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              color: "var(--color-muted-foreground)",
            }}
          >
            Last updated: {formatTimestamp(derived.lastUpdated)}
          </p>
        </div>
      )}
    </div>
  );
}
