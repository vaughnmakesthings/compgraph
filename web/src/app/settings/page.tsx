"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type {
  ScrapeRunSummary,
  EnrichmentRunSummary,
  ScrapeStatusResponse,
  EnrichStatusResponse,
  SchedulerStatusResponse,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TERMINAL_STATES = new Set(["success", "partial", "failed", "cancelled"]);

type HealthStatus = "idle" | "ok" | "error";

// --- Shared primitives ---

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
  variant?: "default" | "danger";
}

function OutlineButton({
  onClick,
  disabled = false,
  children,
  tooltip,
  variant = "default",
}: OutlineButtonProps) {
  const color = variant === "danger" ? "#8C2C23" : "#EF8354";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      style={{
        border: `1px solid ${color}`,
        color,
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
          (e.currentTarget as HTMLButtonElement).style.backgroundColor =
            variant === "danger" ? "rgba(140,44,35,0.08)" : "rgba(239,131,84,0.1)";
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

function SmallButton({
  onClick,
  disabled = false,
  children,
  variant = "default",
}: {
  onClick?: () => void;
  disabled?: boolean;
  children: React.ReactNode;
  variant?: "default" | "danger";
}) {
  const color = variant === "danger" ? "#8C2C23" : "#EF8354";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        border: `1px solid ${color}`,
        color,
        borderRadius: "4px",
        padding: "4px 10px",
        fontSize: "12px",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
        backgroundColor: "transparent",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "background-color 150ms",
        whiteSpace: "nowrap",
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor =
            variant === "danger" ? "rgba(140,44,35,0.08)" : "rgba(239,131,84,0.1)";
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

// Status badge for live run panels
const SCRAPE_BADGE: Record<string, { bg: string; color: string; label: string }> = {
  pending:   { bg: "#E8E8E4",     color: "#4F5D75", label: "Pending" },
  running:   { bg: "#DCB2561A",   color: "#DCB256", label: "Running" },
  paused:    { bg: "#EF83541A",   color: "#EF8354", label: "Paused" },
  stopping:  { bg: "#EF83541A",   color: "#EF8354", label: "Stopping" },
  success:   { bg: "#1B998B1A",   color: "#1B998B", label: "Success" },
  partial:   { bg: "#DCB2561A",   color: "#DCB256", label: "Partial" },
  failed:    { bg: "#8C2C231A",   color: "#8C2C23", label: "Failed" },
  cancelled: { bg: "#E8E8E4",     color: "#4F5D75", label: "Cancelled" },
};

function RunBadge({ status }: { status: string }) {
  const c = SCRAPE_BADGE[status] ?? { bg: "#E8E8E4", color: "#4F5D75", label: status };
  return (
    <span
      style={{
        backgroundColor: c.bg,
        color: c.color,
        borderRadius: "4px",
        padding: "2px 8px",
        fontSize: "12px",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
        fontWeight: 600,
        letterSpacing: "0.03em",
      }}
    >
      {c.label}
    </span>
  );
}

const COMPANY_STATE_LABEL: Record<string, string> = {
  pending:   "pending",
  running:   "running",
  completed: "done",
  failed:    "failed",
  skipped:   "skipped",
};

const COMPANY_STATE_COLOR: Record<string, string> = {
  pending:   "#4F5D75",
  running:   "#DCB256",
  completed: "#1B998B",
  failed:    "#8C2C23",
  skipped:   "#BFC0C0",
};

// --- Live scrape panel ---

function LiveScrapePanel({
  status,
  onControl,
  controlRunning,
}: {
  status: ScrapeStatusResponse;
  onControl: (action: "pause" | "resume" | "stop" | "force-stop") => void;
  controlRunning: boolean;
}) {
  const isActive = !TERMINAL_STATES.has(status.status);
  const canPause = status.status === "running";
  const canResume = status.status === "paused";
  const canStop = status.status === "running" || status.status === "paused";
  const canForce = status.status === "running" || status.status === "paused" || status.status === "stopping";

  return (
    <div
      className="mt-4 rounded"
      style={{ border: "1px solid #BFC0C0" }}
      role="region"
      aria-label="Active scrape run"
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2.5"
        style={{ borderBottom: "1px solid #BFC0C0", backgroundColor: "#F4F4F0", borderRadius: "6px 6px 0 0" }}
      >
        <span
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontWeight: 600,
            color: "#2D3142",
            fontSize: "13px",
          }}
        >
          Active Scrape Run
        </span>
        <div className="flex items-center gap-3">
          <span
            style={{
              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "11px",
              color: "#4F5D75",
            }}
          >
            {status.run_id.slice(0, 8)}
          </span>
          <RunBadge status={status.status} />
        </div>
      </div>

      {/* Stats grid */}
      <div
        className="grid grid-cols-5 divide-x divide-[#BFC0C0]"
        style={{ borderBottom: "1px solid #BFC0C0" }}
      >
        {[
          { label: "Postings", value: status.total_postings_found },
          { label: "Snapshots", value: status.total_snapshots_created },
          { label: "Errors", value: status.total_errors },
          { label: "Succeeded", value: status.companies_succeeded },
          { label: "Failed", value: status.companies_failed },
        ].map(({ label, value }) => (
          <div key={label} className="px-3 py-2" style={{ borderColor: "#BFC0C0" }}>
            <div
              style={{
                fontSize: "10px",
                color: "#4F5D75",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              }}
            >
              {label}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                fontSize: "18px",
                color: label === "Errors" && value > 0 ? "#8C2C23" : "#2D3142",
                fontWeight: 600,
              }}
            >
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Per-company table */}
      {Object.keys(status.company_states).length > 0 && (
        <div style={{ borderBottom: "1px solid #BFC0C0" }}>
          <table className="w-full text-xs">
            <thead>
              <tr style={{ backgroundColor: "#F9F9F7" }}>
                {["Company", "State", "Postings", "Snapshots"].map((col) => (
                  <th
                    key={col}
                    className="text-left px-3 py-1.5"
                    style={{
                      fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                      fontWeight: 600,
                      color: "#4F5D75",
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                      fontSize: "10px",
                    }}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(status.company_states).map(([slug, cs]) => (
                <tr key={slug} style={{ borderTop: "1px solid #E8E8E4" }}>
                  <td
                    className="px-3 py-1.5"
                    style={{
                      fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                      color: "#2D3142",
                    }}
                  >
                    {slug}
                  </td>
                  <td className="px-3 py-1.5">
                    <span
                      style={{
                        color: COMPANY_STATE_COLOR[cs.state] ?? "#4F5D75",
                        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                      }}
                    >
                      {COMPANY_STATE_LABEL[cs.state] ?? cs.state.toLowerCase()}
                    </span>
                  </td>
                  <td
                    className="px-3 py-1.5"
                    style={{
                      fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                      color: "#4F5D75",
                    }}
                  >
                    {cs.postings_found}
                  </td>
                  <td
                    className="px-3 py-1.5"
                    style={{
                      fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                      color: "#4F5D75",
                    }}
                  >
                    {cs.snapshots_created}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Control buttons (only when active) */}
      {isActive && (
        <div className="flex gap-2 px-4 py-3" style={{ borderRadius: "0 0 6px 6px" }}>
          {canPause && (
            <SmallButton onClick={() => onControl("pause")} disabled={controlRunning}>
              Pause
            </SmallButton>
          )}
          {canResume && (
            <SmallButton onClick={() => onControl("resume")} disabled={controlRunning}>
              Resume
            </SmallButton>
          )}
          {canStop && (
            <SmallButton onClick={() => onControl("stop")} disabled={controlRunning}>
              Stop
            </SmallButton>
          )}
          {canForce && (
            <SmallButton onClick={() => onControl("force-stop")} disabled={controlRunning} variant="danger">
              Force Stop
            </SmallButton>
          )}
        </div>
      )}
    </div>
  );
}

// --- Live enrichment panel ---

function LiveEnrichPanel({ status }: { status: EnrichStatusResponse }) {
  return (
    <div
      className="mt-4 rounded"
      style={{ border: "1px solid #BFC0C0" }}
      role="region"
      aria-label="Active enrichment run"
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2.5"
        style={{ borderBottom: "1px solid #BFC0C0", backgroundColor: "#F4F4F0", borderRadius: "6px 6px 0 0" }}
      >
        <span
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontWeight: 600,
            color: "#2D3142",
            fontSize: "13px",
          }}
        >
          Active Enrichment Run
        </span>
        <div className="flex items-center gap-3">
          <span
            style={{
              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "11px",
              color: "#4F5D75",
            }}
          >
            {status.run_id.slice(0, 8)}
          </span>
          <RunBadge status={status.status.toUpperCase()} />
        </div>
      </div>

      {/* Circuit breaker warning */}
      {status.circuit_breaker_tripped && (
        <div
          className="px-4 py-2"
          style={{
            backgroundColor: "#8C2C231A",
            borderBottom: "1px solid #8C2C2333",
            color: "#8C2C23",
            fontSize: "12px",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          }}
          role="alert"
        >
          Circuit breaker tripped — LLM API errors exceeded threshold
        </div>
      )}

      {/* Pass results */}
      <div
        className="grid grid-cols-2 divide-x"
        style={{ borderBottom: "1px solid #BFC0C0" }}
      >
        {[
          { label: "Pass 1 (Haiku)", result: status.pass1_result },
          { label: "Pass 2 (Sonnet)", result: status.pass2_result },
        ].map(({ label, result }) => (
          <div key={label} className="px-4 py-3" style={{ borderColor: "#BFC0C0" }}>
            <div
              style={{
                fontSize: "11px",
                color: "#4F5D75",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                marginBottom: "6px",
                fontWeight: 600,
              }}
            >
              {label}
            </div>
            <div className="flex gap-4">
              {[
                { k: "succeeded", v: result.succeeded, color: "#1B998B" },
                { k: "failed",    v: result.failed,    color: "#8C2C23" },
                { k: "skipped",   v: result.skipped,   color: "#4F5D75" },
              ].map(({ k, v, color }) => (
                <div key={k}>
                  <div style={{ fontSize: "10px", color: "#4F5D75", textTransform: "uppercase", letterSpacing: "0.04em" }}>{k}</div>
                  <div style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", fontSize: "16px", color, fontWeight: 600 }}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Token / API stats */}
      <div className="grid grid-cols-4 divide-x" style={{ borderColor: "#BFC0C0" }}>
        {[
          { label: "Input tokens",  value: status.total_input_tokens.toLocaleString() },
          { label: "Output tokens", value: status.total_output_tokens.toLocaleString() },
          { label: "API calls",     value: status.total_api_calls.toLocaleString() },
          { label: "Dedup saved",   value: status.total_dedup_saved.toLocaleString() },
        ].map(({ label, value }) => (
          <div key={label} className="px-3 py-2" style={{ borderColor: "#BFC0C0" }}>
            <div style={{ fontSize: "10px", color: "#4F5D75", textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}>
              {label}
            </div>
            <div style={{ fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)", fontSize: "14px", color: "#2D3142", fontWeight: 600 }}>
              {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Main page ---

export default function SettingsPage() {
  // Health check
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("idle");
  const [apiVersion, setApiVersion] = useState<string | null>(null);
  const [healthChecking, setHealthChecking] = useState(false);

  // Aggregation trigger
  const [aggStatus, setAggStatus] = useState<"idle" | "ok" | "error">("idle");
  const [aggMessage, setAggMessage] = useState<string | null>(null);
  const [aggRunning, setAggRunning] = useState(false);

  // Scrape trigger + live status
  const [scrapeActiveRunId, setScrapeActiveRunId] = useState<string | null>(null);
  const [scrapeStatus, setScrapeStatus] = useState<ScrapeStatusResponse | null>(null);
  const [scrapeTriggerRunning, setScrapeTriggerRunning] = useState(false);
  const [scrapeTriggerError, setScrapeTriggerError] = useState<string | null>(null);
  const [scrapeControlRunning, setScrapeControlRunning] = useState(false);

  // Enrichment trigger + live status
  const [enrichActiveRunId, setEnrichActiveRunId] = useState<string | null>(null);
  const [enrichStatus, setEnrichStatus] = useState<EnrichStatusResponse | null>(null);
  const [enrichTriggerRunning, setEnrichTriggerRunning] = useState(false);
  const [enrichTriggerError, setEnrichTriggerError] = useState<string | null>(null);

  // Scheduler
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatusResponse | null>(null);
  const [schedulerLoading, setSchedulerLoading] = useState(true);
  const [schedulerJobRunning, setSchedulerJobRunning] = useState<string | null>(null);

  // Run history
  const [scrapeRuns, setScrapeRuns] = useState<ScrapeRunSummary[]>([]);
  const [enrichRuns, setEnrichRuns] = useState<EnrichmentRunSummary[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);

  // Load run history on mount
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

  // Load scheduler status on mount
  useEffect(() => {
    let cancelled = false;
    void api.getSchedulerStatus().then((data) => {
      if (!cancelled) { setSchedulerStatus(data); setSchedulerLoading(false); }
    }).catch(() => {
      if (!cancelled) setSchedulerLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  // Poll scrape status while run is active
  useEffect(() => {
    if (!scrapeActiveRunId) return;
    let mounted = true;

    async function fetchScrapeStatus(id: ReturnType<typeof setInterval>) {
      try {
        const s = await api.getScrapeStatus();
        if (!mounted) return;
        setScrapeStatus(s);
        if (TERMINAL_STATES.has(s.status)) {
          clearInterval(id);
          setScrapeActiveRunId(null);
        }
      } catch { /* ignore — keep polling */ }
    }

    const intervalId = setInterval(() => void fetchScrapeStatus(intervalId), 3000);
    void fetchScrapeStatus(intervalId);
    return () => { mounted = false; clearInterval(intervalId); };
  }, [scrapeActiveRunId]);

  // Poll enrichment status while run is active
  useEffect(() => {
    if (!enrichActiveRunId) return;
    let mounted = true;

    async function fetchEnrichStatus(id: ReturnType<typeof setInterval>) {
      try {
        const s = await api.getEnrichStatus();
        if (!mounted) return;
        setEnrichStatus(s);
        if (TERMINAL_STATES.has(s.status)) {
          clearInterval(id);
          setEnrichActiveRunId(null);
        }
      } catch { /* ignore — keep polling */ }
    }

    const intervalId = setInterval(() => void fetchEnrichStatus(intervalId), 3000);
    void fetchEnrichStatus(intervalId);
    return () => { mounted = false; clearInterval(intervalId); };
  }, [enrichActiveRunId]);

  // Handlers
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

  async function handleTriggerScrape() {
    setScrapeTriggerRunning(true);
    setScrapeTriggerError(null);
    setScrapeStatus(null);
    try {
      const result = await api.triggerScrape();
      setScrapeActiveRunId(result.run_id);
    } catch (err) {
      setScrapeTriggerError(err instanceof Error ? err.message : "Failed to trigger scrape");
    } finally {
      setScrapeTriggerRunning(false);
    }
  }

  async function handleScrapeControl(action: "pause" | "resume" | "stop" | "force-stop") {
    setScrapeControlRunning(true);
    try {
      if (action === "pause") await api.pauseScrape();
      else if (action === "resume") await api.resumeScrape();
      else if (action === "stop") await api.stopScrape();
      else await api.forceStopScrape();
      // Immediate re-fetch to reflect the new state
      const s = await api.getScrapeStatus();
      setScrapeStatus(s);
      if (TERMINAL_STATES.has(s.status)) setScrapeActiveRunId(null);
    } catch { /* ignore */ } finally {
      setScrapeControlRunning(false);
    }
  }

  async function handleTriggerEnrichment() {
    setEnrichTriggerRunning(true);
    setEnrichTriggerError(null);
    setEnrichStatus(null);
    try {
      const result = await api.triggerEnrichment();
      setEnrichActiveRunId(result.run_id);
    } catch (err) {
      setEnrichTriggerError(err instanceof Error ? err.message : "Failed to trigger enrichment");
    } finally {
      setEnrichTriggerRunning(false);
    }
  }

  async function handleSchedulerJob(jobId: string, action: "trigger" | "pause" | "resume") {
    setSchedulerJobRunning(`${jobId}:${action}`);
    try {
      if (action === "trigger") await api.triggerSchedulerJob(jobId);
      else if (action === "pause") await api.pauseSchedulerJob(jobId);
      else await api.resumeSchedulerJob(jobId);
      const s = await api.getSchedulerStatus();
      setSchedulerStatus(s);
    } catch { /* ignore */ } finally {
      setSchedulerJobRunning(null);
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

      {/* API Health */}
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

      {/* Pipeline Controls */}
      <SectionCard title="Pipeline Controls" className="mt-4">
        <div className="flex flex-col gap-2">
          <OutlineButton
            onClick={() => void handleTriggerAggregation()}
            disabled={aggRunning}
          >
            {aggRunning ? "Running..." : "Trigger Aggregation"}
          </OutlineButton>
          <OutlineButton
            onClick={() => void handleTriggerScrape()}
            disabled={scrapeTriggerRunning || !!scrapeActiveRunId}
          >
            {scrapeTriggerRunning ? "Starting..." : scrapeActiveRunId ? "Scrape running…" : "Trigger Scrape"}
          </OutlineButton>
          <OutlineButton
            onClick={() => void handleTriggerEnrichment()}
            disabled={enrichTriggerRunning || !!enrichActiveRunId}
          >
            {enrichTriggerRunning ? "Starting..." : enrichActiveRunId ? "Enrichment running…" : "Trigger Enrichment"}
          </OutlineButton>
        </div>

        {/* Aggregation status */}
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

        {/* Scrape trigger error */}
        {scrapeTriggerError && (
          <div
            className="mt-3 rounded px-3 py-2 text-sm"
            style={{
              backgroundColor: "#8C2C231A",
              color: "#8C2C23",
              border: "1px solid #8C2C2333",
              borderRadius: "var(--radius-md, 6px)",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
            }}
            role="alert"
          >
            Scrape error: {scrapeTriggerError}
          </div>
        )}

        {/* Enrichment trigger error */}
        {enrichTriggerError && (
          <div
            className="mt-3 rounded px-3 py-2 text-sm"
            style={{
              backgroundColor: "#8C2C231A",
              color: "#8C2C23",
              border: "1px solid #8C2C2333",
              borderRadius: "var(--radius-md, 6px)",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
            }}
            role="alert"
          >
            Enrichment error: {enrichTriggerError}
          </div>
        )}

        {/* Live scrape status panel */}
        {scrapeStatus && (
          <LiveScrapePanel
            status={scrapeStatus}
            onControl={(action) => void handleScrapeControl(action)}
            controlRunning={scrapeControlRunning}
          />
        )}

        {/* Live enrichment status panel */}
        {enrichStatus && <LiveEnrichPanel status={enrichStatus} />}
      </SectionCard>

      {/* Scheduler */}
      <SectionCard title="Scheduler" className="mt-4">
        {schedulerLoading ? (
          <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: "13px", color: "#4F5D75" }}>
            Loading…
          </p>
        ) : !schedulerStatus ? (
          <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: "13px", color: "#4F5D75" }}>
            Could not load scheduler status.
          </p>
        ) : (
          <>
            {/* Header row */}
            <div className="flex items-center gap-3 mb-4">
              <span
                style={{
                  backgroundColor: schedulerStatus.enabled ? "#1B998B1A" : "#E8E8E4",
                  color: schedulerStatus.enabled ? "#1B998B" : "#4F5D75",
                  borderRadius: "4px",
                  padding: "2px 8px",
                  fontSize: "12px",
                  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontWeight: 600,
                }}
              >
                {schedulerStatus.enabled ? "Enabled" : "Disabled"}
              </span>
              {schedulerStatus.last_pipeline_finished_at && (
                <span
                  style={{
                    fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "12px",
                    color: "#4F5D75",
                  }}
                >
                  Last run:{" "}
                  <span
                    style={{
                      color: schedulerStatus.last_pipeline_success === true ? "#1B998B"
                           : schedulerStatus.last_pipeline_success === false ? "#8C2C23"
                           : "#4F5D75",
                      fontWeight: 500,
                    }}
                  >
                    {schedulerStatus.last_pipeline_success === true ? "Success"
                   : schedulerStatus.last_pipeline_success === false ? "Failed"
                   : "Unknown"}
                  </span>{" "}
                  {formatTs(schedulerStatus.last_pipeline_finished_at)}
                </span>
              )}
            </div>

            {/* Missed run warning */}
            {schedulerStatus.missed_run && (
              <div
                className="mb-4 px-3 py-2 rounded"
                style={{
                  backgroundColor: "#8C2C231A",
                  border: "1px solid #8C2C2333",
                  color: "#8C2C23",
                  fontSize: "13px",
                  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                }}
                role="alert"
              >
                No pipeline completed in the last 56 hours — scheduler may have failed.
              </div>
            )}

            {/* Schedules table */}
            {schedulerStatus.schedules.length === 0 ? (
              <p style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: "13px", color: "#4F5D75" }}>
                No schedules configured.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ borderBottom: "1px solid #BFC0C0", backgroundColor: "#F4F4F0" }}>
                      {["Schedule", "Status", "Next Run", "Last Run", "Actions"].map((col) => (
                        <th
                          key={col}
                          className="text-left px-3 py-2"
                          style={{
                            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                            fontWeight: 600,
                            color: "#4F5D75",
                            textTransform: "uppercase",
                            letterSpacing: "0.04em",
                          }}
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {schedulerStatus.schedules.map((sched) => {
                      const isRunning = schedulerJobRunning?.startsWith(sched.schedule_id + ":");
                      return (
                        <tr key={sched.schedule_id} style={{ borderBottom: "1px solid #E8E8E4" }}>
                          <td
                            className="px-3 py-2"
                            style={{
                              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                              color: "#2D3142",
                            }}
                          >
                            {sched.schedule_id}
                          </td>
                          <td className="px-3 py-2">
                            <span
                              style={{
                                backgroundColor: sched.paused ? "#EF83541A" : "#1B998B1A",
                                color: sched.paused ? "#EF8354" : "#1B998B",
                                borderRadius: "4px",
                                padding: "1px 6px",
                                fontSize: "11px",
                                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontWeight: 600,
                              }}
                            >
                              {sched.paused ? "Paused" : "Scheduled"}
                            </span>
                          </td>
                          <td
                            className="px-3 py-2"
                            style={{
                              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                              color: "#4F5D75",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {formatTs(sched.next_fire_time)}
                          </td>
                          <td
                            className="px-3 py-2"
                            style={{
                              fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                              color: "#4F5D75",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {formatTs(sched.last_fire_time)}
                          </td>
                          <td className="px-3 py-2">
                            <div className="flex gap-1.5">
                              <SmallButton
                                onClick={() => void handleSchedulerJob(sched.schedule_id, "trigger")}
                                disabled={!!isRunning}
                              >
                                Trigger
                              </SmallButton>
                              {sched.paused ? (
                                <SmallButton
                                  onClick={() => void handleSchedulerJob(sched.schedule_id, "resume")}
                                  disabled={!!isRunning}
                                >
                                  Resume
                                </SmallButton>
                              ) : (
                                <SmallButton
                                  onClick={() => void handleSchedulerJob(sched.schedule_id, "pause")}
                                  disabled={!!isRunning}
                                >
                                  Pause
                                </SmallButton>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </SectionCard>

      {/* System Info */}
      <SectionCard title="System Info" className="mt-4">
        <div>
          <KvRow label="API Version" value={apiVersion ?? "—"} />
          <KvRow label="Database" value="Supabase Postgres 17" />
          <KvRow label="Platform" value="Digital Ocean" />
        </div>
      </SectionCard>

      {/* Scrape Run History */}
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

      {/* Enrichment Run History */}
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
