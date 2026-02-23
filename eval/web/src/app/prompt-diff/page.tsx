"use client";

import { Suspense } from "react";
import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { DataTable, type Column } from "@/components/data-table";
import { getRuns, getRunResults, type Run, type Result } from "@/lib/api-client";
import { formatRunLabel } from "@/lib/run-utils";
import { cn } from "@/lib/utils";

const COMPARE_FIELDS = [
  "role_archetype",
  "role_level",
  "employment_type",
  "pay_type",
  "pay_frequency",
  "pay_min",
  "pay_max",
  "has_commission",
  "has_benefits",
  "travel_required",
  "store_count",
  "tools_mentioned",
  "kpis_mentioned",
];

interface FieldDiffStats {
  field: string;
  matches: number;
  divergences: number;
  baselineOnly: number;
  candidateOnly: number;
}

function normalizeValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value)) {
    return value.length === 0 ? null : JSON.stringify(value.sort());
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function DotIndicator({ variant }: { variant: "match" | "diverge" }) {
  return (
    <span
      className={cn(
        "mr-1.5 inline-block size-1.5 rounded-full",
        variant === "match" ? "bg-status-correct" : "bg-status-wrong",
      )}
    />
  );
}

const columns: Column<FieldDiffStats>[] = [
  {
    key: "field",
    label: "Field",
    render: (row) => (
      <span className="text-[12px] text-muted-foreground">{row.field}</span>
    ),
  },
  {
    key: "matches",
    label: "Matches",
    align: "right",
    mono: true,
    render: (row) => (
      <span>
        <DotIndicator variant="match" />
        {row.matches}
      </span>
    ),
  },
  {
    key: "divergences",
    label: "Divergences",
    align: "right",
    mono: true,
    render: (row) => (
      <span>
        <DotIndicator variant="diverge" />
        {row.divergences}
      </span>
    ),
  },
  {
    key: "matchPct",
    label: "Match%",
    align: "right",
    mono: true,
    render: (row) => {
      const total = row.matches + row.divergences + row.baselineOnly + row.candidateOnly;
      if (total === 0) return <span className="text-muted-foreground">\u2014</span>;
      const pct = Math.round((row.matches / total) * 100);
      return (
        <span
          className={cn(
            "font-semibold",
            pct >= 90
              ? "text-threshold-high"
              : pct >= 70
                ? "text-threshold-mid"
                : "text-threshold-low",
          )}
        >
          {pct}%
        </span>
      );
    },
  },
];

function PromptDiffPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // --- Data state ---
  const [runs, setRuns] = useState<Run[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);

  const [baselineRunId, setBaselineRunId] = useState<number | null>(() => {
    const p = searchParams.get("baseline");
    return p ? Number(p) : null;
  });
  const [candidateRunId, setCandidateRunId] = useState<number | null>(() => {
    const p = searchParams.get("candidate");
    return p ? Number(p) : null;
  });

  const [baselineResults, setBaselineResults] = useState<Result[]>([]);
  const [candidateResults, setCandidateResults] = useState<Result[]>([]);
  const [loadingResults, setLoadingResults] = useState(false);

  // --- Fetch runs on mount ---
  useEffect(() => {
    let cancelled = false;
    getRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingRuns(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // --- Derived state ---
  const bothSelected = baselineRunId !== null && candidateRunId !== null;

  // --- Fetch results when both runs selected ---
  useEffect(() => {
    if (!bothSelected) return;
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Loading indicator before async fetch is intentional
    setLoadingResults(true);

    Promise.all([getRunResults(baselineRunId!), getRunResults(candidateRunId!)])
      .then(([baseData, candData]) => {
        if (!cancelled) {
          setBaselineResults(baseData);
          setCandidateResults(candData);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingResults(false);
      });

    return () => {
      cancelled = true;
      setBaselineResults([]);
      setCandidateResults([]);
    };
  }, [baselineRunId, candidateRunId, bothSelected]);

  // --- Compute diff stats ---
  const { fieldStats, commonCount, overallMatchRate, overallDivergenceRate } =
    useMemo(() => {
      // Build lookup maps by posting_id
      const baselineMap: Record<string, Result> = {};
      for (const r of baselineResults) {
        baselineMap[r.posting_id] = r;
      }
      const candidateMap: Record<string, Result> = {};
      for (const r of candidateResults) {
        candidateMap[r.posting_id] = r;
      }

      // Find common posting IDs
      const commonIds = Object.keys(baselineMap).filter(
        (id) => id in candidateMap,
      );

      // Initialize per-field counters
      const stats: Record<
        string,
        { matches: number; divergences: number; baselineOnly: number; candidateOnly: number }
      > = {};
      for (const field of COMPARE_FIELDS) {
        stats[field] = { matches: 0, divergences: 0, baselineOnly: 0, candidateOnly: 0 };
      }

      let totalMatches = 0;
      let totalDivergences = 0;

      for (const postingId of commonIds) {
        const baseResult = baselineMap[postingId];
        const candResult = candidateMap[postingId];

        let baseParsed: Record<string, unknown> = {};
        let candParsed: Record<string, unknown> = {};

        try {
          if (baseResult.parsed_result) {
            baseParsed = JSON.parse(baseResult.parsed_result);
          }
        } catch {
          // invalid JSON, treat as empty
        }
        try {
          if (candResult.parsed_result) {
            candParsed = JSON.parse(candResult.parsed_result);
          }
        } catch {
          // invalid JSON, treat as empty
        }

        for (const field of COMPARE_FIELDS) {
          const baseVal = normalizeValue(baseParsed[field]);
          const candVal = normalizeValue(candParsed[field]);

          if (baseVal === null && candVal === null) {
            // Both null — count as match
            stats[field].matches += 1;
            totalMatches += 1;
          } else if (baseVal !== null && candVal === null) {
            stats[field].baselineOnly += 1;
            totalDivergences += 1;
          } else if (baseVal === null && candVal !== null) {
            stats[field].candidateOnly += 1;
            totalDivergences += 1;
          } else if (baseVal === candVal) {
            stats[field].matches += 1;
            totalMatches += 1;
          } else {
            stats[field].divergences += 1;
            totalDivergences += 1;
          }
        }
      }

      const fieldStats: FieldDiffStats[] = COMPARE_FIELDS.map((field) => ({
        field,
        ...stats[field],
      }));

      const totalComparisons = totalMatches + totalDivergences;
      const matchRate =
        totalComparisons > 0
          ? Math.round((totalMatches / totalComparisons) * 1000) / 10
          : 0;
      const divergeRate =
        totalComparisons > 0
          ? Math.round((totalDivergences / totalComparisons) * 1000) / 10
          : 0;

      return {
        fieldStats,
        commonCount: commonIds.length,
        overallMatchRate: matchRate,
        overallDivergenceRate: divergeRate,
      };
    }, [baselineResults, candidateResults]);

  const syncRunParams = useCallback((baseId: number | null, candId: number | null) => {
    const params = new URLSearchParams(searchParams.toString());
    if (baseId !== null) params.set("baseline", String(baseId)); else params.delete("baseline");
    if (candId !== null) params.set("candidate", String(candId)); else params.delete("candidate");
    router.replace(`${pathname}?${params.toString()}`);
  }, [searchParams, router, pathname]);

  return (
    <AppShell title="Run Diff" subtitle="Field-level extraction comparison">
      {/* Run selectors */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <label
            htmlFor="baseline-select"
            className="mb-1.5 block text-[12px] font-medium text-muted-foreground"
          >
            Baseline Run
          </label>
          <select
            id="baseline-select"
            value={baselineRunId ?? ""}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : null;
              setBaselineRunId(id);
              syncRunParams(id, candidateRunId);
            }}
            disabled={loadingRuns}
            className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-[13px]"
          >
            <option value="">
              {loadingRuns ? "Loading runs\u2026" : "Select baseline run\u2026"}
            </option>
            {runs.map((run) => (
              <option key={run.id} value={run.id}>
                {formatRunLabel(run)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            htmlFor="candidate-select"
            className="mb-1.5 block text-[12px] font-medium text-muted-foreground"
          >
            Candidate Run
          </label>
          <select
            id="candidate-select"
            value={candidateRunId ?? ""}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : null;
              setCandidateRunId(id);
              syncRunParams(baselineRunId, id);
            }}
            disabled={loadingRuns}
            className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-[13px]"
          >
            <option value="">
              {loadingRuns ? "Loading runs\u2026" : "Select candidate run\u2026"}
            </option>
            {runs.map((run) => (
              <option key={run.id} value={run.id}>
                {formatRunLabel(run)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <p className="mt-3 text-[12px] text-muted-foreground/60">
        Compares extracted field values between two runs on the same corpus.
        Use this to measure how much extraction changed between prompt versions or models.
      </p>

      {/* Loading state */}
      {loadingResults && (
        <div className="mt-6 flex items-center justify-center py-16">
          <div className="animate-pulse text-[13px] text-muted-foreground">
            Loading results\u2026
          </div>
        </div>
      )}

      {/* Empty state — no runs selected */}
      {!bothSelected && !loadingResults && (
        <div className="mt-6 flex items-center justify-center py-16">
          <div className="text-[13px] text-muted-foreground">
            Select both a baseline and candidate run to compare
          </div>
        </div>
      )}

      {/* Results */}
      {bothSelected && !loadingResults && (
        <>
          {/* No common postings */}
          {commonCount === 0 ? (
            <div className="mt-6 flex items-center justify-center py-16">
              <div className="text-[13px] text-muted-foreground">
                No common postings found between the selected runs
              </div>
            </div>
          ) : (
            <>
              {/* Summary metrics */}
              <div className="mt-6 grid grid-cols-3 gap-4">
                <div className="rounded-md border border-border bg-card p-4">
                  <div className="text-[13px] text-muted-foreground">
                    Common Postings
                  </div>
                  <div className="font-mono text-2xl font-semibold tabular-nums text-foreground">
                    {commonCount}
                  </div>
                </div>
                <div className="rounded-md border border-border bg-card p-4">
                  <div className="text-[13px] text-muted-foreground">
                    Overall Match Rate
                  </div>
                  <div className="font-mono text-2xl font-semibold tabular-nums text-foreground">
                    {overallMatchRate}%
                  </div>
                </div>
                <div className="rounded-md border border-border bg-card p-4">
                  <div className="text-[13px] text-muted-foreground">
                    Divergence Rate
                  </div>
                  <div className="font-mono text-2xl font-semibold tabular-nums text-foreground">
                    {overallDivergenceRate}%
                  </div>
                </div>
              </div>

              {/* Diff table */}
              <div className="mt-6 rounded-lg border border-border bg-card p-5 shadow-sm">
                <div className="mb-4 flex items-baseline justify-between">
                  <h3 className="font-display text-[14px] font-semibold text-foreground">
                    Field-Level Comparison
                  </h3>
                </div>
                <DataTable
                  columns={columns}
                  data={fieldStats}
                  ariaLabel="Field-level comparison"
                  rowKey={(row) => row.field}
                />
              </div>
            </>
          )}
        </>
      )}

      <p className="mt-3 text-[11px] text-muted-foreground/50">
        Select different runs to compare field extraction accuracy
      </p>
    </AppShell>
  );
}

export default function PromptDiffPage() {
  return (
    <Suspense fallback={null}>
      <PromptDiffPageContent />
    </Suspense>
  );
}
