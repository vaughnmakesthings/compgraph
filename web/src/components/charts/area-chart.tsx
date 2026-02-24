"use client";

import React from "react";
import { AreaChart as TremorAreaChart } from "@tremor/react";

const CHART_COLORS = ["#EF8354", "#1B998B", "#4F5D75", "#DCB256", "#8C2C23"];

interface AreaDef {
  dataKey: string;
  name: string;
}

interface AreaChartProps {
  data: Array<Record<string, unknown>>;
  areas: AreaDef[];
  xDataKey: string;
  height?: number;
}

export function AreaChart({ data, areas, xDataKey, height = 300 }: AreaChartProps) {
  const categories = areas.map((a) => a.dataKey);
  const colors = CHART_COLORS.slice(0, categories.length);

  return (
    <div style={{ height, fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}>
      <TremorAreaChart
        data={data}
        index={xDataKey}
        categories={categories}
        colors={colors}
        showLegend={true}
        showGridLines={true}
        showXAxis={true}
        showYAxis={true}
        showGradient={true}
        valueFormatter={(v) => String(v)}
      />
    </div>
  );
}
