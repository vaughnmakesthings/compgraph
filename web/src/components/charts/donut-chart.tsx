"use client";

import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  type TooltipContentProps,
} from "recharts";

type ValueType = number | string | ReadonlyArray<number | string>;
type NameType = number | string;

const CHART_COLORS = ["#EF8354", "#1B998B", "#4F5D75", "#DCB256", "#8C2C23"];

interface DonutSlice {
  name: string;
  value: number;
}

interface DonutChartProps {
  data: DonutSlice[];
  centerLabel?: string;
  height?: number;
}

function renderTooltip(props: TooltipContentProps<ValueType, NameType>) {
  const { active, payload } = props;
  if (!active || !payload?.length) return null;
  const entry = payload[0];

  return (
    <div
      style={{
        backgroundColor: "#FFFFFF",
        border: "1px solid #BFC0C0",
        borderRadius: "var(--radius-lg, 8px)",
        padding: "8px 12px",
        boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
        fontSize: "12px",
      }}
    >
      <p style={{ color: entry.color, fontWeight: 600 }}>
        {String(entry.name ?? "")}: {String(entry.value ?? "")}
      </p>
    </div>
  );
}

interface CenterLabelProps {
  viewBox?: { cx: number; cy: number };
  total: number;
  label?: string;
}

function CenterLabelContent({ viewBox, total, label }: CenterLabelProps) {
  if (!viewBox) return null;
  const { cx, cy } = viewBox;

  return (
    <g>
      <text
        x={cx}
        y={label ? cy - 10 : cy}
        textAnchor="middle"
        dominantBaseline="middle"
        fontFamily="var(--font-mono, 'JetBrains Mono Variable', monospace)"
        fontSize={22}
        fontWeight={600}
        fill="#2D3142"
      >
        {total.toLocaleString()}
      </text>
      {label && (
        <text
          x={cx}
          y={cy + 18}
          textAnchor="middle"
          dominantBaseline="middle"
          fontFamily="var(--font-body, 'DM Sans Variable', sans-serif)"
          fontSize={11}
          fill="#4F5D75"
        >
          {label}
        </text>
      )}
    </g>
  );
}

export function DonutChart({ data, centerLabel, height = 280 }: DonutChartProps) {
  const total = data.reduce((sum, entry) => sum + entry.value, 0);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="80%"
          dataKey="value"
          strokeWidth={2}
          stroke="#FFFFFF"
          labelLine={false}
          label={false}
        >
          {data.map((entry, index) => (
            <Cell
              key={`cell-${entry.name}`}
              fill={CHART_COLORS[index % CHART_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip content={renderTooltip} />
        <CenterLabelContent total={total} label={centerLabel} />
      </PieChart>
    </ResponsiveContainer>
  );
}
