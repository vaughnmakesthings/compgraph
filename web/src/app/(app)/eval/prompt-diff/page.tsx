"use client";

import { Suspense, useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api-client";
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
  if (pct >= 90) return "#1B998B";
  if (pct >= 70) return "#A07D28";
  return "#8C2C23";
}

function PromptDiffContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);

  const [baselineRunId, setBaselineRunId] = useState<string | null>(
    () => searchParams.get("baseline"),
  );
  const [candidateRunId, setCandidateRunId] = useState<string | null>(
    () => searchParams.get("candidate"),
  );

  const [baselineResults, setBaselineResults] = useState<EvalResult[]>([]);
  const [candidateResults, setCandidateResults] = useState<EvalResult[]>([]);
  const [loadingResults, setLoadingResults] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .listEvalRuns()
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

  const bothSelected = baselineRunId !== null && candidateRunId !== null;

  useEffect(() => {
    if (!bothSelected) return;
    let cancelled = false;

    async function fetchResults() {
      setLoadingResults(true);
      try {
        const [baseData, candData] = await Promise.all([
          api.getEvalResults(baselineRunId!),
          api.getEvalResults(candidateRunId!),
        ]);
        if (cancelled) return;
        setBaselineResults(baseData);
        setCandidateResults(candData);
      } catch {
        // ignore — results stay empty
      } finally {
        if (!cancelled) setLoadingResults(false);
      }
    }

    void fetchResults();

    return () => {
      cancelled = true;
      setBaselineResults([]);
      setCandidateResults([]);
    };
  }, [baselineRunId, candidateRunId, bothSelected]);

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

  const selectorBaseStyle = {
    borderColor: "#BFC0C0",
    backgroundColor: "#FFFFFF",
    fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
    fontSize: "13px",
    color: "#2D3142",
    borderRadius: "var(--radius-sm, 4px)",
  };

  const cardStyle = {
    backgroundColor: "#FFFFFF",
    borderColor: "#BFC0C0",
    boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
    borderRadius: "var(--radius-lg, 8px)",
  };

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
          }}
        >
          Run Diff
        </h1>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground, #4F5D75)",
          }}
        >
          Field-level extraction comparison between two runs
        </p>
      </div>

      {/* Run selectors */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {(
          [
            {
              id: "baseline-select",
              label: "Baseline Run",
              value: baselineRunId,
              onChange: (id: string | null) => {
                setBaselineRunId(id);
                syncRunParams(id, candidateRunId);
              },
            },
            {
              id: "candidate-select",
              label: "Candidate Run",
              value: candidateRunId,
              onChange: (id: string | null) => {
                setCandidateRunId(id);
                syncRunParams(baselineRunId, id);
              },
            },
          ] as const
        ).map((sel) => (
          <div key={sel.id}>
            <label
              htmlFor={sel.id}
              className="mb-1.5 block"
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "12px",
                fontWeight: 500,
                color: "#4F5D75",
              }}
            >
              {sel.label}
            </label>
            <select
              id={sel.id}
              value={sel.value ?? ""}
              onChange={(e) => sel.onChange(e.target.value || null)}
              disabled={loadingRuns}
              className="w-full rounded border px-2 py-1.5"
              style={selectorBaseStyle}
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

      <p
        className="mt-3"
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          fontSize: "12px",
          color: "#4F5D7560",
        }}
      >
        Compares extracted field values between two runs on the same corpus.
        Use this to measure how much extraction changed between prompt versions or models.
      </p>

      {loadingResults && (
        <div
          className="mt-6 flex items-center justify-center py-16"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#4F5D75",
          }}
        >
          Loading results\u2026
        </div>
      )}

      {!bothSelected && !loadingResults && (
        <div
          className="mt-6 flex items-center justify-center py-16"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#4F5D75",
          }}
        >
          Select both a baseline and candidate run to compare.
        </div>
      )}

      {bothSelected && !loadingResults && (
        <>
          {commonCount === 0 ? (
            <div
              className="mt-6 flex items-center justify-center py-16"
              style={{
                fontFamily:
                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "13px",
                color: "#4F5D75",
              }}
            >
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
                    className="rounded-lg border p-4"
                    style={cardStyle}
                  >
                    <p
                      style={{
                        fontFamily:
                          "var(--font-body, 'DM Sans Variable', sans-serif)",
                        fontSize: "12px",
                        color: "#4F5D75",
                        marginBottom: "4px",
                      }}
                    >
                      {label}
                    </p>
                    <p
                      style={{
                        fontFamily:
                          "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                        fontSize: "24px",
                        fontWeight: 600,
                        color: "#2D3142",
                        lineHeight: 1,
                      }}
                    >
                      {value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Diff table */}
              <div
                className="mt-6 rounded-lg border"
                style={cardStyle}
              >
                <div className="border-b border-[#BFC0C0] px-5 py-4">
                  <h3
                    className="font-semibold"
                    style={{
                      fontFamily:
                        "var(--font-display, 'Sora Variable', sans-serif)",
                      fontSize: "14px",
                      color: "#2D3142",
                    }}
                  >
                    Field-Level Comparison
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table
                    className="w-full"
                    aria-label="Field-level comparison"
                  >
                    <thead>
                      <tr className="border-b border-[#BFC0C0]">
                        {["Field", "Matches", "Divergences", "Match%"].map(
                          (h) => (
                            <th
                              key={h}
                              className="pb-3 pl-5 pt-4 pr-4 text-left last:text-right"
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
                          <tr
                            key={row.field}
                            className="border-b border-[#BFC0C0] last:border-0"
                          >
                            <td
                              className="py-2.5 pl-5 pr-4"
                              style={{
                                fontFamily:
                                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                                fontSize: "12px",
                                color: "#4F5D75",
                              }}
                            >
                              {row.field}
                            </td>
                            <td
                              className="py-2.5 pr-4"
                              style={{
                                fontFamily:
                                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                fontSize: "12px",
                                color: "#2D3142",
                              }}
                            >
                              <span
                                className="mr-1.5 inline-block size-1.5 rounded-full"
                                style={{ backgroundColor: "#1B998B" }}
                              />
                              {row.matches}
                            </td>
                            <td
                              className="py-2.5 pr-4"
                              style={{
                                fontFamily:
                                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                fontSize: "12px",
                                color: "#2D3142",
                              }}
                            >
                              <span
                                className="mr-1.5 inline-block size-1.5 rounded-full"
                                style={{ backgroundColor: "#8C2C23" }}
                              />
                              {row.divergences}
                            </td>
                            <td
                              className="py-2.5 pl-4 pr-5 text-right"
                              style={{
                                fontFamily:
                                  "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                fontSize: "12px",
                                fontWeight: 600,
                                color:
                                  pct !== null
                                    ? matchPctColor(pct)
                                    : "#4F5D75",
                              }}
                            >
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

      <p
        className="mt-3"
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          fontSize: "11px",
          color: "#4F5D7550",
        }}
      >
        Select different runs to compare field extraction accuracy.
      </p>
    </div>
  );
}

export default function PromptDiffPage() {
  return (
    <Suspense fallback={<div style={{ padding: "24px", color: "#4F5D75" }}>Loading&hellip;</div>}>
      <PromptDiffContent />
    </Suspense>
  );
}
