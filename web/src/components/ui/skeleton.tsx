import React from "react";

interface SkeletonBoxProps {
  className?: string;
  style?: React.CSSProperties;
}

export function SkeletonBox({ className, style }: SkeletonBoxProps) {
  return (
    <div
      className={className}
      style={{
        backgroundColor: "#E8E8E4",
        borderRadius: "var(--radius-lg, 8px)",
        animation: "pulse 1.5s ease-in-out infinite",
        ...style,
      }}
      aria-hidden="true"
    />
  );
}
