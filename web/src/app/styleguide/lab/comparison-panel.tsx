"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Variant {
  id: string;
  name: string;
  library: string;
  render: () => React.ReactNode;
  scorecard: ScorecardData;
}

export interface ScorecardData {
  bundleKb: number | string;
  tokenCompliance: "full" | "partial" | "none";
  a11y: "built-in" | "manual" | "none";
  propsNeeded: number;
  notes: string;
}

type ViewMode = "split" | "swap" | "matrix";

interface ComparisonPanelProps {
  title: string;
  description: string;
  variants: Variant[];
}

// ---------------------------------------------------------------------------
// Scorecard
// ---------------------------------------------------------------------------

const COMPLIANCE_LABEL: Record<ScorecardData["tokenCompliance"], { text: string; color: string }> = {
  full: { text: "Full", color: "#1B998B" },
  partial: { text: "Partial", color: "#DCB256" },
  none: { text: "None", color: "#8C2C23" },
};

const A11Y_LABEL: Record<ScorecardData["a11y"], { text: string; color: string }> = {
  "built-in": { text: "Built-in", color: "#1B998B" },
  manual: { text: "Manual", color: "#DCB256" },
  none: { text: "None", color: "#8C2C23" },
};

function Scorecard({ data }: { data: ScorecardData }) {
  const compliance = COMPLIANCE_LABEL[data.tokenCompliance];
  const a11y = A11Y_LABEL[data.a11y];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: "1px",
        backgroundColor: "#E8E8E4",
        borderRadius: "var(--radius-md)",
        overflow: "hidden",
        fontSize: "11px",
        fontFamily: "var(--font-body)",
      }}
    >
      <div style={{ backgroundColor: "#FAFAF7", padding: "8px 10px", textAlign: "center" }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "14px", fontWeight: 600, color: "#2D3142" }}>
          {typeof data.bundleKb === "number" ? `${data.bundleKb}kb` : data.bundleKb}
        </div>
        <div style={{ color: "#4F5D75", marginTop: "2px" }}>Bundle</div>
      </div>
      <div style={{ backgroundColor: "#FAFAF7", padding: "8px 10px", textAlign: "center" }}>
        <div style={{ fontSize: "12px", fontWeight: 600, color: compliance.color }}>
          {compliance.text}
        </div>
        <div style={{ color: "#4F5D75", marginTop: "2px" }}>Tokens</div>
      </div>
      <div style={{ backgroundColor: "#FAFAF7", padding: "8px 10px", textAlign: "center" }}>
        <div style={{ fontSize: "12px", fontWeight: 600, color: a11y.color }}>
          {a11y.text}
        </div>
        <div style={{ color: "#4F5D75", marginTop: "2px" }}>A11y</div>
      </div>
      <div style={{ backgroundColor: "#FAFAF7", padding: "8px 10px", textAlign: "center" }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "14px", fontWeight: 600, color: "#2D3142" }}>
          {data.propsNeeded}
        </div>
        <div style={{ color: "#4F5D75", marginTop: "2px" }}>Props</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant card
// ---------------------------------------------------------------------------

function VariantCard({ variant, flex }: { variant: Variant; flex?: string }) {
  return (
    <div style={{ flex: flex ?? "1", minWidth: 0 }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: "8px",
          marginBottom: "8px",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "13px",
            fontWeight: 600,
            color: "#2D3142",
          }}
        >
          {variant.name}
        </span>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10px",
            color: "#4F5D75",
            padding: "2px 6px",
            backgroundColor: "#E8E8E4",
            borderRadius: "3px",
          }}
        >
          {variant.library}
        </span>
      </div>

      <div
        style={{
          border: "1px solid #BFC0C0",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "#FFFFFF",
          padding: "16px",
          marginBottom: "8px",
          overflow: "hidden",
        }}
      >
        {variant.render()}
      </div>

      <Scorecard data={variant.scorecard} />

      {variant.scorecard.notes && (
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "11px",
            color: "#4F5D75",
            margin: "6px 0 0",
            lineHeight: 1.5,
            fontStyle: "italic",
          }}
        >
          {variant.scorecard.notes}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mode tabs
// ---------------------------------------------------------------------------

function ModeTabs({
  mode,
  onChange,
}: {
  mode: ViewMode;
  onChange: (m: ViewMode) => void;
}) {
  const modes: { id: ViewMode; label: string }[] = [
    { id: "split", label: "A/B Split" },
    { id: "swap", label: "Swap" },
    { id: "matrix", label: "Matrix" },
  ];

  return (
    <div style={{ display: "flex", gap: "2px", backgroundColor: "#E8E8E4", borderRadius: "var(--radius-md)", padding: "2px" }}>
      {modes.map((m) => (
        <button
          key={m.id}
          type="button"
          onClick={() => onChange(m.id)}
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "12px",
            fontWeight: mode === m.id ? 600 : 400,
            color: mode === m.id ? "#2D3142" : "#4F5D75",
            backgroundColor: mode === m.id ? "#FFFFFF" : "transparent",
            border: "none",
            borderRadius: "var(--radius-sm)",
            padding: "5px 12px",
            cursor: "pointer",
            transition: "background-color 150ms, color 150ms",
          }}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ComparisonPanel
// ---------------------------------------------------------------------------

export function ComparisonPanel({ title, description, variants }: ComparisonPanelProps) {
  const [mode, setMode] = useState<ViewMode>("split");
  const [swapIndex, setSwapIndex] = useState(0);

  return (
    <section style={{ marginBottom: "48px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "16px", gap: "16px", flexWrap: "wrap" }}>
        <div>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "18px",
              fontWeight: 600,
              color: "#2D3142",
              margin: 0,
            }}
          >
            {title}
          </h2>
          <p
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "13px",
              color: "#4F5D75",
              margin: "4px 0 0",
            }}
          >
            {description}
          </p>
        </div>
        <ModeTabs mode={mode} onChange={setMode} />
      </div>

      {/* Split view */}
      {mode === "split" && (
        <div style={{ display: "flex", gap: "20px" }}>
          {variants.map((v) => (
            <VariantCard key={v.id} variant={v} />
          ))}
        </div>
      )}

      {/* Swap view */}
      {mode === "swap" && (
        <div>
          <div style={{ marginBottom: "12px" }}>
            <select
              value={swapIndex}
              onChange={(e) => setSwapIndex(Number(e.target.value))}
              style={{
                fontFamily: "var(--font-body)",
                fontSize: "13px",
                color: "#2D3142",
                padding: "7px 28px 7px 10px",
                border: "1px solid #BFC0C0",
                borderRadius: "var(--radius-md)",
                backgroundColor: "#FFFFFF",
                cursor: "pointer",
                appearance: "auto",
              }}
            >
              {variants.map((v, i) => (
                <option key={v.id} value={i}>
                  {v.name} — {v.library}
                </option>
              ))}
            </select>
          </div>
          <VariantCard variant={variants[swapIndex]} flex="none" />
        </div>
      )}

      {/* Matrix view */}
      {mode === "matrix" && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${Math.min(variants.length, 3)}, 1fr)`,
            gap: "16px",
          }}
        >
          {variants.map((v) => (
            <VariantCard key={v.id} variant={v} />
          ))}
        </div>
      )}
    </section>
  );
}
