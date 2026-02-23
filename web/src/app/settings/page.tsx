"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { ScrapeRunSummary, EnrichmentRunSummary } from "@/lib/types";

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

function formatTs(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "completed" ? "#1B998B"
    : status === "running" ? "#DCB256"
    : status === "failed" ? "#8C2C23"
    : "#BFC0C0";
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        borderRadius: "50%",
        backgroundColor: color,
        marginRight: 5,
        verticalAlign: "middle",
      }}
      aria-hidden="true"
    />
  );
}

export default function SettingsPage() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("idle");
  const [apiVersion, setApiVersion] = useState<string | null>(null);
  const [healthChecking, setHealthChecking] = useState(false);

  const [aggStatus, setAggStatus] = useState<"idle" | "ok" | "error">("idle");
  const [aggMessage, setAggMessage] = useState<string | null>(null);
  const [aggRunning, setAggRunning] = useState(false);

  const [scrapeRuns, setScrapeRuns] = useState<ScrapeRunSummary[]>([]);
  const [enrichRuns, setEnrichRuns] = useState<EnrichmentRunSummary[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void api.getPipelineRuns().then((data) => {
      if (!cancelled) {
        setScrapeRuns(data.scrape_runs);
        setEnrichRuns(data.enrichment_runs);
        setRunsLoading(false);
      }
    }).catch(() => {
      if (!cancelled) setRunsLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

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

      <SectionCard title="Scrape Run History" className="mt-4">
        {runsLoading ? (
          <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: "13px", color: "#4F5D75" }}>Loading…</p>
        ) : scrapeRuns.length === 0 ? (
          <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: "13px", color: "#4F5D75" }}>No scrape runs recorded.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ borderBottom: "1px solid #BFC0C0", backgroundColor: "#F4F4F0" }}>
                  {["Company", "Status", "Started", "Duration", "Found", "Created", "Closed"].map((col) => (
                    <th key={col} className="text-left px-3 py-2"
                      style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontWeight: 600, color: "#4F5D75", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {scrapeRuns.map((r) => {
                  const dur = r.completed_at && r.started_at
                    ? Math.round((new Date(r.completed_at).getTime() - new Date(r.started_at).getTime()) / 1000) + "s"
                    : "—";
                  return (
                    <tr key={r.id} style={{ borderBottom: "1px solid #E8E8E4" }}>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", color: "#2D3142" }}>{r.company_name}</td>
                      <td className="px-3 py-1.5" style={{ color: "#4F5D75" }}>
                        <StatusDot status={r.status} />{r.status}
                      </td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#4F5D75", whiteSpace: "nowrap" }}>{formatTs(r.started_at)}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#4F5D75" }}>{dur}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#2D3142" }}>{r.jobs_found}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#2D3142" }}>{r.snapshots_created}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#2D3142" }}>{r.postings_closed}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Enrichment Run History" className="mt-4">
        {runsLoading ? (
          <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: "13px", color: "#4F5D75" }}>Loading…</p>
        ) : enrichRuns.length === 0 ? (
          <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: "13px", color: "#4F5D75" }}>No enrichment runs recorded.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ borderBottom: "1px solid #BFC0C0", backgroundColor: "#F4F4F0" }}>
                  {["Status", "Started", "Duration", "P1 Total", "P1 OK", "P2 Total", "P2 OK"].map((col) => (
                    <th key={col} className="text-left px-3 py-2"
                      style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontWeight: 600, color: "#4F5D75", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {enrichRuns.map((r) => {
                  const dur = r.finished_at && r.started_at
                    ? Math.round((new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()) / 1000) + "s"
                    : "—";
                  return (
                    <tr key={r.id} style={{ borderBottom: "1px solid #E8E8E4" }}>
                      <td className="px-3 py-1.5" style={{ color: "#4F5D75" }}>
                        <StatusDot status={r.status} />{r.status}
                      </td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#4F5D75", whiteSpace: "nowrap" }}>{formatTs(r.started_at)}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#4F5D75" }}>{dur}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#2D3142" }}>{r.pass1_total}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#1B998B" }}>{r.pass1_succeeded}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#2D3142" }}>{r.pass2_total}</td>
                      <td className="px-3 py-1.5" style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", color: "#1B998B" }}>{r.pass2_succeeded}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
