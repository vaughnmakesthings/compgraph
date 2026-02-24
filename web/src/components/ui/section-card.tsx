import React from "react";

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
      style={{
        backgroundColor: "#FFFFFF",
        borderColor: "#BFC0C0",
        boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-sm font-semibold"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "#2D3142",
          }}
        >
          {title}
        </h2>
        {action && <div>{action}</div>}
      </div>
      {children}
    </div>
  );
}
