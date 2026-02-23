"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { KpiCard } from "@/components/data/kpi-card";
import { Badge } from "@/components/data/badge";
import { Callout } from "@/components/content/callout";
import { BarChart } from "@/components/charts/bar-chart";
import { COMPANIES } from "@/lib/constants";
import { formatRoleArchetype } from "@/lib/utils";
import { DOSSIER_MOCKS } from "@/lib/mock/dossiers";
import type { GlassdoorReview } from "@/lib/mock/dossiers";
import { MockupBanner } from "@/components/content/mockup-banner";

type Tab = "summary" | "brands" | "hiring" | "employees";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "summary", label: "Executive Summary" },
  { id: "brands", label: "Brand Intelligence" },
  { id: "hiring", label: "Hiring" },
  { id: "employees", label: "Employee Insights" },
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function StarRating({ rating, size = 14 }: { rating: number; size?: number }) {
  const filled = Math.round(rating);
  return (
    <span style={{ fontSize: `${size}px`, letterSpacing: "1px", lineHeight: 1 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} style={{ color: i <= filled ? "#EF8354" : "#BFC0C0" }}>
          ★
        </span>
      ))}
    </span>
  );
}

function SentimentCard({
  pct,
  label,
  sublabel,
}: {
  pct: number;
  label: string;
  sublabel: string;
}) {
  return (
    <div
      style={{
        backgroundColor: "#FFFFFF",
        border: "1px solid #BFC0C0",
        borderRadius: "8px",
        padding: "16px",
        boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
          fontSize: "26px",
          fontWeight: 600,
          color: "#2D3142",
          lineHeight: 1,
          marginBottom: "8px",
        }}
      >
        {pct}%
      </div>
      <div
        style={{
          height: "4px",
          backgroundColor: "#E8E8E4",
          borderRadius: "2px",
          marginBottom: "10px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            backgroundColor: "#EF8354",
            borderRadius: "2px",
            transition: "width 400ms ease",
          }}
        />
      </div>
      <div
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          fontSize: "12px",
          fontWeight: 600,
          color: "#2D3142",
          lineHeight: "1.3",
          marginBottom: "2px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          fontSize: "11px",
          color: "#4F5D75",
        }}
      >
        {sublabel}
      </div>
    </div>
  );
}

function ReviewCard({ review }: { review: GlassdoorReview }) {
  const borderColor =
    review.rating >= 4 ? "#3CA060" : review.rating >= 3 ? "#BFC0C0" : "#D64045";

  const signals: Array<{ val: boolean | null; label: string }> = [
    { val: review.recommend, label: "Recommend" },
    { val: review.ceoApproval, label: "CEO approval" },
    { val: review.businessOutlook, label: "Business outlook" },
  ];

  return (
    <div
      style={{
        border: "1px solid #E8E8E4",
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: "6px",
        padding: "14px 16px",
        backgroundColor: "#FAFAF9",
      }}
    >
      {/* Rating + date */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "8px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontFamily:
                "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "13px",
              fontWeight: 600,
              color: "#2D3142",
            }}
          >
            {review.rating.toFixed(1)}
          </span>
          <StarRating rating={review.rating} size={11} />
        </div>
        <span
          style={{
            fontFamily:
              "var(--font-mono, 'JetBrains Mono Variable', monospace)",
            fontSize: "11px",
            color: "#BFC0C0",
          }}
        >
          {review.date}
        </span>
      </div>

      {/* Title */}
      <p
        style={{
          fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
          fontSize: "14px",
          fontWeight: 600,
          color: "#2D3142",
          marginBottom: "8px",
          lineHeight: "1.3",
        }}
      >
        {review.title}
      </p>

      {/* Role + status + location */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "6px",
          marginBottom: "10px",
        }}
      >
        <Badge variant="neutral" size="sm">
          {review.role}
        </Badge>
        <Badge variant="neutral" size="sm">
          {review.employmentStatus}
        </Badge>
        <Badge variant="neutral" size="sm">
          {review.location}
        </Badge>
      </div>

      {/* Signals */}
      <div
        style={{
          display: "flex",
          gap: "16px",
          paddingBottom: "10px",
          marginBottom: "10px",
          borderBottom: "1px solid #E8E8E4",
          flexWrap: "wrap",
        }}
      >
        {signals.map(({ val, label }) => {
          const sym = val === true ? "✓" : val === false ? "✗" : "—";
          const color =
            val === true ? "#3CA060" : val === false ? "#D64045" : "#BFC0C0";
          return (
            <span
              key={label}
              style={{
                fontFamily:
                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "12px",
                color,
              }}
            >
              {sym} {label}
            </span>
          );
        })}
      </div>

      {/* Pros */}
      <div style={{ marginBottom: "6px" }}>
        <span
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "10px",
            fontWeight: 700,
            color: "#3CA060",
            textTransform: "uppercase",
            letterSpacing: "0.07em",
            marginRight: "6px",
          }}
        >
          Pros
        </span>
        <span
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#2D3142",
            lineHeight: "1.5",
          }}
        >
          {review.pros}
        </span>
      </div>

      {/* Cons */}
      <div>
        <span
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "10px",
            fontWeight: 700,
            color: "#D64045",
            textTransform: "uppercase",
            letterSpacing: "0.07em",
            marginRight: "6px",
          }}
        >
          Cons
        </span>
        <span
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#2D3142",
            lineHeight: "1.5",
          }}
        >
          {review.cons}
        </span>
      </div>
    </div>
  );
}

function BarList({
  items,
}: {
  items: Array<{ label: string; count: number }>;
}) {
  const maxCount = items.length > 0 ? items[0].count : 1;
  return (
    <div className="space-y-1.5">
      {items.map((item) => {
        const pct = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
        return (
          <div key={item.label} className="flex items-center gap-3">
            <span
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "13px",
                color: "#2D3142",
                width: "160px",
                flexShrink: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={item.label}
            >
              {item.label}
            </span>
            <div
              style={{
                flex: 1,
                backgroundColor: "#E8E8E4",
                borderRadius: "3px",
                height: "8px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: "100%",
                  backgroundColor: "#EF8354",
                  borderRadius: "3px",
                  transition: "width 300ms ease",
                }}
              />
            </div>
            <span
              style={{
                fontFamily:
                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                fontSize: "11px",
                color: "#4F5D75",
                width: "32px",
                textAlign: "right",
                flexShrink: 0,
              }}
            >
              {item.count}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
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
        {title}
      </h2>
      {children}
    </div>
  );
}

export default function CompetitorDossierPage() {
  const params = useParams();
  const slug =
    typeof params.slug === "string" ? params.slug : (params.slug?.[0] ?? "");

  const company = COMPANIES.find((c) => c.slug === slug);
  const mock = DOSSIER_MOCKS[slug];

  const [activeTab, setActiveTab] = useState<Tab>("summary");

  if (!company || !mock) {
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

  const payChartData = mock.payBenchmarks
    .filter((p) => p.pay_min_avg !== null || p.pay_max_avg !== null)
    .map((p) => ({
      role: p.role_archetype,
      "Pay Min": Math.round(p.pay_min_avg ?? 0),
      "Pay Max": Math.round(p.pay_max_avg ?? 0),
    }));

  return (
    <div>
      <MockupBanner />
      {/* Header */}
      <div className="flex items-start gap-3 mb-6 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap mb-1">
            <h1
              style={{
                fontFamily:
                  "var(--font-display, 'Sora Variable', sans-serif)",
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
            {mock.hq}
          </p>
        </div>
      </div>

      {/* KPI Row */}
      <div
        className="grid gap-4 mb-6"
        style={{ gridTemplateColumns: "repeat(4, 1fr)" }}
      >
        <KpiCard
          label="Active Postings"
          value={mock.kpis.activePostings.toLocaleString()}
        />
        <KpiCard
          label="New This Week"
          value={mock.kpis.newThisWeek.toLocaleString()}
        />
        <KpiCard
          label="Avg Pay Min"
          value={
            mock.kpis.avgPayMin !== null
              ? `$${mock.kpis.avgPayMin.toLocaleString()}`
              : "—"
          }
        />
        <KpiCard label="Top Role" value={mock.kpis.topRole} />
      </div>

      {/* Tab Bar */}
      <div
        className="flex mb-6"
        style={{ borderBottom: "1px solid #BFC0C0" }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              style={{
                fontFamily:
                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "14px",
                fontWeight: isActive ? 600 : 400,
                color: isActive ? "#2D3142" : "#4F5D75",
                padding: "10px 16px",
                background: "none",
                border: "none",
                borderBottom: isActive
                  ? "2px solid #EF8354"
                  : "2px solid transparent",
                marginBottom: "-1px",
                cursor: "pointer",
                transition: "color 150ms ease",
                whiteSpace: "nowrap",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab: Executive Summary */}
      {activeTab === "summary" && (
        <div>
          <div className="mb-6">
            <Callout variant="finding" title="Key Finding">
              {mock.insight}
            </Callout>
          </div>

          <div
            className="rounded-lg border p-4 mb-6"
            style={{
              backgroundColor: "#FFFFFF",
              borderColor: "#BFC0C0",
              boxShadow:
                "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
            }}
          >
            <p
              style={{
                fontFamily:
                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "11px",
                fontWeight: 600,
                color: "#4F5D75",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginBottom: "8px",
              }}
            >
              Company Overview
            </p>
            <p
              style={{
                fontFamily:
                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "14px",
                color: "#2D3142",
                lineHeight: "1.6",
              }}
            >
              {mock.narrative}
            </p>
          </div>

          <SectionCard title="Known Clients & Channels">
            <div className="mb-4">
              <p
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "#4F5D75",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  marginBottom: "8px",
                }}
              >
                Client Brands
              </p>
              <div className="flex flex-wrap gap-2">
                {mock.clientBrands.map((brand) => (
                  <Badge key={brand} variant="neutral">
                    {brand}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <p
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "#4F5D75",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  marginBottom: "8px",
                }}
              >
                Operating In
              </p>
              <div className="flex flex-wrap gap-2">
                {mock.operatingIn.map((channel) => (
                  <Badge key={channel} variant="neutral">
                    {channel}
                  </Badge>
                ))}
              </div>
            </div>
          </SectionCard>

          <div
            className="grid gap-4 mb-6"
            style={{ gridTemplateColumns: "repeat(3, 1fr)" }}
          >
            <KpiCard
              label="Total Roles Found"
              value={mock.totalRolesFound.toLocaleString()}
            />
            <KpiCard
              label="Roles Closed"
              value={mock.rolesClosed.toLocaleString()}
            />
            <KpiCard
              label="Currently Open"
              value={mock.kpis.activePostings.toLocaleString()}
            />
          </div>

          <SectionCard title="Hiring by Role">
            <BarList
              items={mock.roleDistribution.map((r) => ({
                label: r.role,
                count: r.count,
              }))}
            />
          </SectionCard>

          <div
            className="rounded-lg border overflow-hidden mb-6"
            style={{
              backgroundColor: "#FFFFFF",
              borderColor: "#BFC0C0",
              boxShadow:
                "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
            }}
          >
            <div
              className="px-4 py-3 border-b"
              style={{ borderColor: "#BFC0C0" }}
            >
              <h2
                className="text-sm font-medium"
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  color: "#2D3142",
                }}
              >
                Latest Roles
              </h2>
            </div>
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
                  {mock.postings.slice(0, 10).map((posting) => (
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
                        {posting.title}
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
                        {posting.location}
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
                        {formatRoleArchetype(posting.role_archetype)}
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
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Brand Intelligence */}
      {activeTab === "brands" && (
        <div>
          <div className="mb-6">
            <Callout variant="positive" title="Geographic Focus">
              {mock.geographicFocus}
            </Callout>
          </div>

          <SectionCard title="Brand Intelligence">
            {mock.topBrands.length > 0 ? (
              <BarList
                items={mock.topBrands.map((b) => ({
                  label: b.brand_name,
                  count: b.count,
                }))}
              />
            ) : (
              <div
                className="flex items-center justify-center py-8 text-sm"
                style={{
                  color: "#4F5D75",
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                }}
              >
                No brand data available
              </div>
            )}
          </SectionCard>

          <div className="mb-6">
            <Callout variant="caution" title="Data Note">
              {mock.dataNote}
            </Callout>
          </div>
        </div>
      )}

      {/* Tab: Hiring */}
      {activeTab === "hiring" && (
        <div>
          <SectionCard title="Pay Benchmarks by Role">
            {payChartData.length > 0 ? (
              <BarChart
                data={payChartData}
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
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                }}
              >
                No pay benchmark data available
              </div>
            )}
          </SectionCard>

          <div
            className="rounded-lg border overflow-hidden"
            style={{
              backgroundColor: "#FFFFFF",
              borderColor: "#BFC0C0",
              boxShadow:
                "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
            }}
          >
            <div
              className="px-4 py-3 border-b"
              style={{ borderColor: "#BFC0C0" }}
            >
              <h2
                className="text-sm font-medium"
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  color: "#2D3142",
                }}
              >
                Job Postings
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr
                    style={{
                      backgroundColor: "#E8E8E4",
                      borderBottom: "1px solid #BFC0C0",
                    }}
                  >
                    {[
                      "Title",
                      "Location",
                      "Role",
                      "Status",
                      "First Seen",
                    ].map((col) => (
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
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {mock.postings.length === 0 ? (
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
                    mock.postings.map((posting) => (
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
                          {posting.title}
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
                          {posting.location}
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
                          {formatRoleArchetype(posting.role_archetype)}
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge
                            variant={
                              posting.is_active ? "success" : "neutral"
                            }
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
          </div>
        </div>
      )}

      {/* Tab: Employee Insights */}
      {activeTab === "employees" && (
        <div>
          {/* Rating hero */}
          <div
            className="rounded-lg border p-5 mb-6"
            style={{
              backgroundColor: "#FFFFFF",
              borderColor: "#BFC0C0",
              boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: "12px",
                marginBottom: "6px",
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  fontFamily:
                    "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                  fontSize: "48px",
                  fontWeight: 600,
                  color: "#2D3142",
                  lineHeight: 1,
                }}
              >
                {mock.glassdoor.overallRating.toFixed(1)}
              </span>
              <StarRating rating={mock.glassdoor.overallRating} size={22} />
              <span
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "13px",
                  color: "#4F5D75",
                }}
              >
                {mock.glassdoor.totalReviews.toLocaleString()} reviews
              </span>
            </div>
            <p
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "11px",
                color: "#BFC0C0",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Sourced from Glassdoor
            </p>
          </div>

          {/* Sentiment grid */}
          <div
            className="grid gap-4 mb-6"
            style={{ gridTemplateColumns: "repeat(4, 1fr)" }}
          >
            <SentimentCard
              pct={mock.glassdoor.recommendPct}
              label="Would Recommend"
              sublabel="to a friend"
            />
            <SentimentCard
              pct={mock.glassdoor.businessOutlookPct}
              label="Business Outlook"
              sublabel="positive"
            />
            <SentimentCard
              pct={mock.glassdoor.ceoApprovalPct}
              label={`Approve ${mock.glassdoor.ceoName.split(" ")[0]}`}
              sublabel={`CEO · ${mock.glassdoor.ceoName}`}
            />
            <SentimentCard
              pct={mock.glassdoor.interviewPositivePct}
              label="Interview"
              sublabel="positive experience"
            />
          </div>

          {/* Category ratings + interview snapshot */}
          <div
            className="grid gap-4 mb-6"
            style={{ gridTemplateColumns: "3fr 2fr" }}
          >
            <SectionCard title="Ratings by Category">
              <div className="space-y-2">
                {mock.glassdoor.ratingsByCategory.map((cat) => {
                  const fill = (cat.score / 5) * 100;
                  const trendSym =
                    cat.trend === "up" ? "↑" : cat.trend === "down" ? "↓" : "→";
                  const trendColor =
                    cat.trend === "up"
                      ? "#3CA060"
                      : cat.trend === "down"
                        ? "#D64045"
                        : "#BFC0C0";
                  return (
                    <div
                      key={cat.label}
                      style={{ display: "flex", alignItems: "center", gap: "10px" }}
                    >
                      <span
                        style={{
                          fontFamily:
                            "var(--font-body, 'DM Sans Variable', sans-serif)",
                          fontSize: "12px",
                          color: "#2D3142",
                          width: "172px",
                          flexShrink: 0,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                        title={cat.label}
                      >
                        {cat.label}
                      </span>
                      <div
                        style={{
                          flex: 1,
                          backgroundColor: "#E8E8E4",
                          borderRadius: "3px",
                          height: "6px",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${fill}%`,
                            height: "100%",
                            backgroundColor: "#EF8354",
                            borderRadius: "3px",
                          }}
                        />
                      </div>
                      <span
                        style={{
                          fontFamily:
                            "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                          fontSize: "11px",
                          color: "#4F5D75",
                          width: "28px",
                          textAlign: "right",
                          flexShrink: 0,
                        }}
                      >
                        {cat.score.toFixed(1)}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          color: trendColor,
                          width: "10px",
                          flexShrink: 0,
                        }}
                      >
                        {trendSym}
                      </span>
                    </div>
                  );
                })}
              </div>
            </SectionCard>

            <SectionCard title="Interview Snapshot">
              <div className="space-y-4">
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "5px",
                    }}
                  >
                    <span
                      style={{
                        fontFamily:
                          "var(--font-body, 'DM Sans Variable', sans-serif)",
                        fontSize: "12px",
                        color: "#4F5D75",
                      }}
                    >
                      Positive experience
                    </span>
                    <span
                      style={{
                        fontFamily:
                          "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                        fontSize: "12px",
                        fontWeight: 600,
                        color: "#2D3142",
                      }}
                    >
                      {mock.glassdoor.interviewPositivePct}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: "6px",
                      backgroundColor: "#E8E8E4",
                      borderRadius: "3px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${mock.glassdoor.interviewPositivePct}%`,
                        height: "100%",
                        backgroundColor: "#EF8354",
                        borderRadius: "3px",
                      }}
                    />
                  </div>
                </div>

                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "5px",
                    }}
                  >
                    <span
                      style={{
                        fontFamily:
                          "var(--font-body, 'DM Sans Variable', sans-serif)",
                        fontSize: "12px",
                        color: "#4F5D75",
                      }}
                    >
                      Avg difficulty
                    </span>
                    <span
                      style={{
                        fontFamily:
                          "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                        fontSize: "12px",
                        fontWeight: 600,
                        color: "#2D3142",
                      }}
                    >
                      {mock.glassdoor.interviewDifficulty.toFixed(1)} / 5
                    </span>
                  </div>
                  <div
                    style={{
                      height: "6px",
                      backgroundColor: "#E8E8E4",
                      borderRadius: "3px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${(mock.glassdoor.interviewDifficulty / 5) * 100}%`,
                        height: "100%",
                        backgroundColor: "#EF8354",
                        borderRadius: "3px",
                      }}
                    />
                  </div>
                </div>

                <p
                  style={{
                    fontFamily:
                      "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "12px",
                    color: "#4F5D75",
                    paddingTop: "6px",
                    borderTop: "1px solid #E8E8E4",
                  }}
                >
                  Based on {mock.glassdoor.interviewReviewCount} Glassdoor
                  interview reviews
                </p>
              </div>
            </SectionCard>
          </div>

          {/* Reviews */}
          <SectionCard title="Recent Reviews">
            <div className="space-y-3">
              {mock.glassdoor.reviews.map((review) => (
                <ReviewCard key={review.id} review={review} />
              ))}
            </div>
          </SectionCard>
        </div>
      )}
    </div>
  );
}
