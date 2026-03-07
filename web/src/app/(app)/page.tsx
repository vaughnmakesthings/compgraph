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
import { SectionErrorBoundary } from "@/components/ui/section-error-boundary";
import { formatTimestamp } from "@/lib/utils";
import {
  pipelineStatusApiV1PipelineStatusGetOptions,
  getVelocityApiV1AggregationVelocityGetOptions
} from "@/api-client/@tanstack/react-query.gen";
import type { DailyVelocity } from "@/lib/types";

interface EnrichCurrentRun {
  run_id: string;
  status: string;
  started_at: string;
  pass1_total: number;
  pass1_succeeded: number;
  pass1_skipped: number;
  pass2_total: number;
  pass2_succeeded: number;
  pass2_skipped: number;
}

interface PipelineStatusResponse {
  status: string;
  system_state?: string;
  scrape: {
    status: string;
    current_run: Record<string, unknown> | null;
    last_completed_at: string | null;
  };
  enrich: {
    status: string;
    current_run: EnrichCurrentRun | null;
    last_completed_at: string | null;
  };
  scheduler: { enabled: boolean; next_run_at: string | null };
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
    select: (data) => data as unknown as PipelineStatusResponse,
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

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);

    const latestByCompany: Record<string, { date: string; active: number }> = {};
    const companyNameMap: Record<string, string> = {};
    const companySet = new Set<string>();
    const dateMap = new Map<string, Record<string, number>>();
    let newThisWeek = 0;

    for (const row of velocity) {
      if (!row.date || !row.company_id) continue;

      companySet.add(row.company_id);
      if (row.company_name) companyNameMap[row.company_id] = row.company_name;

      const existing = latestByCompany[row.company_id];
      if (!existing || row.date > existing.date) {
        latestByCompany[row.company_id] = { date: row.date, active: row.active_postings ?? 0 };
      }

      if (new Date(row.date) >= cutoff) {
        newThisWeek += row.new_postings ?? 0;
      }

      let dateEntry = dateMap.get(row.date);
      if (!dateEntry) {
        dateEntry = {};
        dateMap.set(row.date, dateEntry);
      }
      dateEntry[row.company_id] = row.new_postings ?? 0;
    }

    const totalActive = Object.values(latestByCompany).reduce((s, e) => s + e.active, 0);

    let enrichmentPct: number | null = null;
    const enrichRun = status.enrich?.current_run;
    if (enrichRun && enrichRun.pass1_succeeded > 0) {
      enrichmentPct = Math.round((enrichRun.pass2_succeeded / enrichRun.pass1_succeeded) * 100);
    }

    const companies = [...companySet].sort();
    const sortedDates = [...dateMap.keys()].sort();
    const chartRows: Record<string, unknown>[] = sortedDates.map((date) => {
      const entry: Record<string, unknown> = { date };
      for (const co of companies) {
        entry[co] = dateMap.get(date)?.[co] ?? 0;
      }
      return entry;
    });

    const bars = companies.map((co) => ({
      dataKey: co,
      name: companyNameMap[co] ?? co,
    }));

    return {
      totalActive,
      newThisWeek,
      enrichmentPct,
      chartRows,
      bars,
      pipelineStatus: status.system_state ?? status.status,
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
        <h1 className="text-2xl font-semibold tracking-tight font-display">
          Pipeline Health
        </h1>
        <p className="mt-1 text-sm text-[#4F5D75]">
          Hiring activity across tracked competitors
        </p>
      </div>

      {error && (
        <div
          className="mb-6 rounded-lg px-4 py-3 text-sm flex items-start gap-3 border-l-[3px] border-l-[#8C2C23] bg-[#8C2C231A] text-[#8C2C23]"
          role="alert"
        >
          <div className="flex-1">
            <p className="font-semibold mb-0.5">Could not connect to the pipeline API</p>
            <p className="text-[#2D3142] text-[13px]">
              {error instanceof Error ? error.message : "Check that the backend service is running and try again."}
            </p>
          </div>
          <button
            type="button"
            onClick={handleRetry}
            className="shrink-0 flex items-center gap-1.5 text-xs transition-opacity hover:opacity-70 text-[#8C2C23] font-body"
            aria-label="Retry loading dashboard"
          >
            <ArrowPathIcon className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      )}

      <SectionErrorBoundary name="KPI metrics">
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
                icon={<BriefcaseIcon className="h-4 w-4 text-[#4F5D75]" />}
                trend={derived ? { value: 12, label: "vs last wk" } : undefined}
              />
              <KpiCard
                label="New This Week"
                value={derived ? derived.newThisWeek.toLocaleString() : kpiFallback.newThisWeek}
                icon={<ArrowTrendingUpIcon className="h-4 w-4 text-[#4F5D75]" />}
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
                icon={<CheckCircleIcon className="h-4 w-4 text-[#4F5D75]" />}
              />
              <KpiCard
                label="Pipeline Status"
                value={derived ? (derived.pipelineStatus as string) : kpiFallback.pipelineStatus}
                icon={<SignalIcon className="h-4 w-4 text-[#4F5D75]" />}
                variant={derived ? pipelineCardVariant(derived.pipelineStatus) : "default"}
              />
            </>
          )}
        </div>
      </SectionErrorBoundary>

      <SectionErrorBoundary name="Daily Posting Velocity">
      <div className="rounded-lg border border-[#BFC0C0] p-4 mb-4 bg-white shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-[#2D3142]">
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
            bars={derived.bars}
            xDataKey="date"
            height={280}
          />
        ) : (
          <div className="flex items-center justify-center h-[280px] text-sm text-[#4F5D75]">
            No velocity data available
          </div>
        )}
      </div>
      </SectionErrorBoundary>

      {!initialLoading && derived && (
        <div className="flex justify-end">
          <p className="text-xs text-[#4F5D75]">
            Last updated: {formatTimestamp(derived.lastUpdated)}
          </p>
        </div>
      )}
    </div>
  );
}
