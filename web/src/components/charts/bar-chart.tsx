"use client";

import React, { useMemo } from "react";
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipContentProps,
} from "recharts";

type ValueType = number | string | ReadonlyArray<number | string>;
type NameType = number | string;

const CHART_COLORS = ["#EF8354", "#1B998B", "#4F5D75", "#DCB256", "#8C2C23"];

interface BarDef {
  dataKey: string;
  name: string;
}

interface BarChartProps {
  data: Array<Record<string, unknown>>;
  bars: BarDef[];
  xDataKey: string;
  height?: number;
}

function renderTooltip(props: TooltipContentProps<ValueType, NameType>) {
  const { active, payload, label } = props;
  if (!active || !payload?.length) return null;

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
      <p style={{ color: "#2D3142", fontWeight: 600, marginBottom: "4px" }}>
        {String(label ?? "")}
      </p>
      {payload.map((entry, i) => (
        <p
          key={i}
          style={{ color: entry.color, margin: "2px 0" }}
        >
          {String(entry.name ?? "")}: {String(entry.value ?? "")}
        </p>
      ))}
    </div>
  );
}

export function BarChart({ data, bars, xDataKey, height = 300 }: BarChartProps) {
  const axisFontStyle = useMemo(
    () => ({
      fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
      fontSize: 11,
      fill: "#4F5D75",
    }),
    []
  );

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart
        data={data}
        margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
      >
        <CartesianGrid
          strokeDasharray="0"
          stroke="#BFC0C0"
          strokeOpacity={0.3}
          vertical={false}
        />
        <XAxis
          dataKey={xDataKey}
          tick={axisFontStyle}
          tickLine={false}
          axisLine={false}
        />
        <YAxis tick={axisFontStyle} tickLine={false} axisLine={false} />
        <Tooltip content={renderTooltip} />
        <Legend
          wrapperStyle={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "12px",
            paddingTop: "8px",
          }}
        />
        {bars.map((bar, index) => (
          <Bar
            key={bar.dataKey}
            dataKey={bar.dataKey}
            name={bar.name}
            fill={CHART_COLORS[index % CHART_COLORS.length]}
            radius={[2, 2, 0, 0]}
          />
        ))}
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
