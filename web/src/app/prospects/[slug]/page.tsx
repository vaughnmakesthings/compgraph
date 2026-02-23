"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Badge } from "@/components/data/badge";
import { Callout } from "@/components/content/callout";
import { PROSPECT_MOCKS, type ProspectContact, type PressRelease } from "@/lib/mock/prospects";

type Tab = "summary" | "contacts";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "summary", label: "Executive Summary" },
  { id: "contacts", label: "Potential Contacts" },
];

// --- helpers ---

function formatDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

const AVATAR_COLORS = [
  { bg: "#1B998B1A", text: "#1B998B", border: "#1B998B33" },
  { bg: "#EF83541A", text: "#C05E34", border: "#EF835433" },
  { bg: "#4F5D751A", text: "#4F5D75", border: "#4F5D7533" },
  { bg: "#DCB2561A", text: "#A07D28", border: "#DCB25633" },
  { bg: "#8C2C231A", text: "#8C2C23", border: "#8C2C2333" },
];

function getAvatarStyle(name: string) {
  const idx = name.charCodeAt(0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}

function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

// --- sub-components ---

function KpiStrip({
  items,
}: {
  items: Array<{ label: string; value: string }>;
}) {
  return (
    <div
      className="grid gap-px mb-6 rounded-lg overflow-hidden border"
      style={{
        gridTemplateColumns: `repeat(${items.length}, 1fr)`,
        borderColor: "#BFC0C0",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {items.map((item, i) => (
        <div
          key={item.label}
          style={{
            backgroundColor: "#FFFFFF",
            padding: "16px 20px",
            borderRight: i < items.length - 1 ? "1px solid #BFC0C0" : "none",
          }}
        >
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "11px",
              fontWeight: 600,
              color: "#4F5D75",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginBottom: "4px",
            }}
          >
            {item.label}
          </p>
          <p
            style={{
              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "18px",
              fontWeight: 600,
              color: "#2D3142",
              lineHeight: 1.2,
            }}
          >
            {item.value}
          </p>
        </div>
      ))}
    </div>
  );
}

const CATEGORY_META: Record<
  PressRelease["category"],
  { label: string; bg: string; text: string; border: string }
> = {
  marketing: { label: "Marketing", bg: "#EF83541A", text: "#C05E34", border: "#EF835433" },
  financial: { label: "Financial", bg: "#4F5D751A", text: "#4F5D75", border: "#4F5D7533" },
  partnership: { label: "Partnership", bg: "#1B998B1A", text: "#1B998B", border: "#1B998B33" },
  leadership: { label: "Leadership", bg: "#DCB2561A", text: "#A07D28", border: "#DCB25633" },
  product: { label: "Product", bg: "#E8E8E4", text: "#4F5D75", border: "#BFC0C0" },
};

function PressReleaseFeed({ releases }: { releases: PressRelease[] }) {
  return (
    <div
      className="rounded-lg border overflow-hidden mb-6"
      style={{
        backgroundColor: "#FFFFFF",
        borderColor: "#BFC0C0",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div className="px-4 py-3 border-b" style={{ borderColor: "#BFC0C0" }}>
        <h2
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            fontWeight: 600,
            color: "#2D3142",
          }}
        >
          Recent Press Releases
        </h2>
      </div>
      <div>
        {releases.map((pr, i) => {
          const cat = CATEGORY_META[pr.category];
          return (
            <div
              key={pr.id}
              style={{
                borderBottom: i < releases.length - 1 ? "1px solid #E8E8E4" : "none",
                padding: "16px 20px",
                display: "grid",
                gridTemplateColumns: "80px 1fr",
                gap: "16px",
                alignItems: "start",
              }}
            >
              {/* Date column */}
              <div style={{ paddingTop: "2px" }}>
                <p
                  style={{
                    fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                    fontSize: "11px",
                    color: "#4F5D75",
                    lineHeight: 1.4,
                    whiteSpace: "nowrap",
                  }}
                >
                  {formatDateShort(pr.date)}
                </p>
              </div>

              {/* Content column */}
              <div>
                <div className="flex items-start gap-2 mb-1.5 flex-wrap">
                  <span
                    style={{
                      display: "inline-block",
                      backgroundColor: cat.bg,
                      color: cat.text,
                      border: `1px solid ${cat.border}`,
                      borderRadius: "var(--radius-sm, 4px)",
                      fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "10px",
                      fontWeight: 600,
                      padding: "1px 6px",
                      letterSpacing: "0.03em",
                      textTransform: "uppercase",
                      lineHeight: "1.4",
                      flexShrink: 0,
                    }}
                  >
                    {cat.label}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "10px",
                      color: "#BFC0C0",
                      lineHeight: "1.6",
                    }}
                  >
                    {pr.source}
                  </span>
                </div>
                <p
                  style={{
                    fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "#2D3142",
                    lineHeight: "1.4",
                    marginBottom: "6px",
                  }}
                >
                  {pr.headline}
                </p>
                <p
                  style={{
                    fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "13px",
                    color: "#4F5D75",
                    lineHeight: "1.6",
                  }}
                >
                  {pr.summary}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const RELEVANCE_META: Record<
  ProspectContact["relevance"],
  { label: string; bg: string; text: string; border: string }
> = {
  primary: { label: "Primary", bg: "#1B998B1A", text: "#1B998B", border: "#1B998B33" },
  secondary: { label: "Secondary", bg: "#DCB2561A", text: "#A07D28", border: "#DCB25633" },
  peripheral: { label: "Peripheral", bg: "#E8E8E4", text: "#4F5D75", border: "#BFC0C0" },
};

const STATUS_META: Record<
  ProspectContact["outreachStatus"],
  { label: string; bg: string; text: string; border: string }
> = {
  "not-contacted": { label: "Not Contacted", bg: "#E8E8E4", text: "#4F5D75", border: "#BFC0C0" },
  "in-queue": { label: "In Queue", bg: "#4F5D751A", text: "#4F5D75", border: "#4F5D7533" },
  "reached-out": { label: "Reached Out", bg: "#DCB2561A", text: "#A07D28", border: "#DCB25633" },
  responded: { label: "Responded", bg: "#1B998B1A", text: "#1B998B", border: "#1B998B33" },
};

const SENIORITY_ORDER: Record<ProspectContact["seniority"], number> = {
  "c-suite": 0,
  vp: 1,
  director: 2,
  manager: 3,
};

const SOURCE_LABELS: Record<"apollo" | "linkedin" | "zoominfo", string> = {
  apollo: "Apollo",
  linkedin: "LinkedIn",
  zoominfo: "ZoomInfo",
};

function ConfidenceBar({ pct }: { pct: number }) {
  const color = pct >= 85 ? "#1B998B" : pct >= 70 ? "#DCB256" : "#4F5D75";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
      <div
        style={{
          width: 48,
          height: 5,
          backgroundColor: "#E8E8E4",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            backgroundColor: color,
            borderRadius: 3,
            transition: "width 300ms ease",
          }}
        />
      </div>
      <span
        style={{
          fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
          fontSize: "11px",
          color: "#4F5D75",
          width: "30px",
          textAlign: "right",
          flexShrink: 0,
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

type ContactFilter = "all" | "primary" | "secondary";
type StatusFilter = "all" | "not-contacted" | "in-queue" | "reached-out" | "responded";

function ContactsTab({ contacts }: { contacts: ProspectContact[] }) {
  const [relevanceFilter, setRelevanceFilter] = useState<ContactFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const sorted = [...contacts].sort(
    (a, b) => SENIORITY_ORDER[a.seniority] - SENIORITY_ORDER[b.seniority]
  );

  const filtered = sorted.filter((c) => {
    const relevanceOk = relevanceFilter === "all" || c.relevance === relevanceFilter;
    const statusOk = statusFilter === "all" || c.outreachStatus === statusFilter;
    return relevanceOk && statusOk;
  });

  function FilterChip({
    label,
    active,
    onClick,
  }: {
    label: string;
    active: boolean;
    onClick: () => void;
  }) {
    return (
      <button
        type="button"
        onClick={onClick}
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          fontSize: "12px",
          fontWeight: active ? 600 : 400,
          color: active ? "#2D3142" : "#4F5D75",
          backgroundColor: active ? "#FFFFFF" : "transparent",
          border: active ? "1px solid #BFC0C0" : "1px solid transparent",
          borderRadius: "var(--radius-md, 6px)",
          padding: "4px 10px",
          cursor: "pointer",
          transition: "background-color 150ms ease, color 150ms ease",
          boxShadow: active ? "var(--shadow-sm)" : "none",
        }}
      >
        {label}
      </button>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <Callout variant="finding" title="Enrichment Opportunity">
          These contacts were identified based on job title patterns correlated with field
          marketing agency selection: VP/Director of Field Marketing, Shopper Marketing, Retail
          Channel Activation, and In-Store Experience. Source confidence reflects profile match
          quality on Apollo and LinkedIn. Primary contacts have direct budget authority or
          program management responsibility.
        </Callout>
      </div>

      {/* Filter toolbar */}
      <div
        className="flex items-center gap-4 mb-4 flex-wrap"
        style={{
          backgroundColor: "#F4F4F0",
          borderRadius: "var(--radius-lg, 8px)",
          padding: "8px 12px",
        }}
      >
        {/* Relevance filters */}
        <div className="flex items-center gap-1">
          <span
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "11px",
              fontWeight: 600,
              color: "#4F5D75",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginRight: "4px",
            }}
          >
            Role
          </span>
          {(["all", "primary", "secondary"] as const).map((v) => (
            <FilterChip
              key={v}
              label={v === "all" ? "All" : v.charAt(0).toUpperCase() + v.slice(1)}
              active={relevanceFilter === v}
              onClick={() => setRelevanceFilter(v)}
            />
          ))}
        </div>

        <div style={{ width: 1, height: 20, backgroundColor: "#BFC0C0", flexShrink: 0 }} />

        {/* Status filters */}
        <div className="flex items-center gap-1 flex-wrap">
          <span
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "11px",
              fontWeight: 600,
              color: "#4F5D75",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              marginRight: "4px",
            }}
          >
            Status
          </span>
          {(["all", "not-contacted", "in-queue", "reached-out", "responded"] as const).map((v) => (
            <FilterChip
              key={v}
              label={
                v === "all"
                  ? "All"
                  : STATUS_META[v as Exclude<StatusFilter, "all">]?.label ?? v
              }
              active={statusFilter === v}
              onClick={() => setStatusFilter(v)}
            />
          ))}
        </div>

        <div style={{ marginLeft: "auto" }}>
          <span
            style={{
              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "11px",
              color: "#4F5D75",
            }}
          >
            {filtered.length} of {contacts.length}
          </span>
        </div>
      </div>

      {/* Contacts table */}
      <div
        className="rounded-lg border overflow-hidden"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <div className="overflow-x-auto">
          <table className="w-full" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr
                style={{
                  backgroundColor: "#E8E8E4",
                  borderBottom: "1px solid #BFC0C0",
                }}
              >
                {["Contact", "Department", "Sources", "Confidence", "Relevance", "Status", ""].map(
                  (col) => (
                    <th
                      key={col}
                      className="text-left px-4 py-2"
                      style={{
                        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
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
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center"
                    style={{
                      fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontSize: "13px",
                      color: "#4F5D75",
                    }}
                  >
                    No contacts match the current filters.
                  </td>
                </tr>
              ) : (
                filtered.map((contact, i) => {
                  const avatarStyle = getAvatarStyle(contact.name);
                  const rel = RELEVANCE_META[contact.relevance];
                  const status = STATUS_META[contact.outreachStatus];

                  return (
                    <tr
                      key={contact.id}
                      style={{
                        borderBottom:
                          i < filtered.length - 1 ? "1px solid #E8E8E4" : "none",
                      }}
                    >
                      {/* Contact (avatar + name + title) */}
                      <td className="px-4 py-3">
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <div
                            style={{
                              width: 32,
                              height: 32,
                              borderRadius: "50%",
                              backgroundColor: avatarStyle.bg,
                              border: `1px solid ${avatarStyle.border}`,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              flexShrink: 0,
                            }}
                          >
                            <span
                              style={{
                                fontFamily:
                                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "11px",
                                fontWeight: 700,
                                color: avatarStyle.text,
                              }}
                            >
                              {initials(contact.name)}
                            </span>
                          </div>
                          <div className="min-w-0">
                            <p
                              style={{
                                fontFamily:
                                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "13px",
                                fontWeight: 600,
                                color: "#2D3142",
                                lineHeight: 1.3,
                              }}
                            >
                              {contact.name}
                            </p>
                            <p
                              style={{
                                fontFamily:
                                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "12px",
                                color: "#4F5D75",
                                lineHeight: 1.3,
                                maxWidth: "260px",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                              title={contact.title}
                            >
                              {contact.title}
                            </p>
                            <p
                              style={{
                                fontFamily:
                                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "11px",
                                color: "#BFC0C0",
                                lineHeight: 1.3,
                              }}
                            >
                              {contact.location}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* Department */}
                      <td
                        className="px-4 py-3"
                        style={{
                          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                          fontSize: "13px",
                          color: "#4F5D75",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {contact.department}
                      </td>

                      {/* Sources */}
                      <td className="px-4 py-3">
                        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                          {contact.sources.map((src) => (
                            <span
                              key={src}
                              style={{
                                display: "inline-block",
                                backgroundColor:
                                  src === "apollo"
                                    ? "#EF83541A"
                                    : src === "linkedin"
                                    ? "#4F5D751A"
                                    : "#E8E8E4",
                                color:
                                  src === "apollo"
                                    ? "#C05E34"
                                    : src === "linkedin"
                                    ? "#4F5D75"
                                    : "#4F5D75",
                                border: `1px solid ${
                                  src === "apollo"
                                    ? "#EF835433"
                                    : src === "linkedin"
                                    ? "#4F5D7533"
                                    : "#BFC0C0"
                                }`,
                                borderRadius: "var(--radius-sm, 4px)",
                                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "10px",
                                fontWeight: 600,
                                padding: "1px 6px",
                                lineHeight: "1.4",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {SOURCE_LABELS[src]}
                            </span>
                          ))}
                        </div>
                      </td>

                      {/* Confidence */}
                      <td className="px-4 py-3">
                        <ConfidenceBar pct={contact.confidence} />
                      </td>

                      {/* Relevance */}
                      <td className="px-4 py-3">
                        <span
                          style={{
                            display: "inline-block",
                            backgroundColor: rel.bg,
                            color: rel.text,
                            border: `1px solid ${rel.border}`,
                            borderRadius: "var(--radius-sm, 4px)",
                            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                            fontSize: "10px",
                            fontWeight: 600,
                            padding: "2px 7px",
                            lineHeight: "1.4",
                            letterSpacing: "0.02em",
                            textTransform: "uppercase",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {rel.label}
                        </span>
                      </td>

                      {/* Outreach status */}
                      <td className="px-4 py-3">
                        <span
                          style={{
                            display: "inline-block",
                            backgroundColor: status.bg,
                            color: status.text,
                            border: `1px solid ${status.border}`,
                            borderRadius: "var(--radius-sm, 4px)",
                            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                            fontSize: "10px",
                            fontWeight: 500,
                            padding: "2px 7px",
                            lineHeight: "1.4",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {status.label}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3">
                        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                          {contact.sources.includes("linkedin") && (
                            <button
                              type="button"
                              title="Find on LinkedIn"
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                backgroundColor: "#4F5D751A",
                                color: "#4F5D75",
                                border: "1px solid #4F5D7533",
                                borderRadius: "var(--radius-md, 6px)",
                                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "11px",
                                fontWeight: 500,
                                padding: "3px 8px",
                                cursor: "pointer",
                                transition: "background-color 150ms ease",
                                whiteSpace: "nowrap",
                              }}
                              onMouseEnter={(e) => {
                                (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                                  "#4F5D7526";
                              }}
                              onMouseLeave={(e) => {
                                (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                                  "#4F5D751A";
                              }}
                            >
                              LI
                            </button>
                          )}
                          {contact.sources.includes("apollo") && (
                            <button
                              type="button"
                              title="Find on Apollo"
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                backgroundColor: "#EF83541A",
                                color: "#C05E34",
                                border: "1px solid #EF835433",
                                borderRadius: "var(--radius-md, 6px)",
                                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "11px",
                                fontWeight: 500,
                                padding: "3px 8px",
                                cursor: "pointer",
                                transition: "background-color 150ms ease",
                                whiteSpace: "nowrap",
                              }}
                              onMouseEnter={(e) => {
                                (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                                  "#EF835426";
                              }}
                              onMouseLeave={(e) => {
                                (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                                  "#EF83541A";
                              }}
                            >
                              Apollo
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Enrichment footer */}
        <div
          className="px-4 py-3 border-t"
          style={{ borderColor: "#BFC0C0", backgroundColor: "#F4F4F0" }}
        >
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              color: "#4F5D75",
            }}
          >
            Contacts identified via public profile enrichment. Confidence scores reflect
            profile match quality. Enrich directly in Apollo or LinkedIn — email discovery
            requires manual verification before outreach.
          </p>
        </div>
      </div>
    </div>
  );
}

// --- main page ---

export default function ProspectDossierPage() {
  const params = useParams();
  const slug = typeof params.slug === "string" ? params.slug : (params.slug?.[0] ?? "");

  const mock = PROSPECT_MOCKS[slug];
  const [activeTab, setActiveTab] = useState<Tab>("summary");

  if (!mock) {
    return (
      <div
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          color: "#4F5D75",
          padding: "2rem 0",
        }}
      >
        Prospect not found.
      </div>
    );
  }

  const signalColor =
    mock.fieldMarketingSignal === "high"
      ? "#1B998B"
      : mock.fieldMarketingSignal === "medium"
      ? "#A07D28"
      : "#4F5D75";

  const signalLabel =
    mock.fieldMarketingSignal === "high"
      ? "High FM Signal"
      : mock.fieldMarketingSignal === "medium"
      ? "Medium FM Signal"
      : "Low FM Signal";

  const primaryContactCount = mock.contacts.filter((c) => c.relevance === "primary").length;

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
              {mock.name}
            </h1>
            <Badge variant="neutral">{mock.industry}</Badge>
            <Badge variant="neutral">{mock.sector}</Badge>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                backgroundColor:
                  mock.fieldMarketingSignal === "high"
                    ? "#1B998B1A"
                    : mock.fieldMarketingSignal === "medium"
                    ? "#DCB2561A"
                    : "#E8E8E4",
                color: signalColor,
                border: `1px solid ${
                  mock.fieldMarketingSignal === "high"
                    ? "#1B998B33"
                    : mock.fieldMarketingSignal === "medium"
                    ? "#DCB25633"
                    : "#BFC0C0"
                }`,
                borderRadius: "var(--radius-sm, 4px)",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "10px",
                fontWeight: 600,
                padding: "2px 7px",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                lineHeight: "1.4",
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  backgroundColor: signalColor,
                  flexShrink: 0,
                }}
              />
              {signalLabel}
            </span>
          </div>
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#4F5D75",
            }}
          >
            {mock.hq} · {mock.employees} employees · {mock.revenue}
          </p>
        </div>
      </div>

      {/* KPI Strip */}
      <KpiStrip
        items={[
          { label: "Est. FM Budget", value: mock.kpis.estimatedFMBudget },
          { label: "Retail Doors", value: mock.kpis.retailDoors },
          { label: "Key Retailers", value: mock.kpis.keyRetailers },
          { label: "Primary Contacts", value: String(primaryContactCount) },
        ]}
      />

      {/* Tab bar */}
      <div className="flex mb-6" style={{ borderBottom: "1px solid #BFC0C0" }}>
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "14px",
                fontWeight: isActive ? 600 : 400,
                color: isActive ? "#2D3142" : "#4F5D75",
                padding: "10px 16px",
                background: "none",
                border: "none",
                borderBottom: isActive ? "2px solid #EF8354" : "2px solid transparent",
                marginBottom: "-1px",
                cursor: "pointer",
                transition: "color 150ms ease",
                whiteSpace: "nowrap",
              }}
            >
              {tab.label}
              {tab.id === "contacts" && (
                <span
                  style={{
                    marginLeft: "6px",
                    display: "inline-block",
                    backgroundColor: isActive ? "#EF83541A" : "#E8E8E4",
                    color: isActive ? "#C05E34" : "#4F5D75",
                    borderRadius: "var(--radius-sm, 4px)",
                    fontFamily:
                      "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                    fontSize: "10px",
                    fontWeight: 600,
                    padding: "1px 5px",
                    lineHeight: "1.4",
                    verticalAlign: "middle",
                    transition: "background-color 150ms ease, color 150ms ease",
                  }}
                >
                  {mock.contacts.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab: Executive Summary */}
      {activeTab === "summary" && (
        <div>
          {/* Company overview */}
          <div
            className="rounded-lg border p-4 mb-6"
            style={{
              backgroundColor: "#FFFFFF",
              borderColor: "#BFC0C0",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <p
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
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
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "14px",
                color: "#2D3142",
                lineHeight: "1.7",
              }}
            >
              {mock.narrative}
            </p>
          </div>

          {/* Key retailers */}
          <div
            className="rounded-lg border p-4 mb-6"
            style={{
              backgroundColor: "#FFFFFF",
              borderColor: "#BFC0C0",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <p
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "11px",
                fontWeight: 600,
                color: "#4F5D75",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginBottom: "8px",
              }}
            >
              Retail Presence
            </p>
            <div className="flex flex-wrap gap-2">
              {mock.keyRetailers.map((r) => (
                <Badge key={r} variant="neutral">
                  {r}
                </Badge>
              ))}
            </div>
          </div>

          {/* Press releases */}
          <PressReleaseFeed releases={mock.pressReleases} />
        </div>
      )}

      {/* Tab: Potential Contacts */}
      {activeTab === "contacts" && <ContactsTab contacts={mock.contacts} />}
    </div>
  );
}
