"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { KpiCard } from "@/components/data/kpi-card";
import { Badge } from "@/components/data/badge";
import { Callout } from "@/components/content/callout";
import { BarChart } from "@/components/charts/bar-chart";
import { api } from "@/lib/api-client";
import type {
  DailyVelocity,
  PayBenchmark,
  BrandTimeline,
  PostingListItem,
} from "@/lib/types";
import { COMPANIES } from "@/lib/constants";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
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

interface DossierData {
  velocity: DailyVelocity[];
  payBenchmarks: PayBenchmark[];
  brandTimeline: BrandTimeline[];
  postings: PostingListItem[];
  lastUpdatedAt: string | null;
}

export default function CompetitorDossierPage() {
  const params = useParams();
  const slug = typeof params.slug === "string" ? params.slug : (params.slug?.[0] ?? "");

  const company = COMPANIES.find((c) => c.slug === slug);

  const [data, setData] = useState<DossierData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    async function load() {
      try {
        const [velocity, payBenchmarks, brandTimeline] = await Promise.all([
          api.getVelocity(),
          api.getPayBenchmarks(),
          api.getBrandTimeline(),
        ]);
        // Get the company UUID from velocity data (filtered by slug)
        const companyRow = velocity.find((r) => r.company_slug === slug);
        const postingsResp = await api.listPostings({
          limit: 20,
          ...(companyRow?.company_id ? { company_id: companyRow.company_id } : {}),
        });
        if (!cancelled) {
          setData({
            velocity,
            payBenchmarks,
            brandTimeline,
            postings: postingsResp.items,
            lastUpdatedAt: null,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load competitor data",
          );
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
  }, [slug]);

  const derived = useMemo(() => {
    if (!data || !company) return null;

    const { velocity, payBenchmarks, brandTimeline } = data;

    const companyVelocity = velocity.filter(
      (r) => r.company_slug === slug,
    );

    const latestRow = companyVelocity.sort((a, b) =>
      b.date.localeCompare(a.date),
    )[0];
    const activePostings = latestRow?.active_postings ?? 0;

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);
    const newThisWeek = companyVelocity
      .filter((r) => new Date(r.date) >= cutoff)
      .reduce((s, r) => s + r.new_postings, 0);

    const companyPayBenchmarks = payBenchmarks.filter(
      (p) => p.company_id === latestRow?.company_id,
    );

    const payMinFiltered = companyPayBenchmarks.filter(
      (p) => p.pay_min_avg !== null,
    );
    const avgPayMin =
      payMinFiltered.length > 0
        ? payMinFiltered.reduce((s, p) => s + (p.pay_min_avg ?? 0), 0) /
          payMinFiltered.length
        : null;

    const topRole =
      companyPayBenchmarks.length > 0
        ? companyPayBenchmarks.reduce((best, curr) =>
            curr.sample_size > best.sample_size ? curr : best,
          ).role_archetype
        : null;

    const payChartData = companyPayBenchmarks
      .filter((p) => p.pay_min_avg !== null || p.pay_max_avg !== null)
      .map((p) => ({
        role: p.role_archetype,
        "Pay Min": Math.round(p.pay_min_avg ?? 0),
        "Pay Max": Math.round(p.pay_max_avg ?? 0),
      }));

    const companyBrandTimeline = brandTimeline.filter(
      (b) => b.company_slug === slug,
    );

    const topBrand =
      companyBrandTimeline.length > 0
        ? companyBrandTimeline.reduce<BrandTimeline>(
            (best, curr) =>
              curr.posting_count > best.posting_count ? curr : best,
            companyBrandTimeline[0],
          )
        : null;

    return {
      activePostings,
      newThisWeek,
      avgPayMin,
      topRole,
      payChartData,
      topBrand,
      companyId: latestRow?.company_id ?? null,
    };
  }, [data, company]);

  if (!company) {
    return (
      <div
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          color: "#4F5D75",
          padding: "2rem 0",
        }}
      >
        Company not found.
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-start gap-3 mb-6 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap mb-1">
            <h1
              style={{
                fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
                fontSize: "28px",
                fontWeight: 700,
                color: "#2D3142",
                lineHeight: "1.2",
              }}
            >
              {company.name}
            </h1>
            <Badge variant="neutral">{company.ats}</Badge>
          </div>
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#4F5D75",
            }}
          >
            Last updated: {formatTimestamp(data?.lastUpdatedAt ?? null)}
          </p>
        </div>
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

      {/* KPI Row */}
      <div
        className="grid gap-4 mb-6"
        style={{ gridTemplateColumns: "repeat(4, 1fr)" }}
      >
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
              value={derived.activePostings.toLocaleString()}
            />
            <KpiCard
              label="New This Week"
              value={derived.newThisWeek.toLocaleString()}
            />
            <KpiCard
              label="Avg Pay Min"
              value={
                derived.avgPayMin !== null
                  ? `$${Math.round(derived.avgPayMin).toLocaleString()}`
                  : "—"
              }
            />
            <KpiCard label="Top Role" value={derived.topRole ?? "—"} />
          </>
        ) : null}
      </div>

      {/* Brand Callout */}
      {!loading && derived?.topBrand && (
        <div className="mb-6">
          <Callout variant="finding" title="Top Brand Relationship">
            Primary brand partner:{" "}
            <strong>{derived.topBrand.brand_name}</strong> —{" "}
            {derived.topBrand.posting_count.toLocaleString()} postings
          </Callout>
        </div>
      )}

      {/* Pay Benchmarks Chart */}
      <div
        className="rounded-lg border p-4 mb-6"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
        }}
      >
        <h2
          className="text-sm font-medium mb-4"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "#2D3142",
          }}
        >
          Pay Benchmarks by Role
        </h2>
        {loading ? (
          <SkeletonBox className="h-[240px]" />
        ) : derived && derived.payChartData.length > 0 ? (
          <BarChart
            data={derived.payChartData}
            bars={[
              { dataKey: "Pay Min", name: "Pay Min" },
              { dataKey: "Pay Max", name: "Pay Max" },
            ]}
            xDataKey="role"
            height={240}
          />
        ) : (
          <div
            className="flex items-center justify-center h-[240px] text-sm"
            style={{
              color: "#4F5D75",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            }}
          >
            No pay benchmark data available
          </div>
        )}
      </div>

      {/* Job Postings Table */}
      <div
        className="rounded-lg border overflow-hidden"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
        }}
      >
        <div
          className="px-4 py-3 border-b"
          style={{ borderColor: "#BFC0C0" }}
        >
          <h2
            className="text-sm font-medium"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              color: "#2D3142",
            }}
          >
            Job Postings
          </h2>
        </div>
        {loading ? (
          <div className="p-4">
            <SkeletonBox className="h-[200px]" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr
                  style={{
                    backgroundColor: "#E8E8E4",
                    borderBottom: "1px solid #BFC0C0",
                  }}
                >
                  {["Title", "Location", "Role", "Status", "First Seen"].map(
                    (col) => (
                      <th
                        key={col}
                        className="text-left px-4 py-2"
                        style={{
                          fontFamily:
                            "var(--font-body, 'DM Sans Variable', sans-serif)",
                          fontSize: "11px",
                          fontWeight: 600,
                          color: "#4F5D75",
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {col}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {data?.postings.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-8 text-center"
                      style={{
                        fontFamily:
                          "var(--font-body, 'DM Sans Variable', sans-serif)",
                        color: "#4F5D75",
                      }}
                    >
                      No postings found
                    </td>
                  </tr>
                ) : (
                  data?.postings.map((posting) => (
                    <tr
                      key={posting.id}
                      style={{ borderBottom: "1px solid #BFC0C0" }}
                    >
                      <td
                        className="px-4 py-2.5"
                        style={{
                          fontFamily:
                            "var(--font-body, 'DM Sans Variable', sans-serif)",
                          color: "#2D3142",
                          maxWidth: "280px",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {posting.title ?? "—"}
                      </td>
                      <td
                        className="px-4 py-2.5"
                        style={{
                          fontFamily:
                            "var(--font-body, 'DM Sans Variable', sans-serif)",
                          color: "#4F5D75",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {posting.location ?? "—"}
                      </td>
                      <td
                        className="px-4 py-2.5"
                        style={{
                          fontFamily:
                            "var(--font-body, 'DM Sans Variable', sans-serif)",
                          color: "#4F5D75",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {posting.role_archetype ?? "—"}
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge
                          variant={posting.is_active ? "success" : "neutral"}
                          size="sm"
                        >
                          {posting.is_active ? "Active" : "Closed"}
                        </Badge>
                      </td>
                      <td
                        className="px-4 py-2.5"
                        style={{
                          fontFamily:
                            "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                          fontSize: "12px",
                          color: "#4F5D75",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {formatDate(posting.first_seen_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
