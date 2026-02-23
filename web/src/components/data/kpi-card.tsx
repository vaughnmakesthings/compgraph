"use client";

import React from "react";

interface KpiCardTrend {
  value: number;
  label: string;
}

type KpiCardVariant = "default" | "success" | "warning" | "error";

interface KpiCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: KpiCardTrend;
  variant?: KpiCardVariant;
}

const variantBorderMap: Record<KpiCardVariant, string> = {
  default: "border-[#BFC0C0]",
  success: "border-[#1B998B]",
  warning: "border-[#DCB256]",
  error: "border-[#8C2C23]",
};

export function KpiCard({
  label,
  value,
  icon,
  trend,
  variant = "default",
}: KpiCardProps) {
  const trendIsPositive = trend && trend.value > 0;
  const trendIsNegative = trend && trend.value < 0;

  return (
    <div
      className={`bg-[#FFFFFF] border ${variantBorderMap[variant]} rounded-lg p-4`}
      style={{
        borderRadius: "var(--radius-lg, 8px)",
        boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p
            className="text-[#4F5D75] font-medium tracking-wider uppercase mb-1"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
            }}
          >
            {label}
          </p>
          <p
            className="text-[#2D3142] font-semibold leading-none"
            style={{
              fontFamily:
                "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "28px",
            }}
          >
            {value}
          </p>
          {trend && (
            <p
              className="mt-1.5"
              style={{
                fontFamily:
                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                fontSize: "12px",
                color: trendIsPositive
                  ? "#1B998B"
                  : trendIsNegative
                    ? "#8C2C23"
                    : "#4F5D75",
              }}
            >
              {trendIsPositive ? "↑" : trendIsNegative ? "↓" : "→"}{" "}
              {Math.abs(trend.value)}% {trend.label}
            </p>
          )}
        </div>
        {icon && (
          <div
            className="flex-shrink-0 flex items-center justify-center bg-[#E8E8E4]"
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "var(--radius-sm, 4px)",
            }}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
