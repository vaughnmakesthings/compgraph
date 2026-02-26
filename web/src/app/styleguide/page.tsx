"use client";

import { useState } from "react";
import {
  HomeIcon,
  BriefcaseIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  EyeSlashIcon,
  MagnifyingGlassIcon,
  EnvelopeIcon,
  LockClosedIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SkeletonBox } from "@/components/ui/skeleton";
import { SectionCard } from "@/components/ui/section-card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Badge } from "@/components/data";
import { KpiCard } from "@/components/data";
import { TablePagination } from "@/components/data/table-pagination";
import {
  BarChart as RechartsBarChart,
  Bar,
  AreaChart as RechartsAreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { MockupBanner } from "@/components/content/mockup-banner";
import { Callout } from "@/components/content/callout";

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

function Section({
  id,
  title,
  source,
  children,
}: {
  id: string;
  title: string;
  source: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      style={{
        scrollMarginTop: "24px",
        marginBottom: "48px",
      }}
    >
      <div style={{ marginBottom: "16px" }}>
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "18px",
            fontWeight: 600,
            color: "var(--color-foreground)",
            margin: 0,
          }}
        >
          {title}
        </h2>
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            color: "var(--color-muted-foreground)",
            margin: "4px 0 0",
            letterSpacing: "0.02em",
          }}
        >
          {source}
        </p>
      </div>
      <div
        style={{
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "24px",
        }}
      >
        {children}
      </div>
    </section>
  );
}

function SubLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      style={{
        fontFamily: "var(--font-body)",
        fontSize: "11px",
        fontWeight: 600,
        color: "var(--color-muted-foreground)",
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        margin: "16px 0 8px",
      }}
    >
      {children}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Sample data for charts
// ---------------------------------------------------------------------------

const BAR_DATA = [
  { month: "Jan", "T-ROC": 142, BDS: 98, MarketSource: 76 },
  { month: "Feb", "T-ROC": 158, BDS: 112, MarketSource: 89 },
  { month: "Mar", "T-ROC": 131, BDS: 95, MarketSource: 102 },
  { month: "Apr", "T-ROC": 167, BDS: 128, MarketSource: 91 },
];

const AREA_DATA = [
  { week: "W1", active: 380, new: 42 },
  { week: "W2", active: 395, new: 38 },
  { week: "W3", active: 412, new: 55 },
  { week: "W4", active: 407, new: 31 },
  { week: "W5", active: 430, new: 47 },
];

const DONUT_DATA = [
  { name: "T-ROC", value: 342 },
  { name: "BDS", value: 218 },
  { name: "MarketSource", value: 176 },
  { name: "OSL", value: 94 },
  { name: "2020 Companies", value: 63 },
];

// ---------------------------------------------------------------------------
// Table of contents items
// ---------------------------------------------------------------------------

const TOC = [
  { id: "tokens", label: "Design Tokens" },
  { id: "typography", label: "Typography" },
  { id: "buttons", label: "Button" },
  { id: "inputs", label: "Input" },
  { id: "badges", label: "Badge" },
  { id: "kpi-cards", label: "KPI Card" },
  { id: "section-card", label: "Section Card" },
  { id: "skeleton", label: "Skeleton" },
  { id: "callout", label: "Callout" },
  { id: "mockup-banner", label: "Mockup Banner" },
  { id: "pagination", label: "Table Pagination" },
  { id: "confirm-dialog", label: "Confirm Dialog" },
  { id: "bar-chart", label: "Bar Chart" },
  { id: "area-chart", label: "Area Chart" },
  { id: "donut-chart", label: "Donut Chart" },
  { id: "icons", label: "Icons" },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function StyleGuidePage() {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [paginationPage, setPaginationPage] = useState(3);

  return (
    <div style={{ maxWidth: "960px", margin: "0 auto" }}>
      {/* Page header */}
      <div style={{ marginBottom: "40px" }}>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "28px",
            fontWeight: 700,
            color: "var(--color-foreground)",
            margin: 0,
          }}
        >
          UI Style Guide
        </h1>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "14px",
            color: "var(--color-muted-foreground)",
            margin: "6px 0 0",
            lineHeight: 1.6,
          }}
        >
          All UI elements used across CompGraph, with their source kits labeled.
        </p>
      </div>

      {/* Table of contents */}
      <nav
        aria-label="Style guide sections"
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "6px",
          marginBottom: "36px",
        }}
      >
        {TOC.map((item) => (
          <a
            key={item.id}
            href={`#${item.id}`}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--color-primary)",
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-primary)",
              textDecoration: "none",
              transition: "background-color 150ms, color 150ms",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "var(--color-primary)";
              e.currentTarget.style.color = "#FFFFFF";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
              e.currentTarget.style.color = "var(--color-primary)";
            }}
          >
            {item.label}
          </a>
        ))}
      </nav>

      {/* ================================================================= */}
      {/* DESIGN TOKENS                                                      */}
      {/* ================================================================= */}
      <Section
        id="tokens"
        title="Design Tokens"
        source="Custom — globals.css @theme block (Tailwind CSS v4)"
      >
        <SubLabel>Brand Palette</SubLabel>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: "12px" }}>
          {[
            { name: "Coral", var: "--color-coral", hex: "#EF8354" },
            { name: "Jet Black", var: "--color-jet-black", hex: "#2D3142" },
            { name: "Blue Slate", var: "--color-blue-slate", hex: "#4F5D75" },
            { name: "Silver", var: "--color-silver", hex: "#BFC0C0" },
            { name: "Teal Jade", var: "--color-teal-jade", hex: "#1B998B" },
            { name: "Chestnut", var: "--color-chestnut", hex: "#8C2C23" },
            { name: "Warm Gold", var: "--color-warm-gold", hex: "#DCB256" },
          ].map((c) => (
            <div key={c.var}>
              <div
                style={{
                  width: "100%",
                  height: "48px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: c.hex,
                  border: c.hex === "#BFC0C0" ? "1px solid #A0A0A0" : "none",
                }}
              />
              <p style={{ fontFamily: "var(--font-body)", fontSize: "12px", fontWeight: 600, color: "var(--color-foreground)", margin: "6px 0 0" }}>
                {c.name}
              </p>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--color-muted-foreground)", margin: "2px 0 0" }}>
                {c.hex}
              </p>
            </div>
          ))}
        </div>

        <SubLabel>Semantic Colors</SubLabel>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: "12px" }}>
          {[
            { name: "Background", hex: "#F4F4F0" },
            { name: "Surface", hex: "#FFFFFF" },
            { name: "Surface Raised", hex: "#FAFAF7" },
            { name: "Muted", hex: "#E8E8E4" },
            { name: "Success", hex: "#1B998B" },
            { name: "Warning", hex: "#DCB256" },
            { name: "Error", hex: "#8C2C23" },
          ].map((c) => (
            <div key={c.name}>
              <div
                style={{
                  width: "100%",
                  height: "48px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: c.hex,
                  border: "1px solid var(--color-border)",
                }}
              />
              <p style={{ fontFamily: "var(--font-body)", fontSize: "12px", fontWeight: 600, color: "var(--color-foreground)", margin: "6px 0 0" }}>
                {c.name}
              </p>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--color-muted-foreground)", margin: "2px 0 0" }}>
                {c.hex}
              </p>
            </div>
          ))}
        </div>

        <SubLabel>Chart Palette (5-color sequence)</SubLabel>
        <div style={{ display: "flex", gap: "8px" }}>
          {["#EF8354", "#1B998B", "#4F5D75", "#DCB256", "#8C2C23"].map((hex, i) => (
            <div key={hex} style={{ textAlign: "center" }}>
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "50%",
                  backgroundColor: hex,
                }}
              />
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--color-muted-foreground)", margin: "4px 0 0" }}>
                chart-{i + 1}
              </p>
            </div>
          ))}
        </div>

        <SubLabel>Border Radius Scale</SubLabel>
        <div style={{ display: "flex", gap: "16px", alignItems: "flex-end" }}>
          {[
            { name: "sm", val: "4px", use: "Inputs, badges" },
            { name: "md", val: "6px", use: "Buttons" },
            { name: "lg", val: "8px", use: "Cards" },
            { name: "xl", val: "12px", use: "Modals" },
          ].map((r) => (
            <div key={r.name} style={{ textAlign: "center" }}>
              <div
                style={{
                  width: "56px",
                  height: "56px",
                  border: "2px solid var(--color-primary)",
                  borderRadius: r.val,
                  backgroundColor: "transparent",
                }}
              />
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "11px", fontWeight: 600, margin: "6px 0 0", color: "var(--color-foreground)" }}>
                {r.name}
              </p>
              <p style={{ fontFamily: "var(--font-body)", fontSize: "10px", color: "var(--color-muted-foreground)", margin: "2px 0 0" }}>
                {r.val} &mdash; {r.use}
              </p>
            </div>
          ))}
        </div>

        <SubLabel>Shadow Scale</SubLabel>
        <div style={{ display: "flex", gap: "24px" }}>
          {[
            { name: "sm", shadow: "0 1px 2px 0 rgb(0 0 0 / 0.05)", use: "Cards" },
            { name: "md", shadow: "0 4px 6px -1px rgb(0 0 0 / 0.08)", use: "Dropdowns" },
            { name: "lg", shadow: "0 10px 15px -3px rgb(0 0 0 / 0.10)", use: "Modals" },
          ].map((s) => (
            <div key={s.name} style={{ textAlign: "center" }}>
              <div
                style={{
                  width: "80px",
                  height: "56px",
                  backgroundColor: "var(--color-surface)",
                  borderRadius: "var(--radius-lg)",
                  boxShadow: s.shadow,
                }}
              />
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "11px", fontWeight: 600, margin: "8px 0 0", color: "var(--color-foreground)" }}>
                shadow-{s.name}
              </p>
              <p style={{ fontFamily: "var(--font-body)", fontSize: "10px", color: "var(--color-muted-foreground)", margin: "2px 0 0" }}>
                {s.use}
              </p>
            </div>
          ))}
        </div>
      </Section>

      {/* ================================================================= */}
      {/* TYPOGRAPHY                                                         */}
      {/* ================================================================= */}
      <Section
        id="typography"
        title="Typography"
        source="@fontsource-variable — Sora (display), DM Sans (body), JetBrains Mono (data)"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div>
            <SubLabel>Display — Sora Variable</SubLabel>
            <p style={{ fontFamily: "var(--font-display)", fontSize: "28px", fontWeight: 700, color: "var(--color-foreground)", margin: 0 }}>
              CompGraph Intelligence
            </p>
            <p style={{ fontFamily: "var(--font-display)", fontSize: "18px", fontWeight: 600, color: "var(--color-foreground)", margin: "4px 0 0" }}>
              Section Heading
            </p>
            <p style={{ fontFamily: "var(--font-display)", fontSize: "14px", fontWeight: 500, color: "var(--color-muted-foreground)", margin: "4px 0 0" }}>
              Subsection Label
            </p>
          </div>
          <div>
            <SubLabel>Body — DM Sans Variable</SubLabel>
            <p style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--color-foreground)", margin: 0, lineHeight: 1.6 }}>
              CompGraph tracks hiring velocity, brand relationships, and pay benchmarks across competing field marketing agencies. Data is scraped from public job postings and enriched via a 2-pass LLM pipeline.
            </p>
            <p style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--color-muted-foreground)", margin: "8px 0 0" }}>
              Secondary body text at 13px — labels, descriptions, helper text.
            </p>
            <p style={{ fontFamily: "var(--font-body)", fontSize: "11px", fontWeight: 600, color: "var(--color-muted-foreground)", margin: "8px 0 0", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Uppercase label — 11px, 600 weight, 0.06em tracking
            </p>
          </div>
          <div>
            <SubLabel>Mono — JetBrains Mono Variable</SubLabel>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "24px", fontWeight: 600, color: "var(--color-foreground)", margin: 0 }}>
              1,247
            </p>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "var(--color-muted-foreground)", margin: "4px 0 0" }}>
              user@compgraph.app — monospace for data, emails, code
            </p>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--color-success)", margin: "4px 0 0" }}>
              ▲ 12.4% vs prior week
            </p>
          </div>
        </div>
      </Section>

      {/* ================================================================= */}
      {/* BUTTON                                                             */}
      {/* ================================================================= */}
      <Section
        id="buttons"
        title="Button"
        source="Custom — components/ui/button.tsx"
      >
        <SubLabel>Variants</SubLabel>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center" }}>
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="ghost">Ghost</Button>
        </div>

        <SubLabel>Sizes</SubLabel>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center" }}>
          <Button variant="primary" size="sm">Small</Button>
          <Button variant="primary" size="md">Medium</Button>
          <Button variant="primary" size="lg">Large</Button>
        </div>

        <SubLabel>Disabled State</SubLabel>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center" }}>
          <Button variant="primary" disabled>Primary Disabled</Button>
          <Button variant="secondary" disabled>Secondary Disabled</Button>
          <Button variant="destructive" disabled>Destructive Disabled</Button>
        </div>

        <SubLabel>With Icon</SubLabel>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center" }}>
          <Button variant="primary">
            <EnvelopeIcon style={{ width: 16, height: 16 }} />
            Send Invite
          </Button>
          <Button variant="secondary">
            <MagnifyingGlassIcon style={{ width: 16, height: 16 }} />
            Search
          </Button>
        </div>
      </Section>

      {/* ================================================================= */}
      {/* INPUT                                                              */}
      {/* ================================================================= */}
      <Section
        id="inputs"
        title="Input"
        source="Custom — components/ui/input.tsx"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", maxWidth: "400px" }}>
          <Input label="Default Input" placeholder="Enter something..." />
          <Input label="With Hint" placeholder="you@company.com" hint="We'll send a verification email." />
          <Input label="Error State" placeholder="Enter email" error="This field is required" />
          <Input
            label="With Right Element"
            type={showPassword ? "text" : "password"}
            placeholder="Password"
            value="mysecretpass"
            onChange={() => {}}
            rightElement={
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  cursor: "pointer",
                  display: "flex",
                  color: "var(--color-muted-foreground)",
                }}
              >
                {showPassword ? (
                  <EyeSlashIcon style={{ width: 16, height: 16 }} />
                ) : (
                  <EyeIcon style={{ width: 16, height: 16 }} />
                )}
              </button>
            }
          />
          <div>
            <SubLabel>Locked / Disabled Input</SubLabel>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 12px",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--color-muted)",
                fontFamily: "var(--font-mono)",
                fontSize: "13px",
                color: "var(--color-muted-foreground)",
              }}
            >
              <LockClosedIcon style={{ width: 14, height: 14, flexShrink: 0 }} />
              admin@compgraph.app
            </div>
          </div>
        </div>
      </Section>

      {/* ================================================================= */}
      {/* BADGE                                                              */}
      {/* ================================================================= */}
      <Section
        id="badges"
        title="Badge"
        source="Custom — components/data/badge.tsx"
      >
        <SubLabel>Variants (md)</SubLabel>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
          <Badge variant="success">Active</Badge>
          <Badge variant="warning">Pending</Badge>
          <Badge variant="error">Failed</Badge>
          <Badge variant="neutral">Neutral</Badge>
          <Badge variant="info">Info</Badge>
        </div>

        <SubLabel>Small Size (sm)</SubLabel>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
          <Badge variant="success" size="sm">Live</Badge>
          <Badge variant="warning" size="sm">Stale</Badge>
          <Badge variant="error" size="sm">Down</Badge>
          <Badge variant="neutral" size="sm">N/A</Badge>
        </div>
      </Section>

      {/* ================================================================= */}
      {/* KPI CARD                                                           */}
      {/* ================================================================= */}
      <Section
        id="kpi-cards"
        title="KPI Card"
        source="Custom — components/data/kpi-card.tsx"
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "16px" }}>
          <KpiCard
            label="Active Postings"
            value="1,247"
            icon={<BriefcaseIcon style={{ width: 16, height: 16, color: "#4F5D75" }} />}
            trend={{ value: 12, label: "vs last week" }}
          />
          <KpiCard
            label="Enriched"
            value="94.2%"
            variant="success"
            icon={<CheckCircleIcon style={{ width: 16, height: 16, color: "#1B998B" }} />}
            trend={{ value: 2.1, label: "vs last week" }}
          />
          <KpiCard
            label="Failures"
            value="18"
            variant="error"
            icon={<XCircleIcon style={{ width: 16, height: 16, color: "#8C2C23" }} />}
            trend={{ value: -5, label: "vs last week" }}
          />
          <KpiCard
            label="Avg Pay"
            value="$17.50/hr"
            variant="warning"
            icon={<ChartBarIcon style={{ width: 16, height: 16, color: "#DCB256" }} />}
          />
        </div>
      </Section>

      {/* ================================================================= */}
      {/* SECTION CARD                                                       */}
      {/* ================================================================= */}
      <Section
        id="section-card"
        title="Section Card"
        source="Custom — components/ui/section-card.tsx"
      >
        <SectionCard
          title="Pipeline Overview"
          action={<Badge variant="success">Healthy</Badge>}
        >
          <p
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "14px",
              color: "var(--color-muted-foreground)",
              margin: 0,
            }}
          >
            Section cards are the primary container for grouping related content. They include a title, optional action slot in the header, and free-form children.
          </p>
        </SectionCard>
      </Section>

      {/* ================================================================= */}
      {/* SKELETON                                                           */}
      {/* ================================================================= */}
      <Section
        id="skeleton"
        title="Skeleton"
        source="Custom — components/ui/skeleton.tsx"
      >
        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}</style>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
            margin: "0 0 12px",
          }}
        >
          Loading placeholders with a pulsing animation. Compose to match the layout being loaded.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxWidth: "400px" }}>
          <SkeletonBox style={{ height: "14px", width: "60%" }} />
          <SkeletonBox style={{ height: "10px", width: "80%" }} />
          <SkeletonBox style={{ height: "10px", width: "45%" }} />
          <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
            <SkeletonBox style={{ height: "64px", flex: 1 }} />
            <SkeletonBox style={{ height: "64px", flex: 1 }} />
            <SkeletonBox style={{ height: "64px", flex: 1 }} />
          </div>
        </div>
      </Section>

      {/* ================================================================= */}
      {/* CALLOUT                                                            */}
      {/* ================================================================= */}
      <Section
        id="callout"
        title="Callout"
        source="Custom — components/content/callout.tsx"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <Callout variant="finding" title="Key Finding">
            T-ROC has increased hiring velocity by 23% in the Southeast market over the last 30 days.
          </Callout>
          <Callout variant="positive" title="Positive Signal">
            Enrichment accuracy improved to 96.4% after the latest prompt revision.
          </Callout>
          <Callout variant="risk" title="Risk Alert">
            BDS scraper returned 0 results for 3 consecutive cycles. Possible ATS change.
          </Callout>
          <Callout variant="caution" title="Caution">
            Pay data for this market has fewer than 50 samples. Benchmarks may be unreliable.
          </Callout>
        </div>
      </Section>

      {/* ================================================================= */}
      {/* MOCKUP BANNER                                                      */}
      {/* ================================================================= */}
      <Section
        id="mockup-banner"
        title="Mockup Banner"
        source="Custom — components/content/mockup-banner.tsx"
      >
        <MockupBanner />
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
            margin: "8px 0 0",
          }}
        >
          Displayed on pages using placeholder data during design review. Uses the warning/gold palette with a top border accent.
        </p>
      </Section>

      {/* ================================================================= */}
      {/* TABLE PAGINATION                                                   */}
      {/* ================================================================= */}
      <Section
        id="pagination"
        title="Table Pagination"
        source="Custom — components/data/table-pagination.tsx"
      >
        <div style={{ maxWidth: "400px" }}>
          <TablePagination
            page={paginationPage}
            totalPages={12}
            onFirst={() => setPaginationPage(1)}
            onPrev={() => setPaginationPage((p) => Math.max(1, p - 1))}
            onNext={() => setPaginationPage((p) => Math.min(12, p + 1))}
            onLast={() => setPaginationPage(12)}
          />
        </div>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
            margin: "12px 0 0",
          }}
        >
          First/prev/next/last navigation with disabled states at boundaries. Click to interact.
        </p>
      </Section>

      {/* ================================================================= */}
      {/* CONFIRM DIALOG                                                     */}
      {/* ================================================================= */}
      <Section
        id="confirm-dialog"
        title="Confirm Dialog"
        source="@headlessui/react — Dialog, DialogBackdrop, DialogPanel, DialogTitle"
      >
        <div style={{ display: "flex", gap: "12px" }}>
          <Button variant="primary" onClick={() => setConfirmOpen(true)}>
            Open Confirm Dialog
          </Button>
        </div>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
            margin: "12px 0 0",
          }}
        >
          Modal confirmation with backdrop overlay, async-aware confirm action, and danger variant with ExclamationTriangleIcon. Built on Headless UI Dialog primitives.
        </p>
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          title="Disable this user?"
          description="They will immediately lose access to CompGraph. This cannot be undone without re-inviting them."
          confirmLabel="Disable user"
          confirmVariant="danger"
          onConfirm={() => setConfirmOpen(false)}
        />
      </Section>

      {/* ================================================================= */}
      {/* BAR CHART                                                          */}
      {/* ================================================================= */}
      <Section
        id="bar-chart"
        title="Bar Chart"
        source="Recharts 3 (via @tremor/react BarChart wrapper in production)"
      >
        <div style={{ width: "100%", height: 280, fontFamily: "var(--font-body)" }}>
          <ResponsiveContainer width="100%" height="100%">
            <RechartsBarChart data={BAR_DATA} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E4" />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#4F5D75" }} />
              <YAxis tick={{ fontSize: 12, fill: "#4F5D75" }} />
              <Tooltip
                contentStyle={{
                  fontFamily: "var(--font-body)",
                  fontSize: 13,
                  borderRadius: 6,
                  border: "1px solid #BFC0C0",
                }}
              />
              <Legend wrapperStyle={{ fontFamily: "var(--font-body)", fontSize: 12 }} />
              <Bar dataKey="T-ROC" fill="#EF8354" radius={[3, 3, 0, 0]} />
              <Bar dataKey="BDS" fill="#1B998B" radius={[3, 3, 0, 0]} />
              <Bar dataKey="MarketSource" fill="#4F5D75" radius={[3, 3, 0, 0]} />
            </RechartsBarChart>
          </ResponsiveContainer>
        </div>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
            margin: "8px 0 0",
          }}
        >
          Production uses Tremor BarChart wrapper which delegates to Recharts 3. CompGraph 5-color chart palette applied.
        </p>
      </Section>

      {/* ================================================================= */}
      {/* AREA CHART                                                         */}
      {/* ================================================================= */}
      <Section
        id="area-chart"
        title="Area Chart"
        source="Recharts 3 (via @tremor/react AreaChart wrapper in production)"
      >
        <div style={{ width: "100%", height: 280, fontFamily: "var(--font-body)" }}>
          <ResponsiveContainer width="100%" height="100%">
            <RechartsAreaChart data={AREA_DATA} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
              <defs>
                <linearGradient id="gradActive" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF8354" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#EF8354" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradNew" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1B998B" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1B998B" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E4" />
              <XAxis dataKey="week" tick={{ fontSize: 12, fill: "#4F5D75" }} />
              <YAxis tick={{ fontSize: 12, fill: "#4F5D75" }} />
              <Tooltip
                contentStyle={{
                  fontFamily: "var(--font-body)",
                  fontSize: 13,
                  borderRadius: 6,
                  border: "1px solid #BFC0C0",
                }}
              />
              <Legend wrapperStyle={{ fontFamily: "var(--font-body)", fontSize: 12 }} />
              <Area type="monotone" dataKey="active" name="Active Postings" stroke="#EF8354" fill="url(#gradActive)" strokeWidth={2} />
              <Area type="monotone" dataKey="new" name="New This Week" stroke="#1B998B" fill="url(#gradNew)" strokeWidth={2} />
            </RechartsAreaChart>
          </ResponsiveContainer>
        </div>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
            margin: "8px 0 0",
          }}
        >
          Gradient-filled area chart with legend. Uses the same CHART_COLORS palette and body font as all chart wrappers.
        </p>
      </Section>

      {/* ================================================================= */}
      {/* DONUT CHART                                                        */}
      {/* ================================================================= */}
      <Section
        id="donut-chart"
        title="Donut Chart"
        source="Recharts 3 (via @tremor/react DonutChart wrapper in production)"
      >
        <div style={{ width: 320, height: 280, fontFamily: "var(--font-body)" }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={DONUT_DATA}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={{ stroke: "#BFC0C0" }}
                style={{ fontSize: 11, fontFamily: "var(--font-body)" }}
              >
                {DONUT_DATA.map((_, i) => (
                  <Cell key={i} fill={["#EF8354", "#1B998B", "#4F5D75", "#DCB256", "#8C2C23"][i % 5]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  fontFamily: "var(--font-body)",
                  fontSize: 13,
                  borderRadius: 6,
                  border: "1px solid #BFC0C0",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
            margin: "8px 0 0",
          }}
        >
          Donut variant with labeled slices. Production uses Tremor DonutChart wrapper; slices auto-colored from the chart palette.
        </p>
      </Section>

      {/* ================================================================= */}
      {/* ICONS                                                              */}
      {/* ================================================================= */}
      <Section
        id="icons"
        title="Icons"
        source="@heroicons/react — v2 outline variant (24px)"
      >
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
            margin: "0 0 12px",
          }}
        >
          All icons are from Heroicons v2 (outline, 24px). Used sparingly and only when communicating meaning.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(100px, 1fr))", gap: "16px" }}>
          {[
            { Icon: HomeIcon, label: "HomeIcon" },
            { Icon: BriefcaseIcon, label: "BriefcaseIcon" },
            { Icon: ChartBarIcon, label: "ChartBarIcon" },
            { Icon: EnvelopeIcon, label: "EnvelopeIcon" },
            { Icon: MagnifyingGlassIcon, label: "MagnifyingGlassIcon" },
            { Icon: EyeIcon, label: "EyeIcon" },
            { Icon: EyeSlashIcon, label: "EyeSlashIcon" },
            { Icon: LockClosedIcon, label: "LockClosedIcon" },
            { Icon: CheckCircleIcon, label: "CheckCircleIcon" },
            { Icon: XCircleIcon, label: "XCircleIcon" },
            { Icon: ExclamationTriangleIcon, label: "ExclamationTriangle" },
            { Icon: InformationCircleIcon, label: "InformationCircle" },
          ].map(({ Icon, label }) => (
            <div key={label} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-muted)",
                }}
              >
                <Icon style={{ width: 20, height: 20, color: "var(--color-foreground)" }} />
              </div>
              <p
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "9px",
                  color: "var(--color-muted-foreground)",
                  margin: 0,
                  textAlign: "center",
                  lineHeight: 1.3,
                  wordBreak: "break-all",
                }}
              >
                {label}
              </p>
            </div>
          ))}
        </div>
      </Section>

      {/* ================================================================= */}
      {/* ADDITIONAL PRIMITIVES                                              */}
      {/* ================================================================= */}
      <Section
        id="additional"
        title="Additional Primitives"
        source="Various — @radix-ui, @headlessui/react, sonner, @tremor/react"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <SubLabel>Libraries in Use (not directly demoed)</SubLabel>
            <div
              style={{
                fontFamily: "var(--font-body)",
                fontSize: "13px",
                color: "var(--color-foreground)",
                lineHeight: 1.8,
              }}
            >
              <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: "4px 16px" }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>@radix-ui/react-dialog</span>
                <span>Accessible modal/dialog primitives (used in AddUserDialog)</span>

                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>@radix-ui/react-dropdown-menu</span>
                <span>Dropdown menu primitives (available, not yet in active use)</span>

                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>@radix-ui/react-tooltip</span>
                <span>Tooltip primitives (available, not yet in active use)</span>

                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>@radix-ui/react-slot</span>
                <span>Component composition via Slot pattern</span>

                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>@headlessui/react</span>
                <span>Dialog, DialogBackdrop, DialogPanel, DialogTitle (ConfirmDialog, EditUserDrawer)</span>

                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>sonner</span>
                <span>Toast notification system — success, error, info toasts</span>

                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>@tremor/react</span>
                <span>Chart components (BarChart, AreaChart, DonutChart) + Dialog/DialogPanel</span>

                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>recharts</span>
                <span>Underlying chart engine (wrapped by Tremor, never used directly)</span>

                <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--color-primary)" }}>@supabase/supabase-js</span>
                <span>Auth client — signIn, signUp, updateUser, onAuthStateChange</span>
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* Footer */}
      <div
        style={{
          borderTop: "1px solid var(--color-border)",
          paddingTop: "16px",
          marginBottom: "40px",
        }}
      >
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            color: "var(--color-muted-foreground)",
            margin: 0,
          }}
        >
          CompGraph UI Style Guide — {TOC.length} component sections cataloged
        </p>
      </div>
    </div>
  );
}
