"use client";

import React from "react";
import { DonutChart as TremorDonutChart } from "@tremor/react";

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

export function DonutChart({ data, centerLabel, height = 280 }: DonutChartProps) {
  const colors = CHART_COLORS.slice(0, data.length);

  return (
    <div style={{ height, fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}>
      <TremorDonutChart
        data={data}
        category="value"
        index="name"
        colors={colors}
        variant="donut"
        showLabel={!!centerLabel}
        label={centerLabel}
        valueFormatter={(v) => v.toLocaleString()}
      />
    </div>
  );
}
