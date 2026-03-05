"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { KpiCard } from "@/components/data/kpi-card";
import { AreaChart } from "@/components/charts/area-chart";
import { SkeletonBox } from "@/components/ui/skeleton";
import {
  getVelocityApiV1AggregationVelocityGetOptions,
  getCoverageGapsApiV1AggregationCoverageGapsGetOptions
} from "@/api-client/@tanstack/react-query.gen";
import type { DailyVelocity, CoverageGap } from "@/lib/types";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-lg font-semibold font-body text-[#2D3142]">
      {children}
    </h2>
  );
}

export default function MarketPage() {
  const {
    data: velocity,
    isLoading: velocityLoading,
    error: velocityError
  } = useQuery({
    ...getVelocityApiV1AggregationVelocityGetOptions({
      query: { days: 30 }
    }),
    select: (data) => data as unknown as DailyVelocity[],
  });

  const {
    data: gaps,
    isLoading: gapsLoading,
    error: gapsError
  } = useQuery({
    ...getCoverageGapsApiV1AggregationCoverageGapsGetOptions(),
    select: (data) => data as unknown as CoverageGap[],
  });

  const loading = velocityLoading || gapsLoading;
  const error = (velocityError || gapsError) ? "Error loading market data" : null;

  const derived = useMemo(() => {
    if (!velocity || !gaps) return null;

    const latestActiveByCompany: Record<string, number> = {};
    const latestDateByCompany: Record<string, string> = {};
    const newLast7ByCompany: Record<string, number> = {};
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);

    for (const row of velocity) {
      if (!row.company_id || !row.date) continue;
      if (!(row.company_id in latestDateByCompany) || row.date > latestDateByCompany[row.company_id]) {
        latestDateByCompany[row.company_id] = row.date;
        latestActiveByCompany[row.company_id] = row.active_postings ?? 0;
      }
      if (row.date && new Date(row.date) >= cutoff) {
        newLast7ByCompany[row.company_id] =
          (newLast7ByCompany[row.company_id] ?? 0) + (row.new_postings ?? 0);
      }
    }

    const totalActive = Object.values(latestActiveByCompany).reduce((s, n) => s + n, 0);

    let mostActiveCompany = "\u2014";
    let maxNew = 0;
    for (const [company, count] of Object.entries(newLast7ByCompany)) {
      if (count > maxNew) {
        maxNew = count;
        const sample = velocity.find((r) => r.company_id === company);
        mostActiveCompany = sample?.company_name ?? company;
      }
    }

    const dateMap = new Map<string, number>();
    for (const row of velocity) {
      if (!row.date) continue;
      dateMap.set(row.date, (dateMap.get(row.date) ?? 0) + (row.new_postings ?? 0));
    }
    const chartRows = [...dateMap.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, total]) => ({ date, total }));

    return {
      totalActive,
      mostActiveCompany,
      gapCount: gaps.length,
      chartRows,
      gaps,
    };
  }, [velocity, gaps]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight font-display text-[#2D3142]">
          Market Overview
        </h1>
        <p className="mt-1 text-sm font-body text-[#4F5D75]">
          Hiring velocity and competitive positioning
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-[#8C2C2333] px-4 py-3 text-sm bg-[#8C2C231A] text-[#8C2C23] font-body" role="alert">
          {error}
        </div>
      )}

      <div
        className="grid grid-cols-3 gap-4 mb-6"
        aria-label="Market KPI metrics"
        aria-busy={loading}
      >
        {loading ? (
          <>
            <SkeletonBox className="h-[96px]" />
            <SkeletonBox className="h-[96px]" />
            <SkeletonBox className="h-[96px]" />
          </>
        ) : derived ? (
          <>
            <KpiCard
              label="Total Active Postings"
              value={derived.totalActive.toLocaleString()}
            />
            <KpiCard
              label="Most Active Company"
              value={derived.mostActiveCompany}
            />
            <KpiCard
              label="Coverage Gaps"
              value={derived.gapCount}
              variant={derived.gapCount > 0 ? "warning" : "success"}
            />
          </>
        ) : null}
      </div>

      <div className="mt-6 mb-3">
        <SectionHeading>Posting Velocity</SectionHeading>
      </div>
      <div className="rounded-lg border border-[#BFC0C0] p-4 mb-6 bg-white shadow-sm">
        {loading ? (
          <SkeletonBox className="h-[260px]" />
        ) : derived && derived.chartRows.length > 0 ? (
          <AreaChart
            data={derived.chartRows}
            areas={[{ dataKey: "total", name: "Total Market" }]}
            xDataKey="date"
            height={260}
          />
        ) : (
          <div className="flex items-center justify-center h-[260px] text-sm text-[#4F5D75] font-body">
            No velocity data available
          </div>
        )}
      </div>

      <div className="mt-6">
        <SectionHeading>Coverage Gaps</SectionHeading>
        <div className="mt-3 rounded-lg border border-[#BFC0C0] overflow-hidden bg-white">
          {loading ? (
            <SkeletonBox className="h-24" />
          ) : !derived || derived.gaps.length === 0 ? (
            <p className="px-4 py-6 text-sm text-center text-[#4F5D75] font-body">
              No coverage gaps detected
            </p>
          ) : (
            <table className="w-full text-sm" aria-label="Coverage gaps by market">
              <thead>
                <tr>
                  <th className="text-left px-4 py-2 text-[11px] font-semibold text-[#4F5D75] opacity-50 font-body uppercase tracking-widest">
                    Market
                  </th>
                  <th className="text-left px-4 py-2 text-[11px] font-semibold text-[#4F5D75] opacity-50 font-body uppercase tracking-widest">
                    Missing Companies
                  </th>
                </tr>
              </thead>
              <tbody>
                {derived.gaps.map((gap, i) => (
                  <tr
                    key={`${gap.market}-${gap.state}-${i}`}
                    className="border-b last:border-b-0 border-[#BFC0C0]"
                  >
                    <td className="px-4 py-2 text-[#2D3142] font-body">
                      {gap.market}, {gap.state}
                    </td>
                    <td className="px-4 py-2 text-[#4F5D75] font-body">
                      {gap.companies_absent?.join(", ") ?? "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
