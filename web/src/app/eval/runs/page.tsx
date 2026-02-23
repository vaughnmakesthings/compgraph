"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api-client";
import type { EvalRun } from "@/lib/types";
import { Badge } from "@/components/data/badge";
import type { BadgeVariant } from "@/components/data/badge";

function formatCost(usd: number | null): string {
  if (usd === null) return "\u2014";
  return `$${usd.toFixed(3)}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatProgress(run: EvalRun): string {
  if (run.total_items === 0) return "\u2014";
  return `${run.completed_items} / ${run.total_items}`;
}

function statusVariant(status: string): BadgeVariant {
  if (status === "completed") return "success";
  if (status === "failed") return "error";
  if (status === "running") return "warning";
  return "neutral";
}

function RunRow({ run }: { run: EvalRun }) {
  const progress =
    run.total_items > 0
      ? Math.round((run.completed_items / run.total_items) * 100)
      : null;

  return (
    <tr className="border-b border-[#BFC0C0] last:border-0 hover:bg-[#E8E8E41A] transition-colors duration-150">
      <td
        className="py-3 pr-4 pl-2"
        style={{
          fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
          fontSize: "12px",
          color: "#4F5D75",
        }}
      >
        {run.id.slice(0, 8)}
      </td>
      <td className="py-3 pr-4">
        <span
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            fontWeight: 500,
            color: "#2D3142",
          }}
        >
          {run.model}
        </span>
        <span
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "12px",
            color: "#4F5D75",
          }}
        >
          {" / "}
          {run.prompt_version}
        </span>
      </td>
      <td
        className="py-3 pr-4"
        style={{
          fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
          fontSize: "12px",
          color: "#4F5D75",
        }}
      >
        {run.pass_number}
      </td>
      <td className="py-3 pr-4">
        <Badge variant={statusVariant(run.status)} size="sm">
          {run.status}
        </Badge>
      </td>
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2">
          <span
            style={{
              fontFamily:
                "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "12px",
              color: "#4F5D75",
            }}
          >
            {formatProgress(run)}
          </span>
          {progress !== null && (
            <div className="w-16 h-1 bg-[#E8E8E4] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${progress}%`,
                  backgroundColor: "#EF8354",
                }}
              />
            </div>
          )}
        </div>
      </td>
      <td
        className="py-3 text-right"
        style={{
          fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
          fontSize: "12px",
          color: "#4F5D75",
        }}
      >
        {formatDate(run.created_at)}
      </td>
    </tr>
  );
}

interface NewRunFormProps {
  onCancel: () => void;
  onCreated: () => void;
}

function NewRunForm({ onCancel, onCreated }: NewRunFormProps) {
  const [passNumber, setPassNumber] = useState(1);
  const [model, setModel] = useState("claude-haiku-4-5-20251001");
  const [promptVersion, setPromptVersion] = useState("pass1_v1");
  const [concurrency, setConcurrency] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmStep, setConfirmStep] = useState(false);

  const handleSubmit = () => {
    if (!promptVersion.trim()) {
      setFormError("Prompt version is required.");
      return;
    }
    setFormError(null);
    setConfirmStep(true);
  };

  const executeRun = async () => {
    setConfirmStep(false);
    setSubmitting(true);
    try {
      await api.createEvalRun({
        pass_number: passNumber,
        model: model.trim(),
        prompt_version: promptVersion.trim(),
        concurrency,
      });
      onCreated();
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to create run",
      );
      setSubmitting(false);
    }
  };

  return (
    <div
      className="rounded-lg border p-5 mb-6"
      style={{
        backgroundColor: "#FFFFFF",
        borderColor: "#BFC0C0",
        boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
      }}
    >
      <h3
        className="mb-4 font-semibold"
        style={{
          fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
          fontSize: "14px",
          color: "#2D3142",
        }}
      >
        Configure New Run
      </h3>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <label
            className="mb-1 block"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              fontWeight: 500,
              color: "#4F5D75",
            }}
          >
            Pass
          </label>
          <select
            value={passNumber}
            onChange={(e) => setPassNumber(Number(e.target.value))}
            disabled={submitting}
            className="w-full rounded border px-2 py-1.5 disabled:opacity-50"
            style={{
              borderColor: "#BFC0C0",
              backgroundColor: "#FFFFFF",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#2D3142",
              borderRadius: "var(--radius-sm, 4px)",
            }}
          >
            <option value={1}>Pass 1</option>
            <option value={2}>Pass 2</option>
          </select>
        </div>
        <div>
          <label
            className="mb-1 block"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              fontWeight: 500,
              color: "#4F5D75",
            }}
          >
            Model
          </label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={submitting}
            className="w-full rounded border px-2 py-1.5 disabled:opacity-50"
            style={{
              borderColor: "#BFC0C0",
              backgroundColor: "#FFFFFF",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#2D3142",
              borderRadius: "var(--radius-sm, 4px)",
            }}
          >
            <option value="claude-haiku-4-5-20251001">Haiku 4.5 (fast, cheap)</option>
            <option value="claude-sonnet-4-5-20251001">Sonnet 4.5 (balanced)</option>
            <option value="claude-sonnet-4-6">Sonnet 4.6 (latest)</option>
            <option value="claude-opus-4-6">Opus 4.6 (highest quality)</option>
          </select>
        </div>
        <div>
          <label
            className="mb-1 block"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              fontWeight: 500,
              color: "#4F5D75",
            }}
          >
            Prompt Version
          </label>
          <input
            type="text"
            value={promptVersion}
            onChange={(e) => setPromptVersion(e.target.value)}
            disabled={submitting}
            placeholder="e.g. pass1_v1"
            className="w-full rounded border px-2 py-1.5 disabled:opacity-50"
            style={{
              borderColor: "#BFC0C0",
              backgroundColor: "#FFFFFF",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#2D3142",
              borderRadius: "var(--radius-sm, 4px)",
            }}
          />
        </div>
        <div>
          <label
            className="mb-1 block"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              fontWeight: 500,
              color: "#4F5D75",
            }}
          >
            Concurrency
          </label>
          <input
            type="number"
            min={1}
            max={50}
            value={concurrency}
            onChange={(e) =>
              setConcurrency(
                Math.max(1, Math.min(50, Number(e.target.value) || 1)),
              )
            }
            disabled={submitting}
            className="w-full rounded border px-2 py-1.5 disabled:opacity-50"
            style={{
              borderColor: "#BFC0C0",
              backgroundColor: "#FFFFFF",
              fontFamily:
                "var(--font-mono, 'JetBrains Mono Variable', monospace)",
              fontSize: "13px",
              color: "#2D3142",
              borderRadius: "var(--radius-sm, 4px)",
            }}
          />
        </div>
      </div>

      {formError && (
        <p
          className="mt-3"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "12px",
            color: "#8C2C23",
          }}
        >
          {formError}
        </p>
      )}

      {confirmStep && (
        <div
          className="mt-4 rounded-lg border px-4 py-3"
          style={{
            backgroundColor: "#DCB2561A",
            borderColor: "#DCB25640",
            borderRadius: "var(--radius-sm, 4px)",
          }}
        >
          <p
            className="mb-2 font-medium"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              color: "#A07D28",
            }}
          >
            Ready to start run:
          </p>
          <ul
            className="mb-3 space-y-0.5"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "12px",
              color: "#4F5D75",
            }}
          >
            <li>
              Pass {passNumber} · {model} · {promptVersion}
            </li>
            <li>Concurrency: {concurrency}</li>
          </ul>
          <div className="flex gap-2">
            <button
              onClick={executeRun}
              className="rounded px-3 py-1.5 font-medium transition-opacity duration-150 hover:opacity-90"
              style={{
                backgroundColor: "#EF8354",
                color: "#FFFFFF",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "13px",
                borderRadius: "var(--radius-sm, 4px)",
              }}
            >
              Confirm &amp; Start
            </button>
            <button
              onClick={() => setConfirmStep(false)}
              className="rounded border px-3 py-1.5 font-medium transition-colors duration-150 hover:bg-[#E8E8E4]"
              style={{
                borderColor: "#BFC0C0",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "13px",
                color: "#4F5D75",
                borderRadius: "var(--radius-sm, 4px)",
              }}
            >
              Back
            </button>
          </div>
        </div>
      )}

      {!confirmStep && (
        <div className="mt-4 flex gap-2">
          <button
            onClick={handleSubmit}
            disabled={submitting || !promptVersion.trim()}
            className="rounded px-3 py-1.5 font-medium transition-opacity duration-150 hover:opacity-90 disabled:opacity-50"
            style={{
              backgroundColor: "#EF8354",
              color: "#FFFFFF",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              borderRadius: "var(--radius-sm, 4px)",
            }}
          >
            {submitting ? "Starting\u2026" : "Start Run"}
          </button>
          <button
            onClick={onCancel}
            disabled={submitting}
            className="rounded border px-3 py-1.5 font-medium transition-colors duration-150 hover:bg-[#E8E8E4] disabled:opacity-50"
            style={{
              borderColor: "#BFC0C0",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#4F5D75",
              borderRadius: "var(--radius-sm, 4px)",
            }}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

export default function EvalRunsPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const fetchRuns = useCallback(async () => {
    try {
      const data = await api.listEvalRuns();
      setRuns(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch runs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchRuns();
  }, [fetchRuns]);

  const uniqueModels = [...new Set(runs.map((r) => r.model))].length;

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
          }}
        >
          Eval Runs
        </h1>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground, #4F5D75)",
          }}
        >
          Execution history across prompt versions and models
        </p>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <p
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#4F5D75",
          }}
        >
          {loading
            ? "Loading\u2026"
            : `${runs.length} runs across ${uniqueModels} models`}
        </p>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="rounded px-3 py-1.5 font-medium transition-opacity duration-150 hover:opacity-90"
            style={{
              backgroundColor: "#EF8354",
              color: "#FFFFFF",
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              borderRadius: "var(--radius-sm, 4px)",
            }}
          >
            New Run
          </button>
        )}
      </div>

      {showForm && (
        <NewRunForm
          onCancel={() => setShowForm(false)}
          onCreated={() => {
            setShowForm(false);
            void fetchRuns();
          }}
        />
      )}

      {error && (
        <div
          className="mb-4 rounded-lg border px-4 py-3 text-sm"
          role="alert"
          style={{
            backgroundColor: "#8C2C231A",
            borderColor: "#8C2C2333",
            color: "#8C2C23",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          }}
        >
          {error}
        </div>
      )}

      <div
        className="rounded-lg border"
        style={{
          backgroundColor: "#FFFFFF",
          borderColor: "#BFC0C0",
          boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
          borderRadius: "var(--radius-lg, 8px)",
        }}
      >
        {loading ? (
          <div
            className="flex items-center justify-center py-16"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#4F5D75",
            }}
          >
            Loading runs\u2026
          </div>
        ) : runs.length === 0 ? (
          <div
            className="flex items-center justify-center py-16"
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "#4F5D75",
            }}
          >
            No runs yet. Start your first eval run above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full" aria-label="Evaluation runs">
              <thead>
                <tr className="border-b border-[#BFC0C0]">
                  {["ID", "Model / Prompt", "Pass", "Status", "Progress", "Date"].map(
                    (h) => (
                      <th
                        key={h}
                        className="pb-3 pt-4 pl-2 pr-4 text-left last:text-right"
                        style={{
                          fontFamily:
                            "var(--font-body, 'DM Sans Variable', sans-serif)",
                          fontSize: "11px",
                          fontWeight: 500,
                          color: "#4F5D75",
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                        }}
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <RunRow key={run.id} run={run} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
