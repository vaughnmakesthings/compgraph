"use client";

import { useState, useMemo } from "react";
import { redirect } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { UserManagementSection } from "@/components/auth/user-management-section";
import {
  triggerAggregationApiV1AggregationTriggerPostMutation,
  triggerScrapeApiV1ScrapeTriggerPostMutation,
  triggerFullApiV1EnrichTriggerPostMutation,
  schedulerStatusApiV1SchedulerStatusGetOptions,
  pipelineRunsApiV1PipelineRunsGetOptions,
  scrapeStatusApiV1ScrapeStatusGetOptions,
  scrapeStatusApiV1ScrapeStatusGetQueryKey,
  enrichStatusApiV1EnrichStatusGetOptions,
  schedulerStatusApiV1SchedulerStatusGetQueryKey,
} from "@/api-client/@tanstack/react-query.gen";
import {
  pauseScrapeApiV1ScrapePausePost,
  resumeScrapeApiV1ScrapeResumePost,
  stopScrapeApiV1ScrapeStopPost,
  forceStopScrapeApiV1ScrapeForceStopPost,
  triggerJobApiV1SchedulerJobsJobIdTriggerPost,
  pauseJobApiV1SchedulerJobsJobIdPausePost,
  resumeJobApiV1SchedulerJobsJobIdResumePost,
} from "@/api-client/sdk.gen";
import type {
  ScrapeStatusResponse,
  EnrichStatusResponse,
  SchedulerStatusResponse,
  PipelineRunsResponse,
  ScrapeRunSummary,
  EnrichmentRunSummary,
} from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { SectionCard } from "@/components/ui/section-card";
import { formatTimestamp, formatDuration } from "@/lib/utils";

const TERMINAL_STATES = new Set(["success", "partial", "failed", "cancelled"]);
const STALE_THRESHOLD_MS = 24 * 60 * 60 * 1000; // 24 hours
const PAGE_SIZE = 10;

// --- Shared primitives ---

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
  const color = variant === "danger" ? "border-[#8C2C23] text-[#8C2C23] hover:bg-[#8C2C230D]" : "border-[#EF8354] text-[#EF8354] hover:bg-[#EF83541A]";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      className={`rounded-md px-4 py-2 text-sm font-body transition-colors border bg-transparent disabled:opacity-50 disabled:cursor-not-allowed ${color}`}
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
  const color = variant === "danger" ? "border-[#8C2C23] text-[#8C2C23] hover:bg-[#8C2C230D]" : "border-[#EF8354] text-[#EF8354] hover:bg-[#EF83541A]";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded px-2.5 py-1 text-xs font-body transition-colors border bg-transparent disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap ${color}`}
    >
      {children}
    </button>
  );
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "completed" || status === "success" ? "bg-[#1B998B]"
    : status === "running" ? "bg-[#DCB256]"
    : status === "failed" ? "bg-[#8C2C23]"
    : "bg-[#BFC0C0]";
  return <span className={`inline-block size-[7px] rounded-full mr-1.5 align-middle ${color}`} aria-hidden="true" />;
}

const SCRAPE_BADGE: Record<string, { bg: string; color: string; label: string }> = {
  pending:   { bg: "bg-[#E8E8E4]",     color: "text-[#4F5D75]", label: "Pending" },
  running:   { bg: "bg-[#DCB2561A]",   color: "text-[#DCB256]", label: "Running" },
  paused:    { bg: "bg-[#EF83541A]",   color: "text-[#EF8354]", label: "Paused" },
  stopping:  { bg: "bg-[#EF83541A]",   color: "text-[#EF8354]", label: "Stopping" },
  success:   { bg: "bg-[#1B998B1A]",   color: "text-[#1B998B]", label: "Success" },
  partial:   { bg: "bg-[#DCB2561A]",   color: "text-[#DCB256]", label: "Partial" },
  failed:    { bg: "bg-[#8C2C231A]",   color: "text-[#8C2C23]", label: "Failed" },
  cancelled: { bg: "bg-[#E8E8E4]",     color: "text-[#4F5D75]", label: "Cancelled" },
  stale:     { bg: "bg-[#DCB2561A]",   color: "text-[#DCB256]", label: "Stale" },
};

function RunBadge({ status }: { status: string }) {
  const c = SCRAPE_BADGE[status] ?? { bg: "bg-[#E8E8E4]", color: "text-[#4F5D75]", label: status };
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-body font-semibold tracking-wide ${c.bg} ${c.color}`}>
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
  pending:   "text-[#4F5D75]",
  running:   "text-[#DCB256]",
  completed: "text-[#1B998B]",
  failed:    "text-[#8C2C23]",
  skipped:   "text-[#BFC0C0]",
};

function isStaleRun(status: string, startedAt: string | null): boolean {
  if (status !== "running" || !startedAt) return false;
  return Date.now() - new Date(startedAt).getTime() > STALE_THRESHOLD_MS;
}

// --- Pagination ---

function PaginationControls({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#E8E8E4]">
      <span className="font-body text-xs text-[#4F5D75]">
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-2">
        <SmallButton onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
          Previous
        </SmallButton>
        <SmallButton onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>
          Next
        </SmallButton>
      </div>
    </div>
  );
}

// --- Panels ---

function LiveScrapePanel({
  status,
  onControl,
  controlRunning,
  companyNames,
}: {
  status: ScrapeStatusResponse;
  onControl: (action: string) => void;
  controlRunning: boolean;
  companyNames: Record<string, string>;
}) {
  const isActive = !TERMINAL_STATES.has(status.status);
  const canPause = status.status === "running";
  const canResume = status.status === "paused";
  const canStop = status.status === "running" || status.status === "paused";
  const canForce = status.status === "running" || status.status === "paused" || status.status === "stopping";

  return (
    <div className="mt-4 rounded border border-[#BFC0C0] bg-white overflow-hidden" role="region" aria-label="Active scrape run">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#BFC0C0] bg-[#F4F4F0]">
        <span className="font-body font-semibold text-[#2D3142] text-[13px]">Active Scrape Run</span>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-[#4F5D75]">{status.run_id.slice(0, 8)}</span>
          <RunBadge status={status.status} />
        </div>
      </div>

      <div className="grid grid-cols-4 divide-x divide-[#BFC0C0] border-b border-[#BFC0C0]">
        {[
          { label: "Postings", value: status.total_postings_found },
          { label: "Errors", value: status.total_errors },
          { label: "Succeeded", value: status.companies_succeeded },
          { label: "Failed", value: status.companies_failed },
        ].map(({ label, value }) => (
          <div key={label} className="px-3 py-2">
            <div className="text-[10px] text-[#4F5D75] uppercase tracking-widest font-body">{label}</div>
            <div className={`font-mono text-lg font-semibold ${label === "Errors" && value > 0 ? 'text-[#8C2C23]' : 'text-[#2D3142]'}`}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {Object.keys(status.company_states).length > 0 && (
        <div className="border-b border-[#BFC0C0]">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-[#FAFAF7]">
                {["Company", "State", "Postings"].map((col) => (
                  <th key={col} className="text-left px-3 py-1.5 font-body font-semibold text-[#4F5D75] uppercase tracking-wider text-[10px]">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E8E4]">
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {Object.entries(status.company_states).map(([slug, cs]: [string, any]) => (
                <tr key={slug}>
                  <td className="px-3 py-1.5 font-body text-[#2D3142]">{companyNames[slug] ?? slug}</td>
                  <td className={`px-3 py-1.5 font-body ${COMPANY_STATE_COLOR[cs] ?? 'text-[#4F5D75]'}`}>
                    {COMPANY_STATE_LABEL[cs] ?? cs}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-[#4F5D75]">
                    {status.company_results[slug]?.postings_found ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {isActive && (
        <div className="flex gap-2 px-4 py-3">
          {canPause && <SmallButton onClick={() => onControl("pause")} disabled={controlRunning}>Pause</SmallButton>}
          {canResume && <SmallButton onClick={() => onControl("resume")} disabled={controlRunning}>Resume</SmallButton>}
          {canStop && <SmallButton onClick={() => onControl("stop")} disabled={controlRunning}>Stop</SmallButton>}
          {canForce && <SmallButton onClick={() => onControl("force-stop")} disabled={controlRunning} variant="danger">Force Stop</SmallButton>}
        </div>
      )}
    </div>
  );
}

function LiveEnrichPanel({ status }: { status: EnrichStatusResponse }) {
  return (
    <div className="mt-4 rounded border border-[#BFC0C0] bg-white overflow-hidden" role="region" aria-label="Active enrichment run">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#BFC0C0] bg-[#F4F4F0]">
        <span className="font-body font-semibold text-[#2D3142] text-[13px]">Active Enrichment Run</span>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] text-[#4F5D75]">{status.run_id.slice(0, 8)}</span>
          <RunBadge status={status.status} />
        </div>
      </div>

      {status.circuit_breaker_tripped && (
        <div className="px-4 py-2 bg-[#8C2C231A] border-b border-[#8C2C2333] text-[#8C2C23] text-xs font-body" role="alert">
          Circuit breaker tripped — LLM API errors exceeded threshold
        </div>
      )}

      <div className="grid grid-cols-2 divide-x divide-[#BFC0C0] border-b border-[#BFC0C0]">
        {[
          { label: "Pass 1 (Haiku)", result: status.pass1_result },
          { label: "Pass 2 (Sonnet)", result: status.pass2_result },
        ].map(({ label, result }) => (
          <div key={label} className="px-4 py-3">
            <div className="text-[11px] font-semibold text-[#4F5D75] font-body mb-1.5 uppercase tracking-wide">{label}</div>
            {result == null ? (
              <div className="text-xs text-[#4F5D75] font-body">Not started</div>
            ) : (
              <div className="flex gap-4">
                {[
                  { k: "succeeded", v: result.succeeded, color: "text-[#1B998B]" },
                  { k: "failed",    v: result.failed,    color: "text-[#8C2C23]" },
                  { k: "skipped",   v: result.skipped,   color: "text-[#4F5D75]" },
                ].map(({ k, v, color }) => (
                  <div key={k}>
                    <div className="text-[10px] text-[#4F5D75] uppercase tracking-wider">{k}</div>
                    <div className={`font-mono text-lg font-semibold ${color}`}>{v}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-4 divide-x divide-[#BFC0C0]">
        {[
          { label: "Input tokens",  value: (status.total_input_tokens ?? 0).toLocaleString() },
          { label: "Output tokens", value: (status.total_output_tokens ?? 0).toLocaleString() },
          { label: "API calls",     value: (status.total_api_calls ?? 0).toLocaleString() },
          { label: "Dedup saved",   value: (status.total_dedup_saved ?? 0).toLocaleString() },
        ].map(({ label, value }) => (
          <div key={label} className="px-3 py-2">
            <div className="text-[10px] text-[#4F5D75] uppercase tracking-wider font-body">{label}</div>
            <div className="font-mono text-[14px] text-[#2D3142] font-semibold">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Error Row ---

function ErrorRow({ message }: { message: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = message.length > 60;

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="text-left text-[11px] font-body text-[#8C2C23] hover:underline underline-offset-2"
      >
        {isLong && !expanded ? `${message.slice(0, 60)}...` : message}
      </button>
    </div>
  );
}

// --- Run History Tables ---

function ScrapeRunHistoryTable({ runs, total }: { runs: ScrapeRunSummary[]; total: number }) {
  const [page, setPage] = useState(1);
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const pagedRuns = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return runs.slice(start, start + PAGE_SIZE);
  }, [runs, page]);

  if (runs.length === 0) {
    return <p className="text-[13px] text-[#4F5D75] font-body">No runs recorded.</p>;
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#BFC0C0]">
              {["Company", "Status", "Started", "Duration", "Found", "Created", "Closed"].map((col) => (
                <th key={col} className="text-left px-3 py-2 font-body font-semibold text-[#4F5D75]/50 uppercase tracking-widest text-[10px]">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E8E8E4]">
            {pagedRuns.map((r) => {
              const dur = r.completed_at && r.started_at ? formatDuration(Math.round((new Date(r.completed_at).getTime() - new Date(r.started_at).getTime()) / 1000)) : "\u2014";
              const stale = isStaleRun(r.status, r.started_at);
              const displayStatus = stale ? "stale" : r.status;
              return (
                <tr key={r.id}>
                  <td className="px-3 py-1.5 font-body text-[#2D3142]">
                    {r.company_name}
                    {r.status === "failed" && r.error_message && (
                      <ErrorRow message={r.error_message} />
                    )}
                  </td>
                  <td className="px-3 py-1.5 text-[#4F5D75] font-body">
                    <div className="flex items-center">
                      <StatusDot status={r.status} />
                      <RunBadge status={displayStatus} />
                    </div>
                  </td>
                  <td className="px-3 py-1.5 font-mono text-[#4F5D75] whitespace-nowrap">{formatTimestamp(r.started_at)}</td>
                  <td className="px-3 py-1.5 font-mono text-[#4F5D75]">{dur}</td>
                  <td className="px-3 py-1.5 font-mono text-[#2D3142]">{r.jobs_found}</td>
                  <td className="px-3 py-1.5 font-mono text-[#2D3142]">{r.snapshots_created}</td>
                  <td className="px-3 py-1.5 font-mono text-[#2D3142]">{r.postings_closed}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
    </>
  );
}

function EnrichRunHistoryTable({ runs, total }: { runs: EnrichmentRunSummary[]; total: number }) {
  const [page, setPage] = useState(1);
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const pagedRuns = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return runs.slice(start, start + PAGE_SIZE);
  }, [runs, page]);

  if (runs.length === 0) {
    return <p className="text-[13px] text-[#4F5D75] font-body">No runs recorded.</p>;
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#BFC0C0]">
              {["Status", "Started", "Duration", "P1 Total", "P1 OK", "P2 Total", "P2 OK"].map((col) => (
                <th key={col} className="text-left px-3 py-2 font-body font-semibold text-[#4F5D75]/50 uppercase tracking-widest text-[10px]">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E8E8E4]">
            {pagedRuns.map((r) => {
              const dur = r.finished_at && r.started_at ? formatDuration(Math.round((new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()) / 1000)) : "\u2014";
              const stale = isStaleRun(r.status, r.started_at);
              const displayStatus = stale ? "stale" : r.status;
              return (
                <tr key={r.id}>
                  <td className="px-3 py-1.5 text-[#4F5D75] font-body">
                    <div className="flex items-center">
                      <StatusDot status={r.status} />
                      <RunBadge status={displayStatus} />
                    </div>
                    {r.status === "failed" && r.error_summary && (
                      <ErrorRow message={r.error_summary} />
                    )}
                    {stale && (
                      <span className="text-[10px] text-[#DCB256] font-body mt-0.5 block">Started {formatTimestamp(r.started_at)} — likely abandoned</span>
                    )}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-[#4F5D75] whitespace-nowrap">{formatTimestamp(r.started_at)}</td>
                  <td className="px-3 py-1.5 font-mono text-[#4F5D75]">{dur}</td>
                  <td className="px-3 py-1.5 font-mono text-[#2D3142]">{r.pass1_total}</td>
                  <td className="px-3 py-1.5 font-mono text-[#1B998B] font-semibold">{r.pass1_succeeded}</td>
                  <td className="px-3 py-1.5 font-mono text-[#2D3142]">{r.pass2_total}</td>
                  <td className="px-3 py-1.5 font-mono text-[#1B998B] font-semibold">{r.pass2_succeeded}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <PaginationControls page={page} totalPages={totalPages} onPageChange={setPage} />
    </>
  );
}

// --- Main Page Content ---

function is409Error(error: Error): boolean {
  return error.message.includes("409") || error.message.includes("already running") || error.message.includes("already active");
}

function SettingsPageContent() {
  const queryClient = useQueryClient();

  // Queries
  const { data: runsRes, isLoading: runsLoading } = useQuery({
    ...pipelineRunsApiV1PipelineRunsGetOptions(),
    select: (data) => data as unknown as PipelineRunsResponse,
  });

  const { data: schedulerStatus, isLoading: schedulerLoading } = useQuery({
    ...schedulerStatusApiV1SchedulerStatusGetOptions(),
    select: (data) => data as unknown as SchedulerStatusResponse,
  });

  const { data: scrapeStatus } = useQuery({
    ...scrapeStatusApiV1ScrapeStatusGetOptions(),
    refetchInterval: (query) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const status = (query.state.data as any)?.status;
      return (status && !TERMINAL_STATES.has(status)) ? 3000 : false;
    },
    select: (data) => data as unknown as ScrapeStatusResponse,
  });

  const { data: enrichStatus } = useQuery({
    ...enrichStatusApiV1EnrichStatusGetOptions(),
    refetchInterval: (query) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const status = (query.state.data as any)?.status;
      return (status && !TERMINAL_STATES.has(status)) ? 3000 : false;
    },
    select: (data) => data as unknown as EnrichStatusResponse,
  });

  // Mutations
  const aggMutation = useMutation(triggerAggregationApiV1AggregationTriggerPostMutation());

  const scrapeTriggerMutation = useMutation({
    ...triggerScrapeApiV1ScrapeTriggerPostMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scrapeStatusApiV1ScrapeStatusGetQueryKey() });
    },
  });

  const enrichTriggerMutation = useMutation(triggerFullApiV1EnrichTriggerPostMutation());

  const scrapeControlMutation = useMutation({
    mutationFn: async (action: string) => {
      if (action === "pause") return pauseScrapeApiV1ScrapePausePost();
      if (action === "resume") return resumeScrapeApiV1ScrapeResumePost();
      if (action === "stop") return stopScrapeApiV1ScrapeStopPost();
      if (action === "force-stop") return forceStopScrapeApiV1ScrapeForceStopPost();
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: scrapeStatusApiV1ScrapeStatusGetQueryKey() }),
  });

  const schedulerMutation = useMutation({
    mutationFn: async ({ jobId, action }: { jobId: string; action: string }) => {
      const path = { job_id: jobId };
      if (action === "trigger") return triggerJobApiV1SchedulerJobsJobIdTriggerPost({ path });
      if (action === "pause") return pauseJobApiV1SchedulerJobsJobIdPausePost({ path });
      if (action === "resume") return resumeJobApiV1SchedulerJobsJobIdResumePost({ path });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: schedulerStatusApiV1SchedulerStatusGetQueryKey() }),
  });

  // Derived state
  const scrapeRuns = runsRes?.scrape_runs ?? [];
  const enrichRuns = runsRes?.enrichment_runs ?? [];
  const scrapeTotal = runsRes?.scrape_total ?? scrapeRuns.length;
  const enrichTotal = runsRes?.enrichment_total ?? enrichRuns.length;
  const scrapeIsActive = scrapeStatus && !TERMINAL_STATES.has(scrapeStatus.status);
  const enrichIsActive = enrichStatus && !TERMINAL_STATES.has(enrichStatus.status);

  // Build slug->display name map from run history
  const companyNames: Record<string, string> = {};
  for (const r of scrapeRuns) {
    if (r.company_slug && r.company_name) companyNames[r.company_slug] = r.company_name;
  }

  // Confirm states
  const [confirmAggOpen, setConfirmAggOpen] = useState(false);
  const [confirmScrapeOpen, setConfirmScrapeOpen] = useState(false);
  const [confirmEnrichOpen, setConfirmEnrichOpen] = useState(false);
  const [confirmScrapeControlOpen, setConfirmScrapeControlOpen] = useState(false);
  const [confirmScrapeAction, setConfirmScrapeAction] = useState<"stop" | "force-stop">("stop");
  const [confirmSchedulerOpen, setConfirmSchedulerOpen] = useState(false);
  const [confirmSchedulerJobId, setConfirmSchedulerJobId] = useState<string | null>(null);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight font-display text-[#2D3142]">Settings</h1>
        <p className="mt-1 text-sm font-body text-muted-foreground">Pipeline controls, scheduler status, and system configuration</p>
      </div>

      <SectionCard title="Pipeline Controls" className="p-5" headingClassName="text-base">
        <div className="flex flex-row flex-wrap gap-3">
          <OutlineButton onClick={() => setConfirmAggOpen(true)} disabled={aggMutation.isPending}>
            {aggMutation.isPending ? "Running..." : "Trigger Aggregation"}
          </OutlineButton>
          <OutlineButton onClick={() => setConfirmScrapeOpen(true)} disabled={scrapeTriggerMutation.isPending || scrapeIsActive}>
            {scrapeTriggerMutation.isPending ? "Starting..." : scrapeIsActive ? "Scrape running\u2026" : "Trigger Scrape"}
          </OutlineButton>
          <OutlineButton onClick={() => setConfirmEnrichOpen(true)} disabled={enrichTriggerMutation.isPending || enrichIsActive}>
            {enrichTriggerMutation.isPending ? "Starting..." : enrichIsActive ? "Enrichment running\u2026" : "Trigger Enrichment"}
          </OutlineButton>
        </div>

        {aggMutation.isSuccess && (
          <div className="mt-3 rounded border border-[#1B998B33] px-3 py-2 text-[13px] bg-[#1B998B1A] text-[#1B998B] font-body">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            Success: {(aggMutation.data as any)?.message || 'Started'}
          </div>
        )}
        {aggMutation.isError && (
          <div className="mt-3 rounded border border-[#8C2C2333] px-3 py-2 text-[13px] bg-[#8C2C231A] text-[#8C2C23] font-body">
            Error: {aggMutation.error.message || 'Failed'}
          </div>
        )}

        {scrapeTriggerMutation.isError && (
          <div className="mt-3 rounded border border-[#DCB25633] px-3 py-2 text-[13px] bg-[#DCB2561A] text-[#2D3142] font-body" role="alert">
            {is409Error(scrapeTriggerMutation.error)
              ? "A scrape pipeline is already running. Wait for it to complete or force-stop it first."
              : `Scrape error: ${scrapeTriggerMutation.error.message}`}
          </div>
        )}

        {enrichTriggerMutation.isError && (
          <div className="mt-3 rounded border border-[#8C2C2333] px-3 py-2 text-[13px] bg-[#8C2C231A] text-[#8C2C23] font-body">
            Enrichment error: {enrichTriggerMutation.error.message}
          </div>
        )}

        {scrapeStatus && <LiveScrapePanel status={scrapeStatus} companyNames={companyNames} onControl={(a) => {
          if (a === "stop" || a === "force-stop") { setConfirmScrapeAction(a); setConfirmScrapeControlOpen(true); }
          else scrapeControlMutation.mutate(a);
        }} controlRunning={scrapeControlMutation.isPending} />}

        {enrichStatus && <LiveEnrichPanel status={enrichStatus} />}
      </SectionCard>

      <SectionCard title="Scheduler" className="mt-4 p-5" headingClassName="text-base">
        {schedulerLoading ? <p className="text-[13px] text-[#4F5D75] font-body">Loading\u2026</p> : !schedulerStatus ? <p className="text-[13px] text-[#4F5D75] font-body">Error loading scheduler.</p> : (
          <>
            <div className="flex items-center gap-3 mb-4">
              <span className={`rounded px-2 py-0.5 text-xs font-body font-semibold ${schedulerStatus.enabled ? 'bg-[#1B998B1A] text-[#1B998B]' : 'bg-[#E8E8E4] text-[#4F5D75]'}`}>
                {schedulerStatus.enabled ? "Enabled" : "Disabled"}
              </span>
              {schedulerStatus.last_pipeline_finished_at && (
                <span className="font-body text-xs text-[#4F5D75]">
                  Last run: <span className={`font-medium ${schedulerStatus.last_pipeline_success === true ? 'text-[#1B998B]' : schedulerStatus.last_pipeline_success === false ? 'text-[#8C2C23]' : 'text-[#4F5D75]'}`}>{schedulerStatus.last_pipeline_success === true ? 'Success' : schedulerStatus.last_pipeline_success === false ? 'Failed' : '\u2014'}</span> {formatTimestamp(schedulerStatus.last_pipeline_finished_at)}
                </span>
              )}
            </div>

            {schedulerStatus.last_pipeline_success === false && schedulerStatus.last_pipeline_error && (
              <div className="mb-4 px-3 py-2 rounded bg-[#8C2C231A] border border-[#8C2C2333] text-[#8C2C23] text-[13px] font-body">
                {schedulerStatus.last_pipeline_error}
              </div>
            )}

            {schedulerStatus.missed_run && (
              <div className="mb-4 px-3 py-2 rounded bg-[#8C2C231A] border border-[#8C2C2333] text-[#8C2C23] text-[13px] font-body">
                No pipeline completed in the last 80 hours — scheduler may have failed.
              </div>
            )}

            {schedulerStatus.schedules.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#BFC0C0]">
                      {["Schedule", "Status", "Next Run", "Last Run", "Actions"].map((col) => (
                        <th key={col} className="text-left px-3 py-2 font-body font-semibold text-[#4F5D75]/50 uppercase tracking-widest text-[10px]">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E8E8E4]">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {schedulerStatus.schedules.map((sched: any) => (
                      <tr key={sched.schedule_id}>
                        <td className="px-3 py-2 font-mono text-[#2D3142]">{sched.schedule_id}</td>
                        <td className="px-3 py-2 font-body font-semibold text-[11px]">
                          <span className={`rounded px-1.5 py-0.5 ${sched.paused ? 'bg-[#EF83541A] text-[#EF8354]' : 'bg-[#1B998B1A] text-[#1B998B]'}`}>
                            {sched.paused ? "Paused" : "Scheduled"}
                          </span>
                        </td>
                        <td className="px-3 py-2 font-mono text-[#4F5D75] whitespace-nowrap">{formatTimestamp(sched.next_fire_time)}</td>
                        <td className="px-3 py-2 font-mono text-[#4F5D75] whitespace-nowrap">{formatTimestamp(sched.last_fire_time)}</td>
                        <td className="px-3 py-2">
                          <div className="flex gap-1.5">
                            <SmallButton onClick={() => { setConfirmSchedulerJobId(sched.schedule_id); setConfirmSchedulerOpen(true); }} disabled={schedulerMutation.isPending}>Trigger</SmallButton>
                            <SmallButton onClick={() => schedulerMutation.mutate({ jobId: sched.schedule_id, action: sched.paused ? "resume" : "pause" })} disabled={schedulerMutation.isPending}>
                              {sched.paused ? "Resume" : "Pause"}
                            </SmallButton>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="text-[13px] text-[#4F5D75] font-body">No schedules configured.</p>}
          </>
        )}
      </SectionCard>

      <div className="mt-4"><UserManagementSection /></div>

      <SectionCard title="Scrape Run History" className="mt-4 p-5" headingClassName="text-base">
        {runsLoading
          ? <p className="text-[13px] text-[#4F5D75] font-body">Loading\u2026</p>
          : <ScrapeRunHistoryTable runs={scrapeRuns} total={scrapeTotal} />
        }
      </SectionCard>

      <SectionCard title="Enrichment Run History" className="mt-4 p-5" headingClassName="text-base">
        {runsLoading
          ? <p className="text-[13px] text-[#4F5D75] font-body">Loading\u2026</p>
          : <EnrichRunHistoryTable runs={enrichRuns} total={enrichTotal} />
        }
      </SectionCard>

      <div className="mt-4 mb-8 px-4 py-2 rounded bg-[#F4F4F0] border border-[#E8E8E4]">
        <span className="font-body text-xs text-[#4F5D75]">
          CompGraph v1.0 — Supabase Postgres 17 — Digital Ocean
        </span>
      </div>

      <ConfirmDialog open={confirmAggOpen} onOpenChange={setConfirmAggOpen} title="Trigger Aggregation" description="Truncate and rebuild all 4 aggregation tables. Existing data will be overwritten." confirmLabel="Confirm" confirmVariant="danger" onConfirm={async () => { await aggMutation.mutateAsync({}); }} />
      <ConfirmDialog open={confirmScrapeOpen} onOpenChange={setConfirmScrapeOpen} title="Trigger Scrape" description="Start a full scrape across all 5 competitor platforms. Takes 5-10 minutes." confirmLabel="Confirm" onConfirm={async () => { await scrapeTriggerMutation.mutateAsync({}); }} />
      <ConfirmDialog open={confirmEnrichOpen} onOpenChange={setConfirmEnrichOpen} title="Trigger Enrichment" description="Run the LLM enrichment pipeline. Anthropic API calls will be made." confirmLabel="Confirm" onConfirm={async () => { await enrichTriggerMutation.mutateAsync({}); }} />
      <ConfirmDialog open={confirmScrapeControlOpen} onOpenChange={setConfirmScrapeControlOpen} title={confirmScrapeAction === "force-stop" ? "Force-Stop Scrape" : "Stop Scrape"} description={confirmScrapeAction === "force-stop" ? "Immediately kill the active run. In-progress company scrapes will be abandoned." : "Request a graceful stop. In-progress scrapes will complete first."} confirmLabel="Confirm" confirmVariant={confirmScrapeAction === "force-stop" ? "danger" : "default"} onConfirm={async () => { await scrapeControlMutation.mutateAsync(confirmScrapeAction); }} />
      <ConfirmDialog open={confirmSchedulerOpen} onOpenChange={(open) => { setConfirmSchedulerOpen(open); if (!open) setConfirmSchedulerJobId(null); }} title="Trigger Scheduler Job" description="Manually trigger this scheduled job outside its normal schedule." confirmLabel="Confirm" onConfirm={async () => { if (confirmSchedulerJobId) await schedulerMutation.mutateAsync({ jobId: confirmSchedulerJobId, action: "trigger" }); }} />
    </div>
  );
}

export default function SettingsPage() {
  const { role, loading } = useAuth();
  if (loading) return null;
  if (role !== "admin") redirect("/403");
  return <SettingsPageContent />;
}
