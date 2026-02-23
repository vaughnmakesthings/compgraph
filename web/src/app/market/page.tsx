"use client";

import { useEffect, useMemo, useState } from "react";
import { KpiCard } from "@/components/data/kpi-card";
import { AreaChart } from "@/components/charts/area-chart";
import { api } from "@/lib/api-client";
import type { DailyVelocity, CoverageGap } from "@/lib/types";

interface MarketData {
  velocity: DailyVelocity[];
  gaps: CoverageGap[];
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="text-lg font-semibold"
      style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", color: "#2D3142" }}
    >
      {children}
    </h2>
  );
}

function SkeletonBox({ className }: { className?: string }) {
  return (
    <div
      className={className}
      style={{ backgroundColor: "#E8E8E4", borderRadius: "var(--radius-lg, 8px)" }}
      aria-hidden="true"
    />
  );
}

export default function MarketPage() {
  const [data, setData] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [velocity, gaps] = await Promise.all([
          api.getVelocity({ days: 30 }),
          api.getCoverageGaps(),
        ]);
        if (!cancelled) {
          setData({ velocity, gaps });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load market data");
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
    const { velocity, gaps } = data;

    const latestActiveByCompany: Record<string, number> = {};
    const newLast7ByCompany: Record<string, number> = {};
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);

    for (const row of velocity) {
      latestActiveByCompany[row.company_id] = row.active_postings;
      if (new Date(row.date) >= cutoff) {
        newLast7ByCompany[row.company_id] =
          (newLast7ByCompany[row.company_id] ?? 0) + row.new_postings;
      }
    }

    const totalActive = Object.values(latestActiveByCompany).reduce((s, n) => s + n, 0);

    let mostActiveCompany = "—";
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
      dateMap.set(row.date, (dateMap.get(row.date) ?? 0) + row.new_postings);
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
  }, [data]);

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display, 'Sora Variable', sans-serif)", color: "#2D3142" }}
        >
          Market Overview
        </h1>
        <p
          className="mt-1 text-sm"
          style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", color: "#4F5D75" }}
        >
          Hiring velocity and competitive positioning
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

      <div className="grid grid-cols-3 gap-4 mb-6">
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
      <div
        className="rounded-lg border p-4 mb-6"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
        }}
      >
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
          <div
            className="flex items-center justify-center h-[260px] text-sm"
            style={{ color: "#4F5D75", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
          >
            No velocity data available
          </div>
        )}
      </div>

      <div className="mt-6">
        <SectionHeading>Coverage Gaps</SectionHeading>
        <div
          className="mt-3 rounded-lg border overflow-hidden"
          style={{ borderColor: "#BFC0C0", backgroundColor: "#FFFFFF" }}
        >
          {loading ? (
            <SkeletonBox className="h-24" />
          ) : !derived || derived.gaps.length === 0 ? (
            <p
              className="px-4 py-6 text-sm text-center"
              style={{ color: "#4F5D75", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
            >
              No coverage gaps detected
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr style={{ backgroundColor: "#E8E8E4" }}>
                  <th
                    className="text-left px-4 py-2 font-semibold"
                    style={{ color: "#2D3142", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
                  >
                    Market
                  </th>
                  <th
                    className="text-left px-4 py-2 font-semibold"
                    style={{ color: "#2D3142", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
                  >
                    Missing Companies
                  </th>
                </tr>
              </thead>
              <tbody>
                {derived.gaps.map((gap, i) => (
                  <tr
                    key={`${gap.market}-${gap.state}-${i}`}
                    className="border-b last:border-b-0"
                    style={{ borderColor: "#BFC0C0" }}
                  >
                    <td
                      className="px-4 py-2"
                      style={{ color: "#2D3142", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
                    >
                      {gap.market}, {gap.state}
                    </td>
                    <td
                      className="px-4 py-2"
                      style={{ color: "#4F5D75", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
                    >
                      {gap.companies_absent.join(", ")}
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
