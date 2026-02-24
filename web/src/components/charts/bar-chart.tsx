"use client";

import React from "react";
import { BarChart as TremorBarChart } from "@tremor/react";

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

export function BarChart({ data, bars, xDataKey, height = 300 }: BarChartProps) {
  const categories = bars.map((b) => b.name);
  const colors = CHART_COLORS.slice(0, categories.length);

  const chartData = data.map((row) => {
    const out: Record<string, unknown> = { [xDataKey]: row[xDataKey] };
    for (const b of bars) {
      out[b.name] = row[b.dataKey];
    }
    return out;
  });

  return (
    <div style={{ height, fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}>
      <TremorBarChart
        data={chartData}
        index={xDataKey}
        categories={categories}
        colors={colors}
        showLegend={true}
        showGridLines={true}
        showXAxis={true}
        showYAxis={true}
        valueFormatter={(v) => String(v)}
      />
    </div>
  );
}
