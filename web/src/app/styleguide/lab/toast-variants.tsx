"use client";

import { useCallback, useState, useRef } from "react";
import { toast, Toaster as SonnerToaster } from "sonner";
import reactHotToast, { Toaster as HotToaster } from "react-hot-toast";
import type { Variant } from "./comparison-panel";

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

const btnRow: React.CSSProperties = { display: "flex", gap: 8, flexWrap: "wrap" };

const btnStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: 6,
  border: "1px solid #BFC0C0",
  backgroundColor: "#FFFFFF",
  fontFamily: "var(--font-body)",
  fontSize: 12,
  color: "#2D3142",
  cursor: "pointer",
};

const successBtn: React.CSSProperties = { ...btnStyle, borderColor: "#1B998B", color: "#1B998B" };
const errorBtn: React.CSSProperties = { ...btnStyle, borderColor: "#8C2C23", color: "#8C2C23" };
const infoBtn: React.CSSProperties = { ...btnStyle, borderColor: "#4F5D75", color: "#4F5D75" };

// ---------------------------------------------------------------------------
// Variant 1: Native (custom implementation)
// ---------------------------------------------------------------------------

interface NativeToast {
  id: number;
  message: string;
  type: "success" | "error" | "info";
}

const TOAST_COLORS = {
  success: { bg: "#E6F5F3", border: "#1B998B", text: "#1B998B" },
  error: { bg: "#FDECEA", border: "#8C2C23", text: "#8C2C23" },
  info: { bg: "#F0F1F4", border: "#4F5D75", text: "#4F5D75" },
};

function NativeToastDemo() {
  const [toasts, setToasts] = useState<NativeToast[]>([]);
  const idRef = useRef(0);

  const add = useCallback((message: string, type: NativeToast["type"]) => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000);
  }, []);

  return (
    <div>
      <div style={btnRow}>
        <button type="button" style={successBtn} onClick={() => add("Pipeline completed successfully", "success")}>Success</button>
        <button type="button" style={errorBtn} onClick={() => add("Scraper failed: timeout", "error")}>Error</button>
        <button type="button" style={infoBtn} onClick={() => add("Enrichment batch queued", "info")}>Info</button>
      </div>
      <div style={{ position: "relative", minHeight: 60, marginTop: 12 }}>
        {toasts.map((t) => {
          const c = TOAST_COLORS[t.type];
          return (
            <div
              key={t.id}
              style={{
                padding: "8px 14px",
                marginBottom: 6,
                borderRadius: 6,
                border: `1px solid ${c.border}`,
                backgroundColor: c.bg,
                color: c.text,
                fontFamily: "var(--font-body)",
                fontSize: 13,
                animation: "fadeIn 200ms ease-out",
              }}
            >
              {t.message}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 2: Sonner
// ---------------------------------------------------------------------------

function SonnerDemo() {
  return (
    <div>
      <SonnerToaster position="bottom-right" toastOptions={{ style: { fontFamily: "var(--font-body)", fontSize: 13 } }} />
      <div style={btnRow}>
        <button type="button" style={successBtn} onClick={() => toast.success("Pipeline completed successfully")}>Success</button>
        <button type="button" style={errorBtn} onClick={() => toast.error("Scraper failed: timeout")}>Error</button>
        <button type="button" style={infoBtn} onClick={() => toast("Enrichment batch queued")}>Info</button>
      </div>
      <p style={{ fontFamily: "var(--font-body)", fontSize: 11, color: "#4F5D75", marginTop: 12 }}>
        Toasts appear at bottom-right of viewport ↘
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 3: React Hot Toast
// ---------------------------------------------------------------------------

function HotToastDemo() {
  return (
    <div>
      <HotToaster position="bottom-right" toastOptions={{ style: { fontFamily: "var(--font-body)", fontSize: 13 } }} />
      <div style={btnRow}>
        <button type="button" style={successBtn} onClick={() => reactHotToast.success("Pipeline completed successfully")}>Success</button>
        <button type="button" style={errorBtn} onClick={() => reactHotToast.error("Scraper failed: timeout")}>Error</button>
        <button type="button" style={infoBtn} onClick={() => reactHotToast("Enrichment batch queued")}>Info</button>
      </div>
      <p style={{ fontFamily: "var(--font-body)", fontSize: 11, color: "#4F5D75", marginTop: 12 }}>
        Toasts appear at bottom-right of viewport ↘
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant definitions
// ---------------------------------------------------------------------------

export const toastVariants: Variant[] = [
  {
    id: "native-toast",
    name: "Native Custom",
    library: "vanilla React state",
    render: () => <NativeToastDemo />,
    scorecard: {
      bundleKb: "0",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 0,
      notes:
        "Zero dependency — useState + setTimeout. Full control over positioning, animation, and styling. Must implement stacking, swipe-to-dismiss, and ARIA live regions manually.",
    },
  },
  {
    id: "sonner-toast",
    name: "Sonner",
    library: "sonner",
    render: () => <SonnerDemo />,
    scorecard: {
      bundleKb: "~5",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 3,
      notes:
        "Modern toast library with swipe-to-dismiss, stacking, promise toasts. ARIA live region built-in. Tiny bundle. Style override via toastOptions. Already in project dependencies.",
    },
  },
  {
    id: "hot-toast",
    name: "React Hot Toast",
    library: "react-hot-toast",
    render: () => <HotToastDemo />,
    scorecard: {
      bundleKb: "~5",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 3,
      notes:
        "Similar API to Sonner. Headless mode available for custom rendering. Built-in promise and loading toasts. Slightly older but battle-tested in production apps.",
    },
  },
];
