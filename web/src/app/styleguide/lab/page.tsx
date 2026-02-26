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
import { scaleBand, scaleLinear, scaleOrdinal } from "@visx/scale";
import { Bar as VisxBar, AreaClosed, Pie as VisxPie } from "@visx/shape";
import { Group } from "@visx/group";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { ParentSize } from "@visx/responsive";
import { LinearGradient } from "@visx/gradient";
import { curveMonotoneX } from "@visx/curve";
import { ResponsiveBar } from "@nivo/bar";
import { ResponsiveLine } from "@nivo/line";
import { ResponsivePie } from "@nivo/pie";
import {
  VictoryBar as VBar,
  VictoryChart,
  VictoryAxis,
  VictoryGroup,
  VictoryArea,
  VictoryPie,
  VictoryTooltip,
  VictoryLegend,
  VictoryStack,
} from "victory";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Filler,
  Title as ChartTitle,
  Tooltip as ChartTooltip,
  Legend as ChartLegend,
} from "chart.js";
import { Bar as ChartJSBar } from "react-chartjs-2";
import { Line as ChartJSLine } from "react-chartjs-2";
import { Doughnut as ChartJSDoughnut } from "react-chartjs-2";
import { ComparisonPanel } from "./comparison-panel";
import type { Variant } from "./comparison-panel";
import { tableVariants } from "./table-variants";
import { selectVariants } from "./select-variants";
import { dialogVariants } from "./dialog-variants";
import { tooltipVariants } from "./tooltip-variants";
import { toastVariants } from "./toast-variants";
import { inputVariants } from "./input-variants";

// ---------------------------------------------------------------------------
// Chart.js registration (required once)
// ---------------------------------------------------------------------------

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Filler,
  ChartTitle,
  ChartTooltip,
  ChartLegend,
);

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

const BAR_KEYS = ["T-ROC", "BDS", "MarketSource"] as const;

function VisxBarChart({ width, height }: { width: number; height: number }) {
  const margin = { top: 8, right: 16, bottom: 40, left: 48 };
  const xMax = width - margin.left - margin.right;
  const yMax = height - margin.top - margin.bottom;

  const x0Scale = scaleBand({ domain: BAR_DATA.map((d) => d.month), range: [0, xMax], padding: 0.2 });
  const x1Scale = scaleBand({ domain: [...BAR_KEYS], range: [0, x0Scale.bandwidth()], padding: 0.05 });
  const yScale = scaleLinear({ domain: [0, 180], range: [yMax, 0] });
  const colorScale = scaleOrdinal({ domain: [...BAR_KEYS], range: CHART_COLORS.slice(0, 3) });

  return (
    <svg width={width} height={height} style={{ fontFamily: "var(--font-body)" }}>
      <Group left={margin.left} top={margin.top}>
        <GridRows scale={yScale} width={xMax} stroke="#E8E8E4" strokeDasharray="3,3" numTicks={5} />
        {BAR_DATA.map((d) => (
          <Group key={d.month} left={x0Scale(d.month) ?? 0}>
            {BAR_KEYS.map((key) => (
              <VisxBar
                key={key}
                x={x1Scale(key) ?? 0}
                y={yScale(d[key])}
                width={x1Scale.bandwidth()}
                height={yMax - yScale(d[key])}
                fill={colorScale(key)}
                rx={3}
              />
            ))}
          </Group>
        ))}
        <AxisBottom top={yMax} scale={x0Scale} tickLabelProps={{ fontSize: 12, fill: "#4F5D75", fontFamily: "var(--font-body)", textAnchor: "middle" }} hideTicks hideAxisLine />
        <AxisLeft scale={yScale} numTicks={5} tickLabelProps={{ fontSize: 12, fill: "#4F5D75", fontFamily: "var(--font-body)", textAnchor: "end", dx: -4 }} hideTicks hideAxisLine />
      </Group>
      {/* Legend */}
      <Group top={height - 8}>
        {BAR_KEYS.map((key, i) => (
          <Group key={key} left={margin.left + i * 100}>
            <rect width={10} height={10} fill={colorScale(key)} rx={2} y={-10} />
            <text x={14} fontSize={11} fill="#4F5D75" fontFamily="var(--font-body)" dominantBaseline="hanging" y={-10}>{key}</text>
          </Group>
        ))}
      </Group>
    </svg>
  );
}

function VisxBarWrapper() {
  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ParentSize>{({ width }) => <VisxBarChart width={width} height={260} />}</ParentSize>
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

function NivoBar() {
  const data = BAR_DATA.map((row) => ({
    month: row.month,
    "T-ROC": row["T-ROC"],
    BDS: row.BDS,
    MarketSource: row.MarketSource,
  }));

  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ResponsiveBar
        data={data}
        keys={["T-ROC", "BDS", "MarketSource"]}
        indexBy="month"
        groupMode="grouped"
        margin={{ top: 8, right: 16, bottom: 40, left: 48 }}
        padding={0.2}
        colors={CHART_COLORS.slice(0, 3)}
        borderRadius={3}
        axisBottom={{ tickSize: 0, tickPadding: 8 }}
        axisLeft={{ tickSize: 0, tickPadding: 8 }}
        gridYValues={5}
        enableLabel={false}
        legends={[
          {
            dataFrom: "keys",
            anchor: "bottom",
            direction: "row",
            translateY: 36,
            itemWidth: 100,
            itemHeight: 16,
            itemTextColor: "#4F5D75",
            symbolSize: 10,
            symbolShape: "square",
          },
        ]}
        theme={{
          text: { fontFamily: "var(--font-body)", fontSize: 12 },
          grid: { line: { stroke: "#E8E8E4", strokeDasharray: "3 3" } },
          tooltip: { container: { fontFamily: "var(--font-body)", fontSize: 13, borderRadius: 6, border: "1px solid #BFC0C0" } },
        }}
      />
    </div>
  );
}

function VictoryBar() {
  const series = ["T-ROC", "BDS", "MarketSource"] as const;
  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <VictoryChart domainPadding={{ x: 30 }} height={260} padding={{ top: 8, right: 16, bottom: 50, left: 48 }}>
        <VictoryAxis tickFormat={(t: string) => t} style={{ tickLabels: { fontSize: 11, fill: "#4F5D75", fontFamily: "var(--font-body)" }, grid: { stroke: "none" } }} />
        <VictoryAxis dependentAxis style={{ tickLabels: { fontSize: 11, fill: "#4F5D75", fontFamily: "var(--font-body)" }, grid: { stroke: "#E8E8E4", strokeDasharray: "3,3" } }} />
        <VictoryGroup offset={16} colorScale={CHART_COLORS.slice(0, 3)}>
          {series.map((key) => (
            <VBar key={key} data={BAR_DATA.map((d) => ({ x: d.month, y: d[key] }))} cornerRadius={{ top: 3 }} labelComponent={<VictoryTooltip />} />
          ))}
        </VictoryGroup>
        <VictoryLegend
          x={60}
          y={230}
          orientation="horizontal"
          gutter={20}
          data={series.map((s, i) => ({ name: s, symbol: { fill: CHART_COLORS[i] } }))}
          style={{ labels: { fontSize: 11, fill: "#4F5D75", fontFamily: "var(--font-body)" } }}
        />
      </VictoryChart>
    </div>
  );
}

function ChartJSBarChart() {
  const data = {
    labels: BAR_DATA.map((d) => d.month),
    datasets: [
      { label: "T-ROC", data: BAR_DATA.map((d) => d["T-ROC"]), backgroundColor: "#EF8354", borderRadius: 3 },
      { label: "BDS", data: BAR_DATA.map((d) => d.BDS), backgroundColor: "#1B998B", borderRadius: 3 },
      { label: "MarketSource", data: BAR_DATA.map((d) => d.MarketSource), backgroundColor: "#4F5D75", borderRadius: 3 },
    ],
  };

  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ChartJSBar
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "bottom", labels: { font: { family: "var(--font-body)", size: 12 }, color: "#4F5D75", usePointStyle: true, pointStyle: "rect" } } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { family: "var(--font-body)", size: 12 }, color: "#4F5D75" } },
            y: { grid: { color: "#E8E8E4" }, ticks: { font: { family: "var(--font-body)", size: 12 }, color: "#4F5D75" }, border: { dash: [3, 3] } },
          },
        }}
      />
    </div>
  );
}

const barVariants: Variant[] = [
  {
    id: "visx-bar",
    name: "visx",
    library: "@visx/shape + @visx/scale",
    render: () => <VisxBarWrapper />,
    scorecard: {
      bundleKb: "~45",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 18,
      notes:
        "Low-level D3 primitives by Airbnb. Maximum control over every SVG element. Smallest bundle of any SVG library. Requires manual assembly of scales, axes, and layout — no pre-built chart components.",
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
  {
    id: "nivo-bar",
    name: "Nivo",
    library: "@nivo/bar",
    render: () => <NivoBar />,
    scorecard: {
      bundleKb: "~120",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 10,
      notes:
        "Declarative API built on D3. Accepts hex color arrays directly. Built-in ARIA attributes and keyboard navigation. Rich theming system with sensible defaults.",
    },
  },
  {
    id: "victory-bar",
    name: "Victory",
    library: "victory",
    render: () => <VictoryBar />,
    scorecard: {
      bundleKb: "~100",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 14,
      notes:
        "Composable component model — each axis, series, and legend is a separate component. Hex colors via colorScale prop. Built-in animation support. Verbose but highly customizable.",
    },
  },
  {
    id: "chartjs-bar",
    name: "Chart.js",
    library: "react-chartjs-2",
    render: () => <ChartJSBarChart />,
    scorecard: {
      bundleKb: "~60",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 6,
      notes:
        "Canvas-based (not SVG). Smallest bundle. Config-object API instead of JSX components. Hex colors in dataset objects. Built-in accessibility via canvas fallback content.",
    },
  },
];

// ---------------------------------------------------------------------------
// Area chart variants
// ---------------------------------------------------------------------------

function VisxAreaChart({ width, height }: { width: number; height: number }) {
  const margin = { top: 8, right: 16, bottom: 40, left: 48 };
  const xMax = width - margin.left - margin.right;
  const yMax = height - margin.top - margin.bottom;

  const xScale = scaleBand({ domain: AREA_DATA.map((d) => d.week), range: [0, xMax], padding: 0.1 });
  const yScale = scaleLinear({ domain: [0, 600], range: [yMax, 0] });

  const getX = (d: (typeof AREA_DATA)[0]) => (xScale(d.week) ?? 0) + xScale.bandwidth() / 2;

  return (
    <svg width={width} height={height} style={{ fontFamily: "var(--font-body)" }}>
      <LinearGradient id="visx-grad-active" from="#EF8354" fromOpacity={0.3} to="#EF8354" toOpacity={0} />
      <LinearGradient id="visx-grad-new" from="#1B998B" fromOpacity={0.3} to="#1B998B" toOpacity={0} />
      <Group left={margin.left} top={margin.top}>
        <GridRows scale={yScale} width={xMax} stroke="#E8E8E4" strokeDasharray="3,3" numTicks={5} />
        <AreaClosed
          data={AREA_DATA}
          x={getX}
          y={(d) => yScale(d.active)}
          yScale={yScale}
          curve={curveMonotoneX}
          fill="url(#visx-grad-active)"
          stroke="#EF8354"
          strokeWidth={2}
        />
        <AreaClosed
          data={AREA_DATA}
          x={getX}
          y={(d) => yScale(d.new)}
          yScale={yScale}
          curve={curveMonotoneX}
          fill="url(#visx-grad-new)"
          stroke="#1B998B"
          strokeWidth={2}
        />
        <AxisBottom top={yMax} scale={xScale} tickLabelProps={{ fontSize: 12, fill: "#4F5D75", fontFamily: "var(--font-body)", textAnchor: "middle" }} hideTicks hideAxisLine />
        <AxisLeft scale={yScale} numTicks={5} tickLabelProps={{ fontSize: 12, fill: "#4F5D75", fontFamily: "var(--font-body)", textAnchor: "end", dx: -4 }} hideTicks hideAxisLine />
      </Group>
      {/* Legend */}
      <Group top={height - 8}>
        {["Active Postings", "New This Week"].map((label, i) => (
          <Group key={label} left={margin.left + i * 130}>
            <circle r={5} fill={CHART_COLORS[i]} cy={-5} />
            <text x={10} fontSize={11} fill="#4F5D75" fontFamily="var(--font-body)" dominantBaseline="hanging" y={-10}>{label}</text>
          </Group>
        ))}
      </Group>
    </svg>
  );
}

function VisxAreaWrapper() {
  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ParentSize>{({ width }) => <VisxAreaChart width={width} height={260} />}</ParentSize>
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

function NivoArea() {
  const data = [
    {
      id: "Active Postings",
      color: "#EF8354",
      data: AREA_DATA.map((d) => ({ x: d.week, y: d.active })),
    },
    {
      id: "New This Week",
      color: "#1B998B",
      data: AREA_DATA.map((d) => ({ x: d.week, y: d.new })),
    },
  ];

  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ResponsiveLine
        data={data}
        margin={{ top: 8, right: 16, bottom: 40, left: 48 }}
        xScale={{ type: "point" }}
        yScale={{ type: "linear", min: 0, max: "auto" }}
        curve="monotoneX"
        enableArea
        areaOpacity={0.15}
        colors={["#EF8354", "#1B998B"]}
        lineWidth={2}
        pointSize={6}
        pointColor={{ from: "color" }}
        pointBorderWidth={2}
        pointBorderColor="#FFFFFF"
        enableGridX={false}
        gridYValues={5}
        axisBottom={{ tickSize: 0, tickPadding: 8 }}
        axisLeft={{ tickSize: 0, tickPadding: 8 }}
        legends={[
          {
            anchor: "bottom",
            direction: "row",
            translateY: 36,
            itemWidth: 120,
            itemHeight: 16,
            itemTextColor: "#4F5D75",
            symbolSize: 10,
            symbolShape: "circle",
          },
        ]}
        theme={{
          text: { fontFamily: "var(--font-body)", fontSize: 12 },
          grid: { line: { stroke: "#E8E8E4", strokeDasharray: "3 3" } },
          tooltip: { container: { fontFamily: "var(--font-body)", fontSize: 13, borderRadius: 6, border: "1px solid #BFC0C0" } },
        }}
      />
    </div>
  );
}

function VictoryAreaChart() {
  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <VictoryChart height={260} padding={{ top: 8, right: 16, bottom: 50, left: 48 }}>
        <VictoryAxis tickFormat={(t: string) => t} style={{ tickLabels: { fontSize: 11, fill: "#4F5D75", fontFamily: "var(--font-body)" }, grid: { stroke: "none" } }} />
        <VictoryAxis dependentAxis style={{ tickLabels: { fontSize: 11, fill: "#4F5D75", fontFamily: "var(--font-body)" }, grid: { stroke: "#E8E8E4", strokeDasharray: "3,3" } }} />
        <VictoryStack>
          <VictoryArea
            data={AREA_DATA.map((d) => ({ x: d.week, y: d.active }))}
            style={{ data: { fill: "#EF8354", fillOpacity: 0.2, stroke: "#EF8354", strokeWidth: 2 } }}
            interpolation="monotoneX"
          />
          <VictoryArea
            data={AREA_DATA.map((d) => ({ x: d.week, y: d.new }))}
            style={{ data: { fill: "#1B998B", fillOpacity: 0.2, stroke: "#1B998B", strokeWidth: 2 } }}
            interpolation="monotoneX"
          />
        </VictoryStack>
        <VictoryLegend
          x={60}
          y={230}
          orientation="horizontal"
          gutter={20}
          data={[
            { name: "Active Postings", symbol: { fill: "#EF8354" } },
            { name: "New This Week", symbol: { fill: "#1B998B" } },
          ]}
          style={{ labels: { fontSize: 11, fill: "#4F5D75", fontFamily: "var(--font-body)" } }}
        />
      </VictoryChart>
    </div>
  );
}

function ChartJSAreaChart() {
  const data = {
    labels: AREA_DATA.map((d) => d.week),
    datasets: [
      {
        label: "Active Postings",
        data: AREA_DATA.map((d) => d.active),
        borderColor: "#EF8354",
        backgroundColor: "rgba(239, 131, 84, 0.15)",
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: "#EF8354",
        borderWidth: 2,
      },
      {
        label: "New This Week",
        data: AREA_DATA.map((d) => d.new),
        borderColor: "#1B998B",
        backgroundColor: "rgba(27, 153, 139, 0.15)",
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: "#1B998B",
        borderWidth: 2,
      },
    ],
  };

  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ChartJSLine
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "bottom", labels: { font: { family: "var(--font-body)", size: 12 }, color: "#4F5D75", usePointStyle: true } } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { family: "var(--font-body)", size: 12 }, color: "#4F5D75" } },
            y: { grid: { color: "#E8E8E4" }, ticks: { font: { family: "var(--font-body)", size: 12 }, color: "#4F5D75" }, border: { dash: [3, 3] } },
          },
        }}
      />
    </div>
  );
}

const areaVariants: Variant[] = [
  {
    id: "visx-area",
    name: "visx",
    library: "@visx/shape + @visx/gradient",
    render: () => <VisxAreaWrapper />,
    scorecard: {
      bundleKb: "~45",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 16,
      notes:
        "AreaClosed with LinearGradient and curveMonotoneX. Direct SVG gradient control. Each area is an independent shape — no stacking abstraction, full layout freedom.",
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
  {
    id: "nivo-area",
    name: "Nivo",
    library: "@nivo/line",
    render: () => <NivoArea />,
    scorecard: {
      bundleKb: "~130",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 12,
      notes:
        "Uses ResponsiveLine with enableArea. Built-in gradient support and smooth curve interpolation. Color array maps directly to series. Rich tooltip theming.",
    },
  },
  {
    id: "victory-area",
    name: "Victory",
    library: "victory",
    render: () => <VictoryAreaChart />,
    scorecard: {
      bundleKb: "~100",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 16,
      notes:
        "VictoryStack + VictoryArea composition. Hex colors in style objects. Monotone interpolation available. Most verbose API of the group but maximum layout control.",
    },
  },
  {
    id: "chartjs-area",
    name: "Chart.js",
    library: "react-chartjs-2",
    render: () => <ChartJSAreaChart />,
    scorecard: {
      bundleKb: "~60",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 6,
      notes:
        "Canvas-based Line chart with fill:true. RGBA colors for gradient-like transparency. Tension property for curve smoothing. Compact config object.",
    },
  },
];

// ---------------------------------------------------------------------------
// Donut chart variants
// ---------------------------------------------------------------------------

function VisxDonutChart({ width, height }: { width: number; height: number }) {
  const radius = Math.min(width, height) / 2 - 30;
  const innerRadius = radius * 0.55;
  const colorScale = scaleOrdinal({ domain: DONUT_DATA.map((d) => d.name), range: CHART_COLORS });
  const total = DONUT_DATA.reduce((sum, d) => sum + d.value, 0);

  return (
    <svg width={width} height={height} style={{ fontFamily: "var(--font-body)" }}>
      <Group top={height / 2} left={width / 2}>
        <VisxPie
          data={DONUT_DATA}
          pieValue={(d) => d.value}
          outerRadius={radius}
          innerRadius={innerRadius}
          padAngle={0.02}
          cornerRadius={2}
        >
          {(pie) =>
            pie.arcs.map((arc) => {
              const [cx, cy] = pie.path.centroid(arc);
              const pct = Math.round((arc.data.value / total) * 100);
              return (
                <g key={arc.data.name}>
                  <path d={pie.path(arc) || ""} fill={colorScale(arc.data.name)} />
                  {pct >= 10 && (
                    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" fontSize={10} fill="#FFFFFF" fontWeight={600}>
                      {pct}%
                    </text>
                  )}
                </g>
              );
            })
          }
        </VisxPie>
      </Group>
      {/* Legend */}
      <Group top={height - 16} left={width / 2 - (DONUT_DATA.length * 80) / 2}>
        {DONUT_DATA.map((d, i) => (
          <Group key={d.name} left={i * 80}>
            <circle r={4} fill={colorScale(d.name)} cy={-4} />
            <text x={8} fontSize={10} fill="#4F5D75" fontFamily="var(--font-body)" dominantBaseline="hanging" y={-8}>
              {d.name.length > 8 ? d.name.slice(0, 8) + "…" : d.name}
            </text>
          </Group>
        ))}
      </Group>
    </svg>
  );
}

function VisxDonutWrapper() {
  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ParentSize>{({ width }) => <VisxDonutChart width={width} height={260} />}</ParentSize>
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

function NivoDonut() {
  const data = DONUT_DATA.map((d, i) => ({
    id: d.name,
    label: d.name,
    value: d.value,
    color: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ResponsivePie
        data={data}
        margin={{ top: 20, right: 80, bottom: 20, left: 80 }}
        innerRadius={0.55}
        padAngle={1.5}
        cornerRadius={2}
        colors={CHART_COLORS}
        borderWidth={0}
        arcLinkLabelsSkipAngle={10}
        arcLinkLabelsTextColor="#4F5D75"
        arcLinkLabelsThickness={1}
        arcLinkLabelsColor={{ from: "color" }}
        arcLabelsSkipAngle={10}
        arcLabelsTextColor="#FFFFFF"
        enableArcLabels={false}
        theme={{
          text: { fontFamily: "var(--font-body)", fontSize: 11 },
          tooltip: { container: { fontFamily: "var(--font-body)", fontSize: 13, borderRadius: 6, border: "1px solid #BFC0C0" } },
        }}
      />
    </div>
  );
}

function VictoryDonut() {
  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)", display: "flex", justifyContent: "center" }}>
      <VictoryPie
        data={DONUT_DATA.map((d) => ({ x: d.name, y: d.value }))}
        colorScale={CHART_COLORS}
        innerRadius={55}
        padAngle={2}
        height={260}
        width={400}
        labels={({ datum }) => `${datum.x} ${Math.round((datum.y / 893) * 100)}%`}
        labelRadius={110}
        style={{ labels: { fontSize: 10, fill: "#4F5D75", fontFamily: "var(--font-body)" } }}
      />
    </div>
  );
}

function ChartJSDonut() {
  const data = {
    labels: DONUT_DATA.map((d) => d.name),
    datasets: [
      {
        data: DONUT_DATA.map((d) => d.value),
        backgroundColor: CHART_COLORS,
        borderWidth: 0,
        spacing: 2,
        borderRadius: 2,
      },
    ],
  };

  return (
    <div style={{ height: 260, fontFamily: "var(--font-body)" }}>
      <ChartJSDoughnut
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          cutout: "55%",
          plugins: {
            legend: {
              position: "right",
              labels: { font: { family: "var(--font-body)", size: 11 }, color: "#4F5D75", usePointStyle: true, pointStyle: "circle", padding: 12 },
            },
          },
        }}
      />
    </div>
  );
}

const donutVariants: Variant[] = [
  {
    id: "visx-donut",
    name: "visx",
    library: "@visx/shape Pie",
    render: () => <VisxDonutWrapper />,
    scorecard: {
      bundleKb: "~45",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 12,
      notes:
        "Pie component with innerRadius for donut. Render-prop pattern exposes arc paths for full SVG control. Percentage labels positioned via centroid math. Smallest donut implementation by bundle.",
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
  {
    id: "nivo-donut",
    name: "Nivo",
    library: "@nivo/pie",
    render: () => <NivoDonut />,
    scorecard: {
      bundleKb: "~110",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 10,
      notes:
        "ResponsivePie with innerRadius for donut. Built-in arc link labels, pad angle, corner radius. Hex colors via array. ARIA roles included by default.",
    },
  },
  {
    id: "victory-donut",
    name: "Victory",
    library: "victory",
    render: () => <VictoryDonut />,
    scorecard: {
      bundleKb: "~100",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 9,
      notes:
        "VictoryPie with innerRadius. Hex colors via colorScale array. Label positioning via labelRadius. Simplest pie/donut API of the composable libraries.",
    },
  },
  {
    id: "chartjs-donut",
    name: "Chart.js",
    library: "react-chartjs-2",
    render: () => <ChartJSDonut />,
    scorecard: {
      bundleKb: "~60",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 5,
      notes:
        "Canvas Doughnut with cutout percentage. Hex colors in backgroundColor array. Built-in legend positioning. Fewest props needed across all libraries.",
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

      {/* Data table comparisons */}
      <ComparisonPanel
        title="Data Table"
        description="Sortable data table with 10 rows, 6 columns (text, currency, status badge, date). Tests: column sorting, row hover, header styling, custom cell renderers, global search."
        variants={tableVariants}
      />

      {/* Select/Dropdown comparisons */}
      <ComparisonPanel
        title="Select / Dropdown"
        description="Single-select dropdown with 5 options and status filter. Tests: keyboard navigation, ARIA roles, custom styling, portal rendering, checkmark indicators."
        variants={selectVariants}
      />

      {/* Dialog comparisons */}
      <ComparisonPanel
        title="Dialog / Modal"
        description="Confirmation dialog with title, body, Cancel and Confirm buttons. Tests: focus trapping, scroll lock, backdrop click-to-close, ARIA roles, portal rendering."
        variants={dialogVariants}
      />

      {/* Tooltip comparisons */}
      <ComparisonPanel
        title="Tooltip"
        description="Hover-triggered tooltip with multi-line content. Tests: positioning, portal rendering, keyboard trigger, delay, arrow indicator."
        variants={tooltipVariants}
      />

      {/* Toast comparisons */}
      <ComparisonPanel
        title="Toast / Notification"
        description="Transient success/error/info notifications. Tests: auto-dismiss, stacking, position control, ARIA live region, swipe-to-dismiss."
        variants={toastVariants}
      />

      {/* Input comparisons */}
      <ComparisonPanel
        title="Checkbox / Toggle / Radio"
        description="Form input controls with labels and hint text. Tests: indeterminate state, switch ARIA role, radio group keyboard navigation, custom styling."
        variants={inputVariants}
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
