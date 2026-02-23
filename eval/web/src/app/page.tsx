"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { BarList } from "@/components/ui/bar-list";
import { getRuns, type Run } from "@/lib/api-client";
import {
  FlaskConical,
  CheckCircle2,
  TrendingUp,
  Clock,
} from "lucide-react";

// --- Page ---

export default function DashboardPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRuns()
      .then(setRuns)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <AppShell title="Dashboard" subtitle="Evaluation overview">
        <div className="flex h-64 items-center justify-center">
          <span className="text-[13px] text-muted-foreground">
            Loading dashboard...
          </span>
        </div>
      </AppShell>
    );
  }

  if (runs.length === 0) {
    return (
      <AppShell title="Dashboard" subtitle="Evaluation overview">
        <div className="flex h-64 flex-col items-center justify-center gap-2">
          <span className="text-[14px] font-medium text-foreground">
            No runs yet
          </span>
          <span className="text-[12px] text-muted-foreground/50">
            Head to the Run Tests page to start your first evaluation run.
          </span>
        </div>
      </AppShell>
    );
  }

  // --- Computed metrics ---

  const uniqueModels = new Set(runs.map((r) => r.model));

  const runsWithCost = runs.filter((r) => r.total_cost_usd !== null);
  const avgCost =
    runsWithCost.length > 0
      ? `$${(
          runsWithCost.reduce((sum, r) => sum + r.total_cost_usd!, 0) /
          runsWithCost.length
        ).toFixed(3)}`
      : "—";

  const runsWithDuration = runs.filter(
    (r) => r.total_duration_ms !== null && r.corpus_size > 0,
  );
  const avgLatency =
    runsWithDuration.length > 0
      ? `${(
          runsWithDuration.reduce(
            (sum, r) => sum + r.total_duration_ms! / r.corpus_size / 1000,
            0,
          ) / runsWithDuration.length
        ).toFixed(1)}s`
      : "—";

  // Derive status per run
  const deriveStatus = (run: Run): "completed" | "running" =>
    run.total_cost_usd !== null ? "completed" : "running";

  // Status → Badge variant
  const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "neutral"> = {
    completed: "success",
    running: "warning",
  };

  // Already in descending order from API (newest first)
  const sortedRuns = runs;

  // Corpus coverage from first run
  const corpusSize = runs.length > 0 ? runs[0].corpus_size : 0;

  // Cost comparison for BarList
  const costData = runs
    .filter((r) => r.total_cost_usd !== null)
    .map((r) => ({
      name: `${r.model} / ${r.prompt_version}`,
      value: r.total_cost_usd!,
    }));

  return (
    <AppShell title="Dashboard" subtitle="Evaluation overview">
      <div className="space-y-8">
        {/* KPI cards */}
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <KpiCard
            label="Total Runs"
            value={String(runs.length)}
            subtext={`${uniqueModels.size} models tested`}
            icon={FlaskConical}
          />
          <KpiCard
            label="Unique Models"
            value={String(uniqueModels.size)}
            subtext="distinct model configurations"
            icon={CheckCircle2}
          />
          <KpiCard
            label="Avg Cost"
            value={avgCost}
            subtext="per run"
            icon={TrendingUp}
          />
          <KpiCard
            label="Avg Latency"
            value={avgLatency}
            subtext="per posting"
            icon={Clock}
          />
        </div>

        {/* Content grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Recent runs — 2 cols */}
          <div className="rounded-lg border border-border bg-card p-5 shadow-sm lg:col-span-2">
            <div className="mb-4 flex items-baseline justify-between">
              <h3 className="font-display text-[14px] font-semibold text-foreground">
                Recent Runs
              </h3>
              <span className="text-[12px] text-muted-foreground/50">
                All runs
              </span>
            </div>

            <table className="w-full" aria-label="Recent evaluation runs">
              <thead>
                <tr className="border-b border-border">
                  <th
                    scope="col"
                    className="px-2 pb-2 text-left text-[11px] font-medium uppercase tracking-wider text-muted-foreground/50"
                  >
                    Status
                  </th>
                  <th
                    scope="col"
                    className="px-2 pb-2 text-left text-[11px] font-medium uppercase tracking-wider text-muted-foreground/50"
                  >
                    Model / Prompt
                  </th>
                  <th
                    scope="col"
                    className="w-16 px-2 pb-2 text-right text-[11px] font-medium uppercase tracking-wider text-muted-foreground/50"
                  >
                    Cost
                  </th>
                  <th
                    scope="col"
                    className="w-14 px-2 pb-2 text-right text-[11px] font-medium uppercase tracking-wider text-muted-foreground/50"
                  >
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedRuns.map((run) => {
                  const status = deriveStatus(run);
                  return (
                    <tr
                      key={run.id}
                      className="border-b border-border/50 transition-colors duration-100 last:border-0 hover:bg-muted/30"
                    >
                      <td className="px-2 py-2.5">
                        <Badge
                          variant={STATUS_VARIANT[status] ?? "neutral"}
                        >
                          {status}
                        </Badge>
                      </td>
                      <td className="px-2 py-2.5 text-[13px]">
                        <span className="font-medium text-foreground">
                          {run.model}
                        </span>
                        <span className="text-muted-foreground">
                          /{run.prompt_version}
                        </span>
                      </td>
                      <td className="w-16 px-2 py-2.5 text-right font-mono text-[12px] tabular-nums text-muted-foreground">
                        {run.total_cost_usd !== null
                          ? `$${run.total_cost_usd.toFixed(3)}`
                          : "—"}
                      </td>
                      <td className="w-14 px-2 py-2.5 text-right font-mono text-[12px] tabular-nums text-muted-foreground/50">
                        {run.total_duration_ms !== null
                          ? `${(run.total_duration_ms / 1000).toFixed(1)}s`
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Review progress — 1 col */}
          <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <h3 className="font-display mb-4 text-[14px] font-semibold text-foreground">
              Review Progress
            </h3>

            <div className="space-y-4">
              {/* Corpus coverage */}
              <div>
                <div className="mb-1.5 flex items-baseline justify-between">
                  <span className="text-[13px] font-normal text-foreground">
                    Corpus Coverage
                  </span>
                </div>
                <span className="font-mono text-2xl font-semibold tabular-nums text-foreground">
                  {corpusSize}
                </span>
                <span className="mt-1 block text-[11px] text-muted-foreground/50">
                  postings in corpus
                </span>
              </div>

              {/* Field coverage placeholder */}
              <div className="border-t border-border/50 pt-4">
                <div className="mb-1.5 flex items-baseline justify-between">
                  <span className="text-[13px] font-normal text-foreground">
                    Field Coverage
                  </span>
                </div>
                <span className="block text-[12px] text-muted-foreground/50">
                  Connect accuracy reviews for field coverage
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Cost per run — full width BarList */}
        <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <h3 className="font-display mb-4 text-[14px] font-semibold text-foreground">
            Cost per Run
          </h3>
          {costData.length > 0 ? (
            <BarList
              data={costData}
              valueFormatter={(v) => `$${v.toFixed(3)}`}
              showAnimation
            />
          ) : (
            <span className="text-[12px] text-muted-foreground/50">
              No cost data available yet.
            </span>
          )}
        </div>
      </div>
    </AppShell>
  );
}

// --- KPI Card ---

function KpiCard({
  label,
  value,
  subtext,
  icon: Icon,
}: {
  label: string;
  value: string;
  subtext: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="rounded-md border border-border bg-card p-4 pb-3 transition-colors duration-150 hover:border-border/80">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <span className="text-[13px] font-medium text-muted-foreground">
            {label}
          </span>
          <div>
            <span className="font-mono text-2xl font-semibold tracking-tight text-foreground">
              {value}
            </span>
          </div>
          <span className="text-[12px] font-normal text-muted-foreground/50">
            {subtext}
          </span>
        </div>
        <div className="rounded-md bg-muted p-2.5">
          <Icon className="size-4 text-muted-foreground" />
        </div>
      </div>
    </div>
  );
}
