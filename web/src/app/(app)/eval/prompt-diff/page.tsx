"use client";

import { Suspense, useMemo, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getRunsApiV1EvalRunsGetOptions, getRunResultsApiV1EvalRunsRunIdResultsGetOptions } from "@/api-client/@tanstack/react-query.gen";
import type { EvalRun, EvalResult } from "@/lib/types";
import {
  EVAL_FIELDS as COMPARE_FIELDS,
  formatRunLabel,
  getParsedResult,
} from "@/lib/eval-utils";

interface FieldDiffStats {
  field: string;
  matches: number;
  divergences: number;
  baselineOnly: number;
  candidateOnly: number;
}

function normalizeValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value))
    return value.length === 0 ? null : JSON.stringify([...value].sort());
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function matchPctColor(pct: number): string {
  if (pct >= 90) return "text-[#1B998B]";
  if (pct >= 70) return "text-[#A07D28]";
  return "text-[#8C2C23]";
}

function PromptDiffContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const baselineRunId = searchParams.get("baseline");
  const candidateRunId = searchParams.get("candidate");

  const { data: runs = [], isLoading: loadingRuns } = useQuery({
    ...getRunsApiV1EvalRunsGetOptions(),
    select: (data) => data as unknown as EvalRun[],
  });

  const { data: baselineResults = [], isLoading: loadingBaseline } = useQuery({
    ...getRunResultsApiV1EvalRunsRunIdResultsGetOptions({ 
      path: { run_id: baselineRunId! },
    }),
    enabled: !!baselineRunId,
    select: (data) => data as unknown as EvalResult[],
  });

  const { data: candidateResults = [], isLoading: loadingCandidate } = useQuery({
    ...getRunResultsApiV1EvalRunsRunIdResultsGetOptions({ 
      path: { run_id: candidateRunId! },
    }),
    enabled: !!candidateRunId,
    select: (data) => data as unknown as EvalResult[],
  });

  const loadingResults = loadingBaseline || loadingCandidate;
  const bothSelected = !!baselineRunId && !!candidateRunId;

  const { fieldStats, commonCount, overallMatchRate, overallDivergenceRate } =
    useMemo(() => {
      const baselineMap: Record<string, EvalResult> = {};
      for (const r of baselineResults) baselineMap[r.posting_id] = r;
      const candidateMap: Record<string, EvalResult> = {};
      for (const r of candidateResults) candidateMap[r.posting_id] = r;

      const commonIds = Object.keys(baselineMap).filter(
        (id) => id in candidateMap,
      );

      const stats: Record<
        string,
        {
          matches: number;
          divergences: number;
          baselineOnly: number;
          candidateOnly: number;
        }
      > = {};
      for (const field of COMPARE_FIELDS) {
        stats[field] = {
          matches: 0,
          divergences: 0,
          baselineOnly: 0,
          candidateOnly: 0,
        };
      }

      let totalMatches = 0;
      let totalDivergences = 0;

      for (const postingId of commonIds) {
        const baseResult = baselineMap[postingId];
        const candResult = candidateMap[postingId];
        const baseParsed = getParsedResult(baseResult);
        const candParsed = getParsedResult(candResult);

        for (const field of COMPARE_FIELDS) {
          const baseVal = normalizeValue(baseParsed[field]);
          const candVal = normalizeValue(candParsed[field]);

          if (baseVal === null && candVal === null) {
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

  const syncRunParams = useCallback(
    (baseId: string | null, candId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (baseId) params.set("baseline", baseId);
      else params.delete("baseline");
      if (candId) params.set("candidate", candId);
      else params.delete("candidate");
      router.replace(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname],
  );

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight font-display text-[#2D3142]">
          Run Diff
        </h1>
        <p className="mt-1 text-sm font-body text-muted-foreground">
          Field-level extraction comparison between two runs
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {(
          [
            {
              id: "baseline-select",
              label: "Baseline Run",
              value: baselineRunId,
              onChange: (id: string | null) => syncRunParams(id, candidateRunId),
            },
            {
              id: "candidate-select",
              label: "Candidate Run",
              value: candidateRunId,
              onChange: (id: string | null) => syncRunParams(baselineRunId, id),
            },
          ] as const
        ).map((sel) => (
          <div key={sel.id}>
            <label
              htmlFor={sel.id}
              className="mb-1.5 block font-body text-xs font-medium text-[#4F5D75]"
            >
              {sel.label}
            </label>
            <select
              id={sel.id}
              value={sel.value ?? ""}
              onChange={(e) => sel.onChange(e.target.value || null)}
              disabled={loadingRuns}
              className="w-full rounded border border-[#BFC0C0] px-2 py-1.5 bg-white font-body text-[13px] text-[#2D3142]"
            >
              <option value="">
                {loadingRuns
                  ? "Loading runs\u2026"
                  : `Select ${sel.label.toLowerCase()}\u2026`}
              </option>
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {formatRunLabel(run)}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      <p className="mt-3 font-body text-xs text-[#4F5D75]/60">
        Compares extracted field values between two runs on the same corpus.
        Use this to measure how much extraction changed between prompt versions or models.
      </p>

      {loadingResults && (
        <div className="mt-6 flex items-center justify-center py-16 font-body text-[13px] text-[#4F5D75]">
          Loading results\u2026
        </div>
      )}

      {!bothSelected && !loadingResults && (
        <div className="mt-6 flex items-center justify-center py-16 font-body text-[13px] text-[#4F5D75]">
          Select both a baseline and candidate run to compare.
        </div>
      )}

      {bothSelected && !loadingResults && (
        <>
          {commonCount === 0 ? (
            <div className="mt-6 flex items-center justify-center py-16 font-body text-[13px] text-[#4F5D75]">
              No common postings found between the selected runs.
            </div>
          ) : (
            <>
              {/* Summary metrics */}
              <div className="mt-6 grid grid-cols-3 gap-4">
                {[
                  { label: "Common Postings", value: String(commonCount) },
                  { label: "Match Rate", value: `${overallMatchRate}%` },
                  {
                    label: "Divergence Rate",
                    value: `${overallDivergenceRate}%`,
                  },
                ].map(({ label, value }) => (
                  <div
                    key={label}
                    className="rounded-lg border border-[#BFC0C0] p-4 bg-white shadow-sm"
                  >
                    <p className="font-body text-xs text-[#4F5D75] mb-1">
                      {label}
                    </p>
                    <p className="font-mono text-2xl font-semibold text-[#2D3142] leading-none">
                      {value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Diff table */}
              <div className="mt-6 rounded-lg border border-[#BFC0C0] bg-white shadow-sm overflow-hidden">
                <div className="border-b border-[#BFC0C0] px-5 py-4">
                  <h3 className="font-semibold font-display text-sm text-[#2D3142]">
                    Field-Level Comparison
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full" aria-label="Field-level comparison">
                    <thead>
                      <tr className="border-b border-[#BFC0C0] bg-[#E8E8E41A]">
                        {["Field", "Matches", "Divergences", "Match%"].map(
                          (h) => (
                            <th
                              key={h}
                              className="pb-3 pl-5 pt-4 pr-4 text-left last:text-right font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider"
                            >
                              {h}
                            </th>
                          ),
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#BFC0C0]">
                      {fieldStats.map((row) => {
                        const total =
                          row.matches +
                          row.divergences +
                          row.baselineOnly +
                          row.candidateOnly;
                        const pct =
                          total > 0
                            ? Math.round((row.matches / total) * 100)
                            : null;

                        return (
                          <tr key={row.field} className="hover:bg-[#E8E8E40D]">
                            <td className="py-2.5 pl-5 pr-4 font-body text-xs text-[#4F5D75]">
                              {row.field}
                            </td>
                            <td className="py-2.5 pr-4 font-mono text-xs text-[#2D3142]">
                              <span className="mr-1.5 inline-block size-1.5 rounded-full bg-[#1B998B]" />
                              {row.matches}
                            </td>
                            <td className="py-2.5 pr-4 font-mono text-xs text-[#2D3142]">
                              <span className="mr-1.5 inline-block size-1.5 rounded-full bg-[#8C2C23]" />
                              {row.divergences}
                            </td>
                            <td className={`py-2.5 pl-4 pr-5 text-right font-mono text-xs font-semibold ${pct !== null ? matchPctColor(pct) : "text-[#4F5D75]"}`}>
                              {pct !== null ? `${pct}%` : "\u2014"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </>
      )}

      <p className="mt-3 font-body text-[11px] text-[#4F5D75]/50">
        Select different runs to compare field extraction accuracy.
      </p>
    </div>
  );
}

export default function PromptDiffPage() {
  return (
    <Suspense fallback={<div className="p-6 font-body text-[#4F5D75]">Loading&hellip;</div>}>
      <PromptDiffContent />
    </Suspense>
  );
}
