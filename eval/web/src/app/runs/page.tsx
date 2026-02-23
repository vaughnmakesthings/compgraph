"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { AppShell } from "@/components/app-shell";
import { DataTable, type Column } from "@/components/data-table";
import { StatusBadge } from "@/components/status-badge";
import {
  getRuns,
  getModels,
  getPrompts,
  createRun,
  getProgress,
  type Run,
  type RunProgress,
} from "@/lib/api-client";
import { ErrorBox } from "@/components/error-box";
import { LoadingCard } from "@/components/loading-card";

function formatCost(cost: number | null): string {
  if (cost === null) return "\u2014";
  return `$${cost.toFixed(3)}`;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "\u2014";
  return `${Math.round(ms / 1000)}s`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function deriveStatus(run: Run): string {
  if (run.total_duration_ms !== null) {
    return "completed";
  }
  return "running";
}

const columns: Column<Run>[] = [
  {
    key: "id",
    label: "#",
    mono: true,
    width: "w-12",
  },
  {
    key: "model",
    label: "Model / Prompt",
    render: (row) => (
      <span>
        <span className="font-medium text-foreground">{row.model}</span>
        <span className="text-muted-foreground">/{row.prompt_version}</span>
      </span>
    ),
  },
  {
    key: "pass_number",
    label: "Pass",
  },
  {
    key: "status",
    label: "Status",
    render: (row) => <StatusBadge status={deriveStatus(row)} />,
  },
  {
    key: "total_cost_usd",
    label: "Cost",
    align: "right",
    mono: true,
    render: (row) => <span>{formatCost(row.total_cost_usd)}</span>,
  },
  {
    key: "total_duration_ms",
    label: "Duration",
    align: "right",
    mono: true,
    render: (row) => <span>{formatDuration(row.total_duration_ms)}</span>,
  },
  {
    key: "created_at",
    label: "Date",
    align: "right",
    render: (row) => <span>{formatDate(row.created_at)}</span>,
  },
];

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Run form state
  const [showForm, setShowForm] = useState(false);
  const [passNumber, setPassNumber] = useState<number>(1);
  const [models, setModels] = useState<Record<string, string>>({});
  const [prompts, setPrompts] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [concurrency, setConcurrency] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmStep, setConfirmStep] = useState(false);

  // Progress tracking
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [trackingId, setTrackingId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      const data = await getRuns();
      setRuns(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch runs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  // Fetch models when form opens
  useEffect(() => {
    if (!showForm) return;
    let cancelled = false;
    (async () => {
      try {
        const m = await getModels();
        if (!cancelled) {
          setModels(m);
          const keys = Object.keys(m);
          if (keys.length > 0 && !selectedModel) {
            setSelectedModel(keys[0]);
          }
        }
      } catch {
        // models fetch failed silently
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showForm]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch prompts when pass number changes
  useEffect(() => {
    if (!showForm) return;
    let cancelled = false;
    (async () => {
      try {
        const p = await getPrompts(passNumber);
        if (!cancelled) {
          setPrompts(p);
          if (p.length > 0) {
            setSelectedPrompt(p[0]);
          } else {
            setSelectedPrompt("");
          }
        }
      } catch {
        setPrompts([]);
        setSelectedPrompt("");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showForm, passNumber]);

  // Poll progress
  useEffect(() => {
    if (trackingId === null) return;

    const poll = async () => {
      try {
        const p = await getProgress(trackingId);
        setProgress(p);
        if (p.status === "completed" || p.status === "failed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          setTrackingId(null);
          setSubmitting(false);
          if (p.status === "completed") {
            setShowForm(false);
            fetchRuns();
          }
        }
      } catch {
        // polling error, keep trying
      }
    };

    poll();
    pollRef.current = setInterval(poll, 2000);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [trackingId, fetchRuns]);

  const handleSubmit = () => {
    if (!selectedModel || !selectedPrompt) {
      setFormError("Please select a model and prompt.");
      return;
    }
    setFormError(null);
    setProgress(null);
    setConfirmStep(true);
  };

  const executeRun = async () => {
    setConfirmStep(false);
    setSubmitting(true);
    setProgress(null);

    try {
      const result = await createRun({
        pass_number: passNumber,
        model: selectedModel,
        prompt_version: selectedPrompt,
        concurrency,
      });
      setTrackingId(result.tracking_id);
      setProgress({
        status: "starting",
        completed: 0,
        total: result.total,
      });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create run");
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setFormError(null);
    setProgress(null);
    setConfirmStep(false);
  };

  const modelKeys = Object.keys(models);
  const uniqueModels = [...new Set(runs.map((r) => r.model))];

  return (
    <AppShell title="Run Tests" subtitle="Execution history">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <p className="text-[13px] text-muted-foreground">
            {loading
              ? "Loading\u2026"
              : `${runs.length} runs across ${uniqueModels.length} models`}
          </p>
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              disabled={submitting}
              className="rounded-md border border-border bg-primary px-3 py-1.5 text-[13px] font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              New Run
            </button>
          )}
        </div>

        {showForm && (
          <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <h3 className="mb-4 text-[13px] font-semibold text-foreground">
              Configure New Run
            </h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <label className="mb-1 block text-[12px] font-medium text-muted-foreground">
                  Pass
                </label>
                <select
                  value={passNumber}
                  onChange={(e) => setPassNumber(Number(e.target.value))}
                  disabled={submitting}
                  className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-[13px] disabled:opacity-50"
                >
                  <option value={1}>Pass 1</option>
                  <option value={2}>Pass 2</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[12px] font-medium text-muted-foreground">
                  Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  disabled={submitting}
                  className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-[13px] disabled:opacity-50"
                >
                  {modelKeys.length === 0 && (
                    <option value="">Loading...</option>
                  )}
                  {modelKeys.map((key) => (
                    <option key={key} value={key}>
                      {models[key]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[12px] font-medium text-muted-foreground">
                  Prompt
                </label>
                <select
                  value={selectedPrompt}
                  onChange={(e) => setSelectedPrompt(e.target.value)}
                  disabled={submitting}
                  className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-[13px] disabled:opacity-50"
                >
                  {prompts.length === 0 && (
                    <option value="">Loading...</option>
                  )}
                  {prompts.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[12px] font-medium text-muted-foreground">
                  Concurrency
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={concurrency}
                  onChange={(e) => setConcurrency(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
                  disabled={submitting}
                  className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-[13px] font-mono tabular-nums disabled:opacity-50"
                />
              </div>
            </div>

            {formError && (
              <p className="mt-3 text-[12px] text-status-wrong">
                {formError}
              </p>
            )}

            {progress && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-muted-foreground">
                    {progress.status === "starting"
                      ? "Starting..."
                      : progress.status === "failed"
                        ? "Failed"
                        : `${progress.completed} / ${progress.total} postings`}
                  </span>
                  {progress.total > 0 && (
                    <span className="text-[11px] font-mono tabular-nums text-muted-foreground">
                      {Math.round((progress.completed / progress.total) * 100)}%
                    </span>
                  )}
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-300"
                    style={{
                      width:
                        progress.total > 0
                          ? `${(progress.completed / progress.total) * 100}%`
                          : "0%",
                    }}
                  />
                </div>
                {progress.status === "completed" && (
                  <p className="text-[11px] text-muted-foreground">
                    Completed &mdash; {formatCost(progress.cost_usd ?? null)} &middot;{" "}
                    {formatDuration(progress.duration_ms ?? null)}
                  </p>
                )}
                {progress.status === "failed" && progress.error && (
                  <p className="text-[12px] text-status-wrong">
                    {progress.error}
                  </p>
                )}
              </div>
            )}

            {confirmStep && !submitting && (
              <div className="mt-4 rounded-md border border-warning/40 bg-warning-muted px-4 py-3">
                <p className="mb-2 text-[12px] font-medium text-warning-foreground">
                  Ready to start run:
                </p>
                <ul className="mb-3 space-y-0.5 text-[12px] text-muted-foreground">
                  <li>Pass {passNumber} · {selectedModel} · {selectedPrompt}</li>
                  <li>Concurrency: {concurrency} | Corpus: all postings</li>
                </ul>
                <div className="flex gap-2">
                  <button onClick={executeRun}
                    className="rounded-md border border-border bg-primary px-3 py-1.5 text-[13px] font-medium text-primary-foreground transition-colors duration-150 hover:bg-primary/90">
                    Confirm &amp; Start
                  </button>
                  <button onClick={() => setConfirmStep(false)}
                    className="rounded-md border border-border bg-muted/30 px-3 py-1.5 text-[13px] font-medium text-muted-foreground transition-colors duration-150 hover:bg-muted/50">
                    Back
                  </button>
                </div>
              </div>
            )}

            <div className="mt-4 flex gap-2">
              {!confirmStep && (
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !selectedModel || !selectedPrompt}
                  className="rounded-md border border-border bg-primary px-3 py-1.5 text-[13px] font-medium text-primary-foreground transition-colors duration-150 hover:bg-primary/90 disabled:opacity-50">
                  {submitting ? "Running\u2026" : "Start Run"}
                </button>
              )}
              <button
                onClick={handleCancel}
                disabled={submitting}
                className="rounded-md border border-border bg-muted/30 px-3 py-1.5 text-[13px] font-medium text-muted-foreground hover:bg-muted/50 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {error && <ErrorBox message={error} />}

        {loading ? (
          <LoadingCard message="Loading runs…" />
        ) : (
          <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <DataTable
              columns={columns}
              data={runs}
              ariaLabel="Evaluation runs"
              rowKey={(row) => row.id}
            />
          </div>
        )}
      </div>
    </AppShell>
  );
}
