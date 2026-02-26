import React from "react";
import { cardStyle, fontBody } from "@/lib/styles";

interface SectionCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}

export function SectionCard({
  title,
  children,
  className = "",
  action,
}: SectionCardProps) {
  return (
    <div
      className={`rounded-lg border p-4 mb-6 ${className}`}
      style={cardStyle}
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-sm font-semibold"
          style={{ ...fontBody, color: "#2D3142" }}
        >
          {title}
        </h2>
        {action && <div>{action}</div>}
      </div>
      {children}
    </div>
  );
}
