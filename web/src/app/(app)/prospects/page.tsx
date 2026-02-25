"use client";

import { useRouter } from "next/navigation";
import { Badge } from "@/components/data/badge";
import { PROSPECTS, type ProspectSummary } from "@/lib/mock/prospects";
import { MockupBanner } from "@/components/content/mockup-banner";

const SIGNAL_COLORS: Record<
  "high" | "medium" | "low",
  { bg: string; text: string; border: string; label: string }
> = {
  high: { bg: "#1B998B1A", text: "#1B998B", border: "#1B998B33", label: "High Signal" },
  medium: { bg: "#DCB2561A", text: "#A07D28", border: "#DCB25633", label: "Medium Signal" },
  low: { bg: "#E8E8E4", text: "#4F5D75", border: "#BFC0C0", label: "Low Signal" },
};

const CONTACT_COUNTS: Record<string, number> = {
  "keurig-dr-pepper": 6,
  weber: 4,
  "turtle-beach": 5,
};

function SignalPip({ signal }: { signal: "high" | "medium" | "low" }) {
  const cfg = SIGNAL_COLORS[signal];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        backgroundColor: cfg.bg,
        color: cfg.text,
        border: `1px solid ${cfg.border}`,
        borderRadius: "var(--radius-sm, 4px)",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
        fontSize: "10px",
        fontWeight: 600,
        padding: "2px 7px",
        lineHeight: "1.4",
        letterSpacing: "0.03em",
        textTransform: "uppercase",
      }}
    >
      <span
        style={{
          display: "inline-block",
          width: 6,
          height: 6,
          borderRadius: "50%",
          backgroundColor: cfg.text,
          flexShrink: 0,
        }}
      />
      {cfg.label}
    </span>
  );
}

function ProspectCard({
  prospect,
  onClick,
}: {
  prospect: ProspectSummary;
  onClick: () => void;
}) {
  const contactCount = CONTACT_COUNTS[prospect.slug] ?? 0;

  return (
    <button type="button" onClick={onClick} className="w-full text-left" style={{ display: "block" }}>
      <div
        style={{
          backgroundColor: "#FFFFFF",
          border: "1px solid #BFC0C0",
          borderLeft: "3px solid #1B998B",
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
        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0">
            <h2
              className="font-semibold mb-0.5 truncate"
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "15px",
                color: "#2D3142",
                lineHeight: "1.3",
              }}
            >
              {prospect.name}
            </h2>
            <p
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "12px",
                color: "#4F5D75",
              }}
            >
              {prospect.industry}
            </p>
          </div>
          <SignalPip signal={prospect.fieldMarketingSignal} />
        </div>

        {/* Meta row */}
        <div
          className="flex flex-wrap gap-x-4 gap-y-1 mb-4"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "12px",
            color: "#4F5D75",
          }}
        >
          <span>{prospect.hq}</span>
          <span>{prospect.employees} employees</span>
          <span>{prospect.revenue}</span>
        </div>

        {/* Footer row */}
        <div className="flex items-center justify-between">
          <Badge variant="neutral" size="sm">
            {contactCount} potential contact{contactCount !== 1 ? "s" : ""}
          </Badge>
          <span
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              color: "#EF8354",
              fontWeight: 500,
            }}
          >
            View dossier →
          </span>
        </div>
      </div>
    </button>
  );
}

export default function ProspectsPage() {
  const router = useRouter();

  return (
    <div>
      <MockupBanner />
      {/* Page header */}
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display, 'Sora Variable', sans-serif)" }}
        >
          Sales Prospects
        </h1>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground)",
          }}
        >
          Brands with active field marketing programs — ranked by outreach signal strength
        </p>
      </div>

      {/* Signal legend */}
      <div
        className="rounded-lg border p-4 mb-6 flex flex-wrap items-start gap-4"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <div className="flex-1 min-w-0">
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
            Signal Criteria
          </p>
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#2D3142",
              lineHeight: "1.5",
            }}
          >
            Signal strength reflects the estimated scale of a company&apos;s field marketing
            activation program based on press releases, job posting patterns, and known retail
            partnerships. High signal accounts have confirmed large-scale in-store programs and
            identifiable decision-maker contacts.
          </p>
        </div>
        <div className="flex gap-2 shrink-0 flex-wrap">
          <SignalPip signal="high" />
          <SignalPip signal="medium" />
          <SignalPip signal="low" />
        </div>
      </div>

      {/* Prospect cards */}
      <div
        className="grid gap-4"
        style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}
      >
        {PROSPECTS.map((prospect) => (
          <ProspectCard
            key={prospect.slug}
            prospect={prospect}
            onClick={() => router.push(`/prospects/${prospect.slug}`)}
          />
        ))}
      </div>
    </div>
  );
}
