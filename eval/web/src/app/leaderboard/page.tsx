"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { DataTable, type Column } from "@/components/data-table";
import {
  getLeaderboardData,
  type Run,
  type Comparison,
  type Result,
} from "@/lib/api-client";
import { ErrorBox } from "@/components/error-box";
import { LoadingCard } from "@/components/loading-card";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LeaderboardRow {
  rank: number;
  label: string;
  model: string;
  prompt: string;
  elo: number;
  winPct: string;
  parseRate: string;
  accuracy: string;
  cost: string;
  latency: string;
}

interface FieldAccuracyRow {
  label: string;
  model: string;
  [field: string]: string;
}

type PassFilter = "all" | 1 | 2;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeLabel(model: string, prompt: string): string {
  return `${model}/${prompt}`;
}

function formatCost(cost: number | null): string {
  if (cost === null) return "\u2014";
  return `$${cost.toFixed(3)}`;
}

function formatLatency(durationMs: number | null, corpusSize: number): string {
  if (durationMs === null || corpusSize === 0) return "\u2014";
  return `${(durationMs / corpusSize / 1000).toFixed(1)}s`;
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RankCell({ rank }: { rank: number }) {
  if (rank === 1) {
    return <span className="font-semibold text-medal-gold">#{rank}</span>;
  }
  if (rank === 2) {
    return <span className="text-medal-silver">#{rank}</span>;
  }
  if (rank === 3) {
    return <span className="text-medal-bronze">#{rank}</span>;
  }
  return <span className="text-muted-foreground">#{rank}</span>;
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function LeaderboardPage() {
  // --- Data state ---
  const [runs, setRuns] = useState<Run[]>([]);
  const [eloRatings, setEloRatings] = useState<Record<string, number>>({});
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [fieldAccuracyMap, setFieldAccuracyMap] = useState<
    Record<number, Record<string, number>>
  >({});
  const [resultsByRun, setResultsByRun] = useState<
    Record<number, Result[]>
  >({});

  // --- UI state ---
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [passFilter, setPassFilter] = useState<PassFilter>("all");
  const [modelFilter, setModelFilter] = useState<string>("all");
  const promptFilter = "all"; // reserved for future prompt filter UI

  // --- Initial data fetch (single bulk request) ---
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await getLeaderboardData();

        if (cancelled) return;

        setRuns(data.runs);
        setEloRatings(data.elo);
        setComparisons(data.comparisons);

        // Convert string keys back to numbers for internal maps
        const accMap: Record<number, Record<string, number>> = {};
        for (const [id, acc] of Object.entries(data.field_accuracy)) {
          accMap[Number(id)] = acc;
        }
        setFieldAccuracyMap(accMap);

        const resMap: Record<number, Result[]> = {};
        for (const [id, res] of Object.entries(data.results)) {
          resMap[Number(id)] = res;
        }
        setResultsByRun(resMap);

        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load leaderboard data",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // --- Filter options ---
  const modelOptions = useMemo(() => {
    const models = [...new Set(runs.map((r) => r.model))].sort();
    return ["all", ...models];
  }, [runs]);

  // --- Filtered runs ---
  const filteredRuns = useMemo(() => {
    return runs.filter((r) => {
      if (passFilter !== "all" && r.pass_number !== passFilter) return false;
      if (modelFilter !== "all" && r.model !== modelFilter) return false;
      if (promptFilter !== "all" && r.prompt_version !== promptFilter) return false;
      return true;
    });
  }, [runs, passFilter, modelFilter, promptFilter]);

  // --- Result ID -> label mapping (for win% computation) ---
  const resultIdToLabel = useMemo(() => {
    const map: Record<number, string> = {};
    for (const run of filteredRuns) {
      const label = makeLabel(run.model, run.prompt_version);
      const results = resultsByRun[run.id] ?? [];
      for (const result of results) {
        map[result.id] = label;
      }
    }
    return map;
  }, [filteredRuns, resultsByRun]);

  // --- Win rates per label ---
  const winRates = useMemo(() => {
    const wins: Record<string, number> = {};
    const appearances: Record<string, number> = {};

    for (const comp of comparisons) {
      const labelA = resultIdToLabel[comp.result_a_id];
      const labelB = resultIdToLabel[comp.result_b_id];

      if (labelA) {
        appearances[labelA] = (appearances[labelA] ?? 0) + 1;
        if (comp.winner === "a") {
          wins[labelA] = (wins[labelA] ?? 0) + 1;
        }
      }
      if (labelB) {
        appearances[labelB] = (appearances[labelB] ?? 0) + 1;
        if (comp.winner === "b") {
          wins[labelB] = (wins[labelB] ?? 0) + 1;
        }
      }
    }

    const rates: Record<string, number> = {};
    for (const label of Object.keys(appearances)) {
      rates[label] = (wins[label] ?? 0) / appearances[label];
    }
    return rates;
  }, [comparisons, resultIdToLabel]);

  // --- Parse rate per run ---
  const parseRateByRun = useMemo(() => {
    const map: Record<number, number> = {};
    for (const run of runs) {
      const results = resultsByRun[run.id] ?? [];
      if (results.length === 0) continue;
      const parsed = results.filter((r) => r.parse_success).length;
      if (run.corpus_size === 0) continue;
      map[run.id] = parsed / run.corpus_size;
    }
    return map;
  }, [runs, resultsByRun]);

  // --- Aggregate field accuracy per run (average across all fields) ---
  const avgAccuracyByRun = useMemo(() => {
    const map: Record<number, number> = {};
    for (const run of runs) {
      const fieldAcc = fieldAccuracyMap[run.id];
      if (!fieldAcc) continue;
      const values = Object.values(fieldAcc);
      if (values.length === 0) continue;
      map[run.id] = values.reduce((a, b) => a + b, 0) / values.length;
    }
    return map;
  }, [runs, fieldAccuracyMap]);

  // --- Build leaderboard rows ---
  const leaderboardRows: LeaderboardRow[] = useMemo(() => {
    // Group runs by label. For each label, pick the run with the highest Elo
    // or the most recent run if Elo is absent.
    const labelToRuns: Record<string, Run[]> = {};
    for (const run of filteredRuns) {
      const label = makeLabel(run.model, run.prompt_version);
      if (!labelToRuns[label]) labelToRuns[label] = [];
      labelToRuns[label].push(run);
    }

    const unsorted: LeaderboardRow[] = [];

    for (const [label, labelRuns] of Object.entries(labelToRuns)) {
      const elo = eloRatings[label] ?? 0;
      const winPctVal = winRates[label];

      // Use the most recent run for cost/latency/parse metrics
      const bestRun = labelRuns.reduce((a, b) =>
        new Date(b.created_at) > new Date(a.created_at) ? b : a,
      );

      const parseRateVal = parseRateByRun[bestRun.id];
      const accuracyVal = avgAccuracyByRun[bestRun.id];

      unsorted.push({
        rank: 0,
        label,
        model: bestRun.model,
        prompt: bestRun.prompt_version,
        elo,
        winPct:
          winPctVal !== undefined ? `${(winPctVal * 100).toFixed(1)}%` : "\u2014",
        parseRate:
          parseRateVal !== undefined
            ? `${(parseRateVal * 100).toFixed(1)}%`
            : "\u2014",
        accuracy:
          accuracyVal !== undefined
            ? `${(accuracyVal * 100).toFixed(1)}%`
            : "\u2014",
        cost: formatCost(bestRun.total_cost_usd),
        latency: formatLatency(bestRun.total_duration_ms, bestRun.corpus_size),
      });
    }

    // Sort by Elo descending and assign ranks
    unsorted.sort((a, b) => b.elo - a.elo);
    return unsorted.map((row, i) => ({ ...row, rank: i + 1 }));
  }, [filteredRuns, eloRatings, winRates, parseRateByRun, avgAccuracyByRun]);

  // --- Elo Rankings table columns ---
  const leaderboardColumns: Column<LeaderboardRow>[] = useMemo(
    () => [
      {
        key: "rank",
        label: "Rank",
        render: (row) => <RankCell rank={row.rank} />,
      },
      {
        key: "model",
        label: "Model",
        render: (row) => (
          <span className="font-medium text-foreground">{row.model}</span>
        ),
      },
      {
        key: "prompt",
        label: "Prompt",
        render: (row) => (
          <span className="text-muted-foreground">{row.prompt}</span>
        ),
      },
      {
        key: "elo",
        label: "Elo",
        mono: true,
        sortable: true,
        render: (row) => (
          <span
            className="font-mono font-semibold tabular-nums"
            title="ELO rating calculated from A/B comparison votes. Higher = better."
          >
            {row.elo}
          </span>
        ),
      },
      {
        key: "winPct",
        label: "Win%",
        align: "right" as const,
        mono: true,
        sortable: true,
      },
      {
        key: "parseRate",
        label: "Parse Rate",
        align: "right" as const,
        mono: true,
        sortable: true,
      },
      {
        key: "accuracy",
        label: "Accuracy",
        align: "right" as const,
        mono: true,
        sortable: true,
      },
      {
        key: "cost",
        label: "Cost",
        align: "right" as const,
        mono: true,
        sortable: true,
      },
      {
        key: "latency",
        label: "Latency",
        align: "right" as const,
        mono: true,
        sortable: true,
        render: (row) => (
          <span className="font-mono tabular-nums text-muted-foreground">
            {row.latency}
          </span>
        ),
      },
    ],
    [],
  );

  // --- Field-level accuracy data ---
  const allFieldNames = useMemo(() => {
    const fieldSet = new Set<string>();
    for (const run of filteredRuns) {
      const fieldAcc = fieldAccuracyMap[run.id];
      if (fieldAcc) {
        for (const key of Object.keys(fieldAcc)) {
          fieldSet.add(key);
        }
      }
    }
    return Array.from(fieldSet).sort();
  }, [filteredRuns, fieldAccuracyMap]);

  const hasFieldAccuracy = allFieldNames.length > 0;

  const fieldAccuracyRows: FieldAccuracyRow[] = useMemo(() => {
    if (!hasFieldAccuracy) return [];

    // Group by label, pick best run per label
    const labelToRun: Record<string, Run> = {};
    for (const run of filteredRuns) {
      const label = makeLabel(run.model, run.prompt_version);
      if (
        !labelToRun[label] ||
        new Date(run.created_at) > new Date(labelToRun[label].created_at)
      ) {
        labelToRun[label] = run;
      }
    }

    return Object.entries(labelToRun).map(([label, run]) => {
      const fieldAcc = fieldAccuracyMap[run.id] ?? {};
      const row: FieldAccuracyRow = {
        label,
        model: `${run.model}/${run.prompt_version}`,
      };
      for (const field of allFieldNames) {
        row[field] =
          fieldAcc[field] !== undefined ? formatPct(fieldAcc[field]) : "\u2014";
      }
      return row;
    });
  }, [filteredRuns, fieldAccuracyMap, allFieldNames, hasFieldAccuracy]);

  const fieldAccuracyColumns: Column<FieldAccuracyRow>[] = useMemo(() => {
    const cols: Column<FieldAccuracyRow>[] = [
      {
        key: "model",
        label: "Model",
        render: (row) => <span className="font-medium">{row.model}</span>,
      },
    ];
    for (const field of allFieldNames) {
      cols.push({
        key: field,
        label: field,
        align: "center",
        mono: true,
        sortable: true,
        render: (row) => {
          const val = (row as Record<string, string>)[field];
          if (val === "\u2014") return <span className="text-muted-foreground/50">{val}</span>;
          const num = parseFloat(val);
          return (
            <span
              className={cn(
                "font-mono tabular-nums text-[12px]",
                num >= 90
                  ? "text-threshold-high font-medium"
                  : num >= 70
                    ? "text-threshold-mid"
                    : "text-threshold-low",
              )}
            >
              {val}
            </span>
          );
        },
      });
    }
    return cols;
  }, [allFieldNames]);

  // --- Pass filter options ---
  const passOptions: { label: string; value: PassFilter }[] = [
    { label: "All", value: "all" },
    { label: "Pass 1", value: 1 },
    { label: "Pass 2", value: 2 },
  ];


  return (
    <AppShell title="Leaderboard" subtitle="Model rankings">
      <div className="space-y-6">
        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Pass filter */}
          <div className="flex items-center gap-1">
            <span className="text-[11px] text-muted-foreground/60 mr-1">Pass</span>
            {passOptions.map((opt) => (
              <button
                key={String(opt.value)}
                onClick={() => setPassFilter(opt.value)}
                className={`rounded px-2 py-1 text-[12px] font-medium transition-colors duration-150 ${
                  passFilter === opt.value
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted/30 text-muted-foreground hover:bg-muted/50"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {/* Model filter - only show if more than 1 unique model */}
          {modelOptions.length > 2 && (
            <div className="flex items-center gap-1">
              <span className="text-[11px] text-muted-foreground/60 mr-1">Model</span>
              {modelOptions.map((m) => (
                <button
                  key={m}
                  onClick={() => setModelFilter(m)}
                  className={`rounded px-2 py-1 text-[12px] font-medium transition-colors duration-150 ${
                    modelFilter === m
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted/30 text-muted-foreground hover:bg-muted/50"
                  }`}
                >
                  {m === "all" ? "All" : m}
                </button>
              ))}
            </div>
          )}
          {/* Results count */}
          <span className="ml-auto text-[11px] text-muted-foreground/60">
            {filteredRuns.length} of {runs.length} runs
          </span>
        </div>

        {/* Error state */}
        {error && <ErrorBox message={error} />}

        {/* Loading state */}
        {loading ? (
          <LoadingCard message="Loading leaderboard data…" />
        ) : (
          <>
            {/* Elo Rankings */}
            <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
              <h3 className="font-display mb-4 text-[14px] font-semibold text-foreground">
                Elo Rankings
              </h3>
              {leaderboardRows.length > 0 ? (
                <DataTable
                  columns={leaderboardColumns}
                  data={leaderboardRows}
                  ariaLabel="Elo rankings"
                  rowKey={(row) => row.label}
                />
              ) : (
                <p className="text-[13px] text-muted-foreground">
                  No runs found
                </p>
              )}
            </div>

            {/* Field-Level Accuracy */}
            {hasFieldAccuracy && (
              <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
                <h3 className="font-display mb-1 text-[14px] font-semibold text-foreground">
                  Field-Level Accuracy
                </h3>
                <p className="mb-4 text-[12px] text-muted-foreground/50">
                  Accuracy of each field based on human reviews
                </p>
                {fieldAccuracyRows.length > 0 ? (
                  <DataTable
                    columns={fieldAccuracyColumns}
                    data={fieldAccuracyRows}
                    ariaLabel="Field-level accuracy"
                    rowKey={(row) => row.label}
                  />
                ) : (
                  <p className="text-[13px] text-muted-foreground">
                    No comparisons yet
                  </p>
                )}
              </div>
            )}

            {/* Next-step link */}
            <div className="flex items-center justify-end border-t border-border/50 pt-4">
              <Link href="/review" className="text-[12px] text-primary hover:underline">
                Compare runs to improve ELO data →
              </Link>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
