"use client";

import { useState } from "react";
import { api } from "@/lib/api-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type HealthStatus = "idle" | "ok" | "error";

interface SectionCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

function SectionCard({ title, children, className = "" }: SectionCardProps) {
  return (
    <div
      className={`bg-[#FFFFFF] border border-[#BFC0C0] rounded-lg p-5 ${className}`}
      style={{ boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))" }}
    >
      <h2
        className="text-base font-semibold mb-4"
        style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", color: "#2D3142" }}
      >
        {title}
      </h2>
      {children}
    </div>
  );
}

interface OutlineButtonProps {
  onClick?: () => void;
  disabled?: boolean;
  children: React.ReactNode;
  tooltip?: string;
}

function OutlineButton({ onClick, disabled = false, children, tooltip }: OutlineButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      style={{
        border: "1px solid #EF8354",
        color: "#EF8354",
        borderRadius: "var(--radius-md, 6px)",
        padding: "8px 16px",
        fontSize: "14px",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
        backgroundColor: "transparent",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "background-color 150ms",
        width: "100%",
        textAlign: "left",
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = "rgba(239,131,84,0.1)";
        }
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLButtonElement).style.backgroundColor = "transparent";
      }}
    >
      {children}
    </button>
  );
}

interface KvRowProps {
  label: string;
  value: string;
}

function KvRow({ label, value }: KvRowProps) {
  return (
    <div
      className="flex items-center justify-between py-2 border-b last:border-b-0"
      style={{ borderColor: "#BFC0C0" }}
    >
      <span
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          fontSize: "13px",
          color: "#4F5D75",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
          fontSize: "12px",
          color: "#2D3142",
        }}
      >
        {value}
      </span>
    </div>
  );
}

export default function SettingsPage() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("idle");
  const [apiVersion, setApiVersion] = useState<string | null>(null);
  const [healthChecking, setHealthChecking] = useState(false);

  const [aggStatus, setAggStatus] = useState<"idle" | "ok" | "error">("idle");
  const [aggMessage, setAggMessage] = useState<string | null>(null);
  const [aggRunning, setAggRunning] = useState(false);

  async function handleHealthCheck() {
    setHealthChecking(true);
    setHealthStatus("idle");
    try {
      const result = await api.health();
      setHealthStatus("ok");
      setApiVersion(result.version ?? null);
    } catch {
      setHealthStatus("error");
    } finally {
      setHealthChecking(false);
    }
  }

  async function handleTriggerAggregation() {
    setAggRunning(true);
    setAggStatus("idle");
    setAggMessage(null);
    try {
      const result = await api.triggerAggregation();
      setAggStatus("ok");
      setAggMessage(result.status);
    } catch (err) {
      setAggStatus("error");
      setAggMessage(err instanceof Error ? err.message : "Aggregation trigger failed");
    } finally {
      setAggRunning(false);
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display, 'Sora Variable', sans-serif)", color: "#2D3142" }}
        >
          Settings
        </h1>
      </div>

      <SectionCard title="API Health">
        <div className="flex items-center gap-4 mb-3">
          <span
            style={{
              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "12px",
              color: "#4F5D75",
              backgroundColor: "#E8E8E4",
              borderRadius: "4px",
              padding: "3px 8px",
            }}
          >
            {API_URL}
          </span>
          {healthStatus !== "idle" && (
            <span className="flex items-center gap-1.5">
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  backgroundColor: healthStatus === "ok" ? "#1B998B" : "#8C2C23",
                  display: "inline-block",
                }}
                aria-hidden="true"
              />
              <span
                style={{
                  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "13px",
                  color: healthStatus === "ok" ? "#1B998B" : "#8C2C23",
                }}
              >
                {healthStatus === "ok" ? "OK" : "Error"}
              </span>
            </span>
          )}
        </div>
        <OutlineButton onClick={() => void handleHealthCheck()} disabled={healthChecking}>
          {healthChecking ? "Checking..." : "Check Health"}
        </OutlineButton>
      </SectionCard>

      <SectionCard title="Pipeline Controls" className="mt-4">
        <div className="flex flex-col gap-2">
          <OutlineButton
            onClick={() => void handleTriggerAggregation()}
            disabled={aggRunning}
          >
            {aggRunning ? "Running..." : "Trigger Aggregation"}
          </OutlineButton>
          <OutlineButton disabled tooltip="Coming soon">
            Trigger Scrape
          </OutlineButton>
          <OutlineButton disabled tooltip="Coming soon">
            Trigger Enrichment
          </OutlineButton>
        </div>

        {aggStatus !== "idle" && aggMessage && (
          <div
            className="mt-3 rounded px-3 py-2 text-sm"
            style={{
              backgroundColor: aggStatus === "ok" ? "#1B998B1A" : "#8C2C231A",
              color: aggStatus === "ok" ? "#1B998B" : "#8C2C23",
              border: `1px solid ${aggStatus === "ok" ? "#1B998B33" : "#8C2C2333"}`,
              borderRadius: "var(--radius-md, 6px)",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
            }}
            role="status"
          >
            {aggStatus === "ok" ? "Success: " : "Error: "}
            {aggMessage}
          </div>
        )}
      </SectionCard>

      <SectionCard title="System Info" className="mt-4">
        <div>
          <KvRow label="API Version" value={apiVersion ?? "—"} />
          <KvRow label="Database" value="Supabase Postgres 17" />
          <KvRow label="Platform" value="Digital Ocean" />
        </div>
      </SectionCard>
    </div>
  );
}
