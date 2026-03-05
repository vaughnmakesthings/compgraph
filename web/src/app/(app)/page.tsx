/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BriefcaseIcon,
  ArrowTrendingUpIcon,
  CheckCircleIcon,
  SignalIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { KpiCard } from "@/components/data/kpi-card";
import { BarChart } from "@/components/charts/bar-chart";
import { SkeletonBox } from "@/components/ui/skeleton";
import { 
  pipelineStatusApiV1PipelineStatusGetOptions, 
  getVelocityApiV1AggregationVelocityGetOptions 
} from "@/api-client/@tanstack/react-query.gen";
import type { PipelineStatus, DailyVelocity } from "@/lib/types";

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function pipelineCardVariant(
  status: string | undefined
): "default" | "success" | "warning" {
  if (status === "idle") return "success";
  return "default";
}

type ChartDays = 14 | 30 | 90;

export default function DashboardPage() {
  const [chartDays, setChartDays] = useState<ChartDays>(14);

  const {
    data: status,
    isLoading: statusLoading,
    error: statusError,
    refetch: refetchStatus,
  } = useQuery({
    ...pipelineStatusApiV1PipelineStatusGetOptions(),
    select: (data) => data as unknown as PipelineStatus,
  });

  const {
    data: velocity,
    isLoading: velocityLoading,
    error: velocityError,
    refetch: refetchVelocity,
  } = useQuery({
    ...getVelocityApiV1AggregationVelocityGetOptions({ 
      query: { days: chartDays } 
    }),
    select: (data) => data as unknown as DailyVelocity[],
  });

  const error = statusError || velocityError;
  const initialLoading = statusLoading || (velocityLoading && !velocity);

  const derived = useMemo(() => {
    if (!status || !velocity) return null;

    const latestByCompany: Record<string, { date: string; active: number }> = {};
    for (const row of velocity) {
      if (!row.company_id || !row.date) continue;
      const existing = latestByCompany[row.company_id];
      if (!existing || row.date > existing.date) {
        latestByCompany[row.company_id] = { 
          date: row.date, 
          active: row.active_postings ?? 0 
        };
      }
    }
    const totalActive = Object.values(latestByCompany).reduce((s, e) => s + e.active, 0);

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);
    const newThisWeek = velocity
      .filter((r) => r.date && new Date(r.date) >= cutoff)
      .reduce((s, r) => s + (r.new_postings ?? 0), 0);

    let enrichmentPct: number | null = null;
    const enrichRun = status.enrich.current_run;
    if (enrichRun && enrichRun.pass1_completed > 0) {
      enrichmentPct = Math.round((enrichRun.pass2_completed / enrichRun.pass1_completed) * 100);
    }

    const companies = [...new Set(velocity.map((r) => r.company_id!).filter(Boolean))].sort();

    const chartRows: Record<string, unknown>[] = [];
    const dateMap = new Map<string, Record<string, number>>();
    for (const row of velocity) {
      if (!row.date || !row.company_id) continue;
      if (!dateMap.has(row.date)) {
        dateMap.set(row.date, {});
      }
      dateMap.get(row.date)![row.company_id] = row.new_postings ?? 0;
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
  }, [status, velocity]);

  // KPI fallback values shown on error
  const kpiFallback = {
    totalActive: "—",
    newThisWeek: "—",
    enrichmentPct: "—",
    pipelineStatus: "—" as const,
  };

  const handleRetry = () => {
    void refetchStatus();
    void refetchVelocity();
  };

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
          style={{ color: "var(--color-muted-foreground)" }}
        >
          Hiring activity across tracked competitors
        </p>
      </div>

      {error && (
        <div
          className="mb-6 rounded-lg px-4 py-3 text-sm flex items-start gap-3"
          style={{
            borderLeft: "3px solid #8C2C23",
            backgroundColor: "#8C2C231A",
            color: "#8C2C23",
          }}
          role="alert"
        >
          <div className="flex-1">
            <p className="font-semibold mb-0.5">Could not connect to the pipeline API</p>
            <p style={{ color: "#2D3142", fontSize: "13px" }}>
              {error instanceof Error ? error.message : "Check that the backend service is running and try again."}
            </p>
          </div>
          <button
            type="button"
            onClick={handleRetry}
            className="shrink-0 flex items-center gap-1.5 text-xs transition-opacity hover:opacity-70"
            style={{
              color: "#8C2C23",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            }}
            aria-label="Retry loading dashboard"
          >
            <ArrowPathIcon className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      )}

      <div
        className="grid grid-cols-4 gap-4 mb-6"
        aria-busy={initialLoading}
        aria-label="KPI metrics"
      >
        {initialLoading ? (
          <>
            <SkeletonBox className="h-[96px]" />
            <SkeletonBox className="h-[96px]" />
            <SkeletonBox className="h-[96px]" />
            <SkeletonBox className="h-[96px]" />
          </>
        ) : (
          <>
            <KpiCard
              label="Active Postings"
              value={derived ? derived.totalActive.toLocaleString() : kpiFallback.totalActive}
              icon={<BriefcaseIcon className="h-4 w-4" style={{ color: "#4F5D75" }} />}
              trend={derived ? { value: 12, label: "vs last wk" } : undefined}
            />
            <KpiCard
              label="New This Week"
              value={derived ? derived.newThisWeek.toLocaleString() : kpiFallback.newThisWeek}
              icon={<ArrowTrendingUpIcon className="h-4 w-4" style={{ color: "#4F5D75" }} />}
              trend={derived ? { value: 8, label: "vs prev wk" } : undefined}
            />
            <KpiCard
              label="Enriched"
              value={
                derived
                  ? derived.enrichmentPct !== null
                    ? `${derived.enrichmentPct}%`
                    : "—"
                  : kpiFallback.enrichmentPct
              }
              icon={<CheckCircleIcon className="h-4 w-4" style={{ color: "#4F5D75" }} />}
            />
            <KpiCard
              label="Pipeline Status"
              value={derived ? (derived.pipelineStatus as string) : kpiFallback.pipelineStatus}
              icon={<SignalIcon className="h-4 w-4" style={{ color: "#4F5D75" }} />}
              variant={derived ? pipelineCardVariant(derived.pipelineStatus) : "default"}
            />
          </>
        )}
      </div>

      <div
        className="rounded-lg border p-4 mb-4"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2
            className="text-sm font-medium"
            style={{ color: "#2D3142" }}
          >
            Daily Posting Velocity
          </h2>
          <div className="flex items-center gap-1" role="group" aria-label="Time range">
            {([14, 30, 90] as ChartDays[]).map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setChartDays(d)}
                className="text-xs rounded px-2 py-1 transition-colors duration-150"
                style={{
                  fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                  backgroundColor:
                    chartDays === d ? "#2D3142" : "transparent",
                  color:
                    chartDays === d ? "#FFFFFF" : "#4F5D75",
                  border:
                    chartDays === d
                      ? "1px solid #2D3142"
                      : "1px solid #BFC0C0",
                }}
                aria-pressed={chartDays === d}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {initialLoading || velocityLoading ? (
          <SkeletonBox className="h-[280px]" />
        ) : derived && derived.chartRows.length > 0 ? (
          <BarChart
            data={derived.chartRows}
            bars={derived.bars as any}
            xDataKey="date"
            height={280}
          />
        ) : (
          <div
            className="flex items-center justify-center h-[280px] text-sm"
            style={{ color: "var(--color-muted-foreground)" }}
          >
            No velocity data available
          </div>
        )}
      </div>

      {!initialLoading && derived && (
        <div className="flex justify-end">
          <p
            className="text-xs"
            style={{ color: "var(--color-muted-foreground)" }}
          >
            Last updated: {formatTimestamp(derived.lastUpdated)}
          </p>
        </div>
      )}
    </div>
  );
}
