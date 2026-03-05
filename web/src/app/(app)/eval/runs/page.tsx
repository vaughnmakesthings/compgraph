/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  getRunsApiV1EvalRunsGetOptions, 
  listModelsApiV1EvalModelsGetOptions, 
  createRunApiV1EvalRunsPostMutation,
  deleteRunApiV1EvalRunsRunIdDeleteMutation
} from "@/api-client/@tanstack/react-query.gen";
import { Badge } from "@/components/data/badge";
import type { BadgeVariant } from "@/components/data/badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import type { EvalRun, EvalModel } from "@/lib/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatProgress(run: any): string {
  if (run.total_items === 0) return "\u2014";
  return `${run.completed_items} / ${run.total_items}`;
}

function statusVariant(status: string): BadgeVariant {
  if (status === "completed") return "success";
  if (status === "failed") return "error";
  if (status === "running") return "warning";
  return "neutral";
}

function RunRow({ run, onDelete }: { run: EvalRun; onDelete: (id: string) => void }) {
  const progress =
    run.total_items > 0
      ? Math.round((run.completed_items / run.total_items) * 100)
      : null;

  return (
    <tr className="border-b border-[#BFC0C0] last:border-0 hover:bg-[#E8E8E41A] transition-colors duration-150">
      <td className="py-3 pr-4 pl-2 font-mono text-xs text-[#4F5D75]">
        {run.id.slice(0, 8)}
      </td>
      <td className="py-3 pr-4">
        <span className="font-body text-[13px] font-medium text-[#2D3142]">
          {run.model}
        </span>
        <span className="font-body text-xs text-[#4F5D75]">
          {" / "}
          {run.prompt_version}
        </span>
      </td>
      <td className="py-3 pr-4 font-mono text-xs text-[#4F5D75]">
        {run.pass_number}
      </td>
      <td className="py-3 pr-4">
        <Badge variant={statusVariant(run.status)} size="sm">
          {run.status}
        </Badge>
      </td>
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-[#4F5D75]">
            {formatProgress(run)}
          </span>
          {progress !== null && (
            <div className="w-16 h-1 bg-[#E8E8E4] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-[#EF8354]"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>
      </td>
      <td className="py-3 text-right font-mono text-xs text-[#4F5D75]">
        {formatDate(run.created_at)}
      </td>
      <td className="py-3 text-right pr-2">
        <button
          type="button"
          onClick={() => onDelete(run.id)}
          className="text-[#8C2C23] hover:opacity-70 text-xs font-medium font-body"
        >
          Delete
        </button>
      </td>
    </tr>
  );
}

function NewRunForm({ onCancel }: { onCancel: () => void }) {
  const queryClient = useQueryClient();
  const [passNumber, setPassNumber] = useState(1);
  const [model, setModel] = useState("");
  const [promptVersion, setPromptVersion] = useState("pass1_v1");
  const [concurrency, setConcurrency] = useState(5);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmStartOpen, setConfirmStartOpen] = useState(false);

  const { data: models = [], isLoading: modelsLoading } = useQuery({
    ...listModelsApiV1EvalModelsGetOptions(),
    select: (data) => data as unknown as EvalModel[],
  });

  const createMutation = useMutation({
    ...createRunApiV1EvalRunsPostMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["eval", "runs"] });
      onCancel();
    },
    onError: (err: any) => {
      setFormError(err.message || "Failed to create run");
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!model) {
      setFormError("Please select a model");
      return;
    }
    setConfirmStartOpen(true);
  };

  const handleConfirmedStart = () => {
    setConfirmStartOpen(false);
    createMutation.mutate({
      body: {
        pass_number: passNumber,
        model,
        prompt_version: promptVersion,
        concurrency,
      }
    });
  };

  return (
    <div className="mb-8 p-6 border border-[#EF835433] rounded-lg bg-[#EF835405] shadow-sm">
      <h2 className="text-lg font-semibold font-display text-[#2D3142] mb-4">
        Start New Eval Run
      </h2>

      {formError && (
        <div className="mb-4 p-3 bg-[#8C2C231A] border border-[#8C2C2333] rounded text-[#8C2C23] text-sm font-body">
          {formError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-[#4F5D75] uppercase tracking-wider font-body">
            Pass Number
          </label>
          <select
            value={passNumber}
            onChange={(e) => {
              const val = parseInt(e.target.value);
              setPassNumber(val);
              setPromptVersion(val === 1 ? "pass1_v1" : "pass2_v1");
            }}
            className="border border-[#BFC0C0] rounded px-3 py-2 text-sm bg-white text-[#2D3142] font-body focus:outline-none focus:ring-1 focus:ring-[#EF8354]"
          >
            <option value={1}>Pass 1 (Classification)</option>
            <option value={2}>Pass 2 (Extraction)</option>
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-[#4F5D75] uppercase tracking-wider font-body">
            Model
          </label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={modelsLoading}
            className="border border-[#BFC0C0] rounded px-3 py-2 text-sm bg-white text-[#2D3142] font-body focus:outline-none focus:ring-1 focus:ring-[#EF8354] disabled:opacity-50"
          >
            <option value="">Select a model...</option>
            {models.map((m: EvalModel) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-[#4F5D75] uppercase tracking-wider font-body">
            Prompt Version
          </label>
          <input
            type="text"
            value={promptVersion}
            onChange={(e) => setPromptVersion(e.target.value)}
            className="border border-[#BFC0C0] rounded px-3 py-2 text-sm bg-white text-[#2D3142] font-body focus:outline-none focus:ring-1 focus:ring-[#EF8354]"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-[#4F5D75] uppercase tracking-wider font-body">
            Concurrency
          </label>
          <input
            type="number"
            min={1}
            max={20}
            value={concurrency}
            onChange={(e) => setConcurrency(parseInt(e.target.value))}
            className="border border-[#BFC0C0] rounded px-3 py-2 text-sm bg-white text-[#2D3142] font-body focus:outline-none focus:ring-1 focus:ring-[#EF8354]"
          />
        </div>

        <div className="md:col-span-2 lg:col-span-4 flex justify-end gap-3 mt-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-[#4F5D75] hover:bg-[#E8E8E4] rounded-md transition-colors duration-150 font-body"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="px-6 py-2 text-sm font-semibold text-white bg-[#EF8354] hover:bg-[#D86D3F] rounded-md shadow-sm transition-colors duration-150 font-body disabled:opacity-50"
          >
            {createMutation.isPending ? "Starting..." : "Start Run"}
          </button>
        </div>
      </form>

      <ConfirmDialog
        open={confirmStartOpen}
        onOpenChange={(open) => setConfirmStartOpen(open)}
        onConfirm={handleConfirmedStart}
        title="Start Evaluation Run"
        description={`This will trigger LLM processing for all items in the eval corpus using ${model}. Cost will be incurred.`}
        confirmLabel="Confirm & Start"
      />
    </div>
  );
}

export default function EvalRunsPage() {
  const queryClient = useQueryClient();
  const [showNewForm, setShowNewForm] = useState(false);
  const [runToDelete, setRunToDelete] = useState<string | null>(null);

  const { data: runs = [], isLoading } = useQuery({
    ...getRunsApiV1EvalRunsGetOptions(),
    refetchInterval: 5000,
    select: (data) => data as unknown as EvalRun[],
  });

  const deleteMutation = useMutation({
    ...deleteRunApiV1EvalRunsRunIdDeleteMutation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["eval", "runs"] });
      setRunToDelete(null);
    }
  });

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight font-display text-[#2D3142]">
            Evaluation Runs
          </h1>
          <p className="mt-1 text-sm font-body text-[#4F5D75]">
            Benchmark model performance against gold-standard data
          </p>
        </div>
        {!showNewForm && (
          <button
            type="button"
            onClick={() => setShowNewForm(true)}
            className="px-4 py-2 text-sm font-semibold text-white bg-[#2D3142] hover:bg-[#4F5D75] rounded-md shadow-sm transition-colors duration-150 font-body"
          >
            New Run
          </button>
        )}
      </div>

      {showNewForm && <NewRunForm onCancel={() => setShowNewForm(false)} />}

      <div className="rounded-lg border border-[#BFC0C0] bg-white shadow-sm overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-[#E8E8E4] border-b border-[#BFC0C0]">
              <th className="py-2.5 pr-4 pl-2 font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider">ID</th>
              <th className="py-2.5 pr-4 font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider">Model / Version</th>
              <th className="py-2.5 pr-4 font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider">Pass</th>
              <th className="py-2.5 pr-4 font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider">Status</th>
              <th className="py-2.5 pr-4 font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider">Progress</th>
              <th className="py-2.5 text-right font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider">Date</th>
              <th className="py-2.5 text-right pr-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#BFC0C0]">
            {isLoading && runs.length === 0 ? (
              Array.from({ length: 3 }).map((_, i) => (
                <tr key={i} className="animate-pulse">
                  <td colSpan={7} className="py-4 px-2">
                    <div className="h-4 bg-[#E8E8E4] rounded w-full" />
                  </td>
                </tr>
              ))
            ) : runs.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-sm font-body text-[#4F5D75]">
                  No evaluation runs found
                </td>
              </tr>
            ) : (
              runs.map((run: EvalRun) => (
                <RunRow 
                  key={run.id} 
                  run={run} 
                  onDelete={(id) => setRunToDelete(id)} 
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={!!runToDelete}
        onOpenChange={(open) => !open && setRunToDelete(null)}
        onConfirm={async () => {
          if (runToDelete) await deleteMutation.mutateAsync({ path: { run_id: runToDelete } });
        }}
        title="Delete Run"
        description="Are you sure you want to delete this evaluation run and all its results? This action cannot be undone."
        confirmLabel="Delete"
        confirmVariant="danger"
      />
    </div>
  );
}
