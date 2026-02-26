"use client";

import Link from "next/link";
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
import { BarChart as TremorBarChart } from "@tremor/react";
import { AreaChart as TremorAreaChart } from "@tremor/react";
import { DonutChart as TremorDonutChart } from "@tremor/react";
import { ComparisonPanel } from "./comparison-panel";
import type { Variant } from "./comparison-panel";

// ---------------------------------------------------------------------------
// Canonical chart data — identical for all variants
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

const CHART_COLORS = ["#EF8354", "#1B998B", "#4F5D75", "#DCB256", "#8C2C23"];

// ---------------------------------------------------------------------------
// Shared tooltip/axis styling for Recharts variants
// ---------------------------------------------------------------------------

const RECHARTS_TOOLTIP_STYLE = {
  fontFamily: "var(--font-body)",
  fontSize: 13,
  borderRadius: 6,
  border: "1px solid #BFC0C0",
};

const AXIS_TICK = { fontSize: 12, fill: "#4F5D75" };

// ---------------------------------------------------------------------------
// Bar chart variants
// ---------------------------------------------------------------------------

function TremorBar() {
  const data = BAR_DATA.map((row) => ({
    month: row.month,
    "T-ROC": row["T-ROC"],
    BDS: row.BDS,
    MarketSource: row.MarketSource,
  }));

  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <TremorBarChart
        data={data}
        index="month"
        categories={["T-ROC", "BDS", "MarketSource"]}
        colors={CHART_COLORS.slice(0, 3)}
        showLegend
        showGridLines
        showXAxis
        showYAxis
        valueFormatter={(v) => String(v)}
      />
    </div>
  );
}

function RechartsBar() {
  return (
    <div style={{ width: "100%", height: 260, fontFamily: "var(--font-body)" }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart data={BAR_DATA} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E4" />
          <XAxis dataKey="month" tick={AXIS_TICK} />
          <YAxis tick={AXIS_TICK} />
          <Tooltip contentStyle={RECHARTS_TOOLTIP_STYLE} />
          <Legend wrapperStyle={{ fontFamily: "var(--font-body)", fontSize: 12 }} />
          <Bar dataKey="T-ROC" fill="#EF8354" radius={[3, 3, 0, 0]} />
          <Bar dataKey="BDS" fill="#1B998B" radius={[3, 3, 0, 0]} />
          <Bar dataKey="MarketSource" fill="#4F5D75" radius={[3, 3, 0, 0]} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}

const barVariants: Variant[] = [
  {
    id: "tremor-bar",
    name: "Tremor Wrapper",
    library: "@tremor/react BarChart",
    render: () => <TremorBar />,
    scorecard: {
      bundleKb: "~180",
      tokenCompliance: "none",
      a11y: "manual",
      propsNeeded: 8,
      notes:
        "Tremor's colors prop expects named tokens (\"blue\", \"red\"), not hex values. Passing hex strings like \"#EF8354\" silently fails — bars render with no fill. Requires Tremor's own color system or CSS class workarounds to use custom palettes.",
    },
  },
  {
    id: "recharts-bar",
    name: "Recharts Direct",
    library: "recharts",
    render: () => <RechartsBar />,
    scorecard: {
      bundleKb: "~95",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 12,
      notes:
        "Accepts hex colors directly on each <Bar> element. Full control over grid, axes, tooltips, and border radius. More verbose API but no color abstraction layer to fight.",
    },
  },
];

// ---------------------------------------------------------------------------
// Area chart variants
// ---------------------------------------------------------------------------

function TremorArea() {
  const data = AREA_DATA.map((row) => ({
    week: row.week,
    "Active Postings": row.active,
    "New This Week": row.new,
  }));

  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <TremorAreaChart
        data={data}
        index="week"
        categories={["Active Postings", "New This Week"]}
        colors={CHART_COLORS.slice(0, 2)}
        showLegend
        showGridLines
        showXAxis
        showYAxis
        showGradient
        valueFormatter={(v) => String(v)}
      />
    </div>
  );
}

function RechartsArea() {
  return (
    <div style={{ width: "100%", height: 260, fontFamily: "var(--font-body)" }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsAreaChart data={AREA_DATA} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <defs>
            <linearGradient id="labGradActive" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#EF8354" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#EF8354" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="labGradNew" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1B998B" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#1B998B" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E4" />
          <XAxis dataKey="week" tick={AXIS_TICK} />
          <YAxis tick={AXIS_TICK} />
          <Tooltip contentStyle={RECHARTS_TOOLTIP_STYLE} />
          <Legend wrapperStyle={{ fontFamily: "var(--font-body)", fontSize: 12 }} />
          <Area type="monotone" dataKey="active" name="Active Postings" stroke="#EF8354" fill="url(#labGradActive)" strokeWidth={2} />
          <Area type="monotone" dataKey="new" name="New This Week" stroke="#1B998B" fill="url(#labGradNew)" strokeWidth={2} />
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const areaVariants: Variant[] = [
  {
    id: "tremor-area",
    name: "Tremor Wrapper",
    library: "@tremor/react AreaChart",
    render: () => <TremorArea />,
    scorecard: {
      bundleKb: "~180",
      tokenCompliance: "none",
      a11y: "manual",
      propsNeeded: 9,
      notes:
        "Same hex color issue as BarChart. Gradient fills fail silently when colors don't resolve to Tremor tokens.",
    },
  },
  {
    id: "recharts-area",
    name: "Recharts Direct",
    library: "recharts",
    render: () => <RechartsArea />,
    scorecard: {
      bundleKb: "~95",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 14,
      notes:
        "Gradient fills defined via SVG <defs> with direct hex references. Full control over gradient opacity and direction.",
    },
  },
];

// ---------------------------------------------------------------------------
// Donut chart variants
// ---------------------------------------------------------------------------

function TremorDonut() {
  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <TremorDonutChart
        data={DONUT_DATA}
        category="value"
        index="name"
        colors={CHART_COLORS}
        variant="donut"
        showLabel
        label="893"
        valueFormatter={(v) => v.toLocaleString()}
      />
    </div>
  );
}

function RechartsDonut() {
  return (
    <div style={{ width: "100%", height: 260, fontFamily: "var(--font-body)" }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={DONUT_DATA}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
            labelLine={{ stroke: "#BFC0C0" }}
            style={{ fontSize: 11, fontFamily: "var(--font-body)" }}
          >
            {DONUT_DATA.map((_, i) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={RECHARTS_TOOLTIP_STYLE} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

const donutVariants: Variant[] = [
  {
    id: "tremor-donut",
    name: "Tremor Wrapper",
    library: "@tremor/react DonutChart",
    render: () => <TremorDonut />,
    scorecard: {
      bundleKb: "~180",
      tokenCompliance: "none",
      a11y: "manual",
      propsNeeded: 8,
      notes:
        "Tremor DonutChart has a simpler API with built-in center label support. Same color token limitation applies.",
    },
  },
  {
    id: "recharts-donut",
    name: "Recharts Direct",
    library: "recharts",
    render: () => <RechartsDonut />,
    scorecard: {
      bundleKb: "~95",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 11,
      notes:
        "Uses PieChart with innerRadius for donut variant. Each Cell receives a direct hex fill. Label positioning requires manual configuration.",
    },
  },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function LabPage() {
  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "36px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
          <Link
            href="/styleguide"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--color-primary)",
              textDecoration: "none",
            }}
          >
            Style Guide
          </Link>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "#BFC0C0" }}>
            /
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "#4F5D75" }}>
            Lab
          </span>
        </div>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "28px",
            fontWeight: 700,
            color: "#2D3142",
            margin: 0,
          }}
        >
          Component Lab
        </h1>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "14px",
            color: "#4F5D75",
            margin: "6px 0 0",
            lineHeight: 1.6,
            maxWidth: "700px",
          }}
        >
          Compare alternative library implementations side-by-side against the current stack.
          Each variant renders the same canonical data with identical design tokens.
          Use the view modes to evaluate visual fidelity, API ergonomics, and bundle tradeoffs.
        </p>
      </div>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          marginBottom: "32px",
          padding: "12px 16px",
          backgroundColor: "#FAFAF7",
          borderRadius: "var(--radius-lg)",
          border: "1px solid #E8E8E4",
          fontFamily: "var(--font-body)",
          fontSize: "12px",
          color: "#4F5D75",
        }}
      >
        <span><strong style={{ color: "#2D3142" }}>A/B Split</strong> — side-by-side comparison</span>
        <span><strong style={{ color: "#2D3142" }}>Swap</strong> — single view, toggle between variants</span>
        <span><strong style={{ color: "#2D3142" }}>Matrix</strong> — all variants in a grid</span>
      </div>

      {/* Chart comparisons */}
      <ComparisonPanel
        title="Bar Chart"
        description="Grouped bar chart with 3 series across 4 months. Tests: hex color rendering, grid/axis styling, legend positioning, tooltip format."
        variants={barVariants}
      />

      <ComparisonPanel
        title="Area Chart"
        description="Stacked area chart with gradient fills. Tests: SVG gradient support, line smoothing, opacity handling, color token pass-through."
        variants={areaVariants}
      />

      <ComparisonPanel
        title="Donut Chart"
        description="Donut (ring) chart with 5 segments and percentage labels. Tests: inner radius control, label positioning, slice coloring, center label."
        variants={donutVariants}
      />

      {/* How to add a variant */}
      <div
        style={{
          borderTop: "1px solid #E8E8E4",
          paddingTop: "24px",
          marginBottom: "40px",
        }}
      >
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "15px",
            fontWeight: 600,
            color: "#2D3142",
            margin: "0 0 8px",
          }}
        >
          Adding a new variant
        </h2>
        <div
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            color: "#4F5D75",
            lineHeight: 1.7,
          }}
        >
          <ol style={{ margin: 0, paddingLeft: "20px" }}>
            <li>Install the library: <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px", backgroundColor: "#E8E8E4", padding: "1px 5px", borderRadius: "3px" }}>npm install @nivo/bar</code></li>
            <li>Write a render function that accepts the canonical data and returns JSX</li>
            <li>Add a <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px", backgroundColor: "#E8E8E4", padding: "1px 5px", borderRadius: "3px" }}>Variant</code> entry with scorecard metrics</li>
            <li>Append to the relevant variants array — the comparison panel handles the rest</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
