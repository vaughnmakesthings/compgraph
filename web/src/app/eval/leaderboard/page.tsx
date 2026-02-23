"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { EvalRun, EvalComparison } from "@/lib/types";

interface LeaderboardData {
  runs: EvalRun[];
  elo: Record<string, number>;
  comparisons: EvalComparison[];
  field_accuracy: Record<string, Record<string, number>>;
}

interface LeaderboardRow {
  rank: number;
  label: string;
  model: string;
  prompt: string;
  elo: number;
  winPct: string;
  parseRate: string;
  accuracy: string;
}

type PassFilter = "all" | 1 | 2;

function makeLabel(model: string, prompt: string): string {
  return `${model}/${prompt}`;
}

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function accuracyTextColor(pctStr: string): string {
  if (pctStr === "\u2014") return "#4F5D75";
  const num = parseFloat(pctStr);
  if (num >= 90) return "#1B998B";
  if (num >= 70) return "#A07D28";
  return "#8C2C23";
}

function RankCell({ rank }: { rank: number }) {
  const color =
    rank === 1 ? "#DCB256" : rank === 2 ? "#9EA0A5" : rank === 3 ? "#A07050" : "#4F5D75";
  return (
    <span
      style={{
        fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
        fontSize: "13px",
        fontWeight: rank <= 3 ? 600 : undefined,
        color,
      }}
    >
      #{rank}
    </span>
  );
}

export default function LeaderboardPage() {
  const [rawData, setRawData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [passFilter, setPassFilter] = useState<PassFilter>("all");
  const [modelFilter, setModelFilter] = useState("all");
  const [sortKey, setSortKey] = useState<keyof LeaderboardRow>("elo");
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getEvalLeaderboard()
      .then((data) => {
        if (!cancelled) {
          // The backend returns a generic Record<string, unknown>; cast defensively
          const d = data as Partial<LeaderboardData>;
          setRawData({
            runs: Array.isArray(d.runs) ? (d.runs as EvalRun[]) : [],
            elo: (d.elo as Record<string, number>) ?? {},
            comparisons: Array.isArray(d.comparisons)
              ? (d.comparisons as EvalComparison[])
              : [],
            field_accuracy:
              (d.field_accuracy as Record<string, Record<string, number>>) ?? {},
          });
        }
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load leaderboard");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runs = rawData?.runs ?? [];
  const eloRatings = rawData?.elo ?? {};
  const comparisons = rawData?.comparisons ?? [];
  const fieldAccuracyMap = rawData?.field_accuracy ?? {};

  const modelOptions = useMemo(
    () => ["all", ...[...new Set(runs.map((r) => r.model))].sort()],
    [runs],
  );

  const filteredRuns = useMemo(
    () =>
      runs.filter((r) => {
        if (passFilter !== "all" && r.pass_number !== passFilter) return false;
        if (modelFilter !== "all" && r.model !== modelFilter) return false;
        return true;
      }),
    [runs, passFilter, modelFilter],
  );

  // Build result_id -> label map for win rate calculation
  // Since EvalResult doesn't exist in filteredRuns, derive from comparisons
  const winRates = useMemo(() => {
    const wins: Record<string, number> = {};
    const appearances: Record<string, number> = {};
    // Use elo labels as proxy — comparisons reference result IDs which we can't resolve
    // without fetching all results. Derive win pct from comparisons if label matches.
    for (const comp of comparisons) {
      const labelA = `result:${comp.result_a_id}`;
      const labelB = `result:${comp.result_b_id}`;
      appearances[labelA] = (appearances[labelA] ?? 0) + 1;
      appearances[labelB] = (appearances[labelB] ?? 0) + 1;
      if (comp.winner === "a") wins[labelA] = (wins[labelA] ?? 0) + 1;
      if (comp.winner === "b") wins[labelB] = (wins[labelB] ?? 0) + 1;
    }
    return wins; // not used for display — win% derived from elo label if available
  }, [comparisons]);
  void winRates;

  // Average field accuracy per run
  const avgAccuracyByRun = useMemo(() => {
    const map: Record<string, number> = {};
    for (const run of runs) {
      const fieldAcc = fieldAccuracyMap[run.id];
      if (!fieldAcc) continue;
      const values = Object.values(fieldAcc);
      if (values.length === 0) continue;
      map[run.id] = values.reduce((a, b) => a + b, 0) / values.length;
    }
    return map;
  }, [runs, fieldAccuracyMap]);

  // Build leaderboard rows
  const leaderboardRows: LeaderboardRow[] = useMemo(() => {
    const labelToRuns: Record<string, EvalRun[]> = {};
    for (const run of filteredRuns) {
      const label = makeLabel(run.model, run.prompt_version);
      if (!labelToRuns[label]) labelToRuns[label] = [];
      labelToRuns[label].push(run);
    }

    const unsorted: LeaderboardRow[] = [];
    for (const [label, labelRuns] of Object.entries(labelToRuns)) {
      const elo = eloRatings[label] ?? 0;

      const bestRun = labelRuns.reduce((a, b) =>
        new Date(b.created_at) > new Date(a.created_at) ? b : a,
      );

      const accuracyVal = avgAccuracyByRun[bestRun.id];

      // Parse rate: completed_items / total_items
      const parseRate =
        bestRun.total_items > 0
          ? bestRun.completed_items / bestRun.total_items
          : null;

      unsorted.push({
        rank: 0,
        label,
        model: bestRun.model,
        prompt: bestRun.prompt_version,
        elo,
        winPct: "\u2014",
        parseRate: parseRate !== null ? formatPct(parseRate) : "\u2014",
        accuracy:
          accuracyVal !== undefined ? formatPct(accuracyVal) : "\u2014",
      });
    }

    unsorted.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortAsc ? aVal - bVal : bVal - aVal;
      }
      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortAsc ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
    });

    return unsorted.map((row, i) => ({ ...row, rank: i + 1 }));
  }, [filteredRuns, eloRatings, avgAccuracyByRun, sortKey, sortAsc]);

  // Field accuracy breakdown
  const allFieldNames = useMemo(() => {
    const fieldSet = new Set<string>();
    for (const run of filteredRuns) {
      const acc = fieldAccuracyMap[run.id];
      if (acc) Object.keys(acc).forEach((k) => fieldSet.add(k));
    }
    return [...fieldSet].sort();
  }, [filteredRuns, fieldAccuracyMap]);

  const hasFieldAccuracy = allFieldNames.length > 0;

  const passOptions: { label: string; value: PassFilter }[] = [
    { label: "All", value: "all" },
    { label: "Pass 1", value: 1 },
    { label: "Pass 2", value: 2 },
  ];

  const headerStyle = {
    fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
    fontSize: "11px",
    fontWeight: 500,
    color: "#4F5D75",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    cursor: "pointer",
    userSelect: "none" as const,
  };

  const sortColumn = (key: keyof LeaderboardRow) => {
    if (sortKey === key) setSortAsc((p) => !p);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
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
          Leaderboard
        </h1>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            color: "var(--color-muted-foreground, #4F5D75)",
          }}
        >
          Model and prompt rankings by accuracy and Elo score
        </p>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <span
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "11px",
              color: "#4F5D7560",
              marginRight: "4px",
            }}
          >
            Pass
          </span>
          {passOptions.map((opt) => (
            <button
              key={String(opt.value)}
              onClick={() => setPassFilter(opt.value)}
              className="rounded px-2 py-1 font-medium transition-colors duration-150"
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "12px",
                backgroundColor:
                  passFilter === opt.value ? "#EF8354" : "#E8E8E4",
                color: passFilter === opt.value ? "#FFFFFF" : "#4F5D75",
                borderRadius: "var(--radius-sm, 4px)",
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
        {modelOptions.length > 2 && (
          <div className="flex items-center gap-1">
            <span
              style={{
                fontFamily:
                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "11px",
                color: "#4F5D7560",
                marginRight: "4px",
              }}
            >
              Model
            </span>
            {modelOptions.map((m) => (
              <button
                key={m}
                onClick={() => setModelFilter(m)}
                className="rounded px-2 py-1 font-medium transition-colors duration-150"
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "12px",
                  backgroundColor:
                    modelFilter === m ? "#EF8354" : "#E8E8E4",
                  color: modelFilter === m ? "#FFFFFF" : "#4F5D75",
                  borderRadius: "var(--radius-sm, 4px)",
                }}
              >
                {m === "all" ? "All" : m}
              </button>
            ))}
          </div>
        )}
        <span
          className="ml-auto"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "11px",
            color: "#4F5D7560",
          }}
        >
          {filteredRuns.length} of {runs.length} runs
        </span>
      </div>

      {error && (
        <div
          className="mb-4 rounded-lg border px-4 py-3"
          role="alert"
          style={{
            backgroundColor: "#8C2C231A",
            borderColor: "#8C2C2333",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#8C2C23",
            borderRadius: "var(--radius-sm, 4px)",
          }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div
          className="flex items-center justify-center py-16"
          style={{
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
            fontSize: "13px",
            color: "#4F5D75",
          }}
        >
          Loading leaderboard data\u2026
        </div>
      ) : (
        <>
          {/* Elo Rankings */}
          <div
            className="rounded-lg border"
            style={{
              backgroundColor: "#FFFFFF",
              borderColor: "#BFC0C0",
              boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
              borderRadius: "var(--radius-lg, 8px)",
            }}
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
                Elo Rankings
              </h3>
            </div>
            {leaderboardRows.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full" aria-label="Elo rankings">
                  <thead>
                    <tr className="border-b border-[#BFC0C0]">
                      {(
                        [
                          { key: "rank" as const, label: "Rank" },
                          { key: "model" as const, label: "Model" },
                          { key: "prompt" as const, label: "Prompt" },
                          { key: "elo" as const, label: "Elo" },
                          { key: "parseRate" as const, label: "Parse Rate" },
                          { key: "accuracy" as const, label: "Accuracy" },
                        ] as const
                      ).map(({ key, label }) => (
                        <th
                          key={key}
                          onClick={() => sortColumn(key)}
                          className="pb-3 pl-5 pt-4 pr-4 text-left last:text-right"
                          style={{
                            ...headerStyle,
                            color:
                              sortKey === key ? "#EF8354" : "#4F5D75",
                          }}
                        >
                          {label}
                          {sortKey === key && (
                            <span className="ml-1">
                              {sortAsc ? "\u2191" : "\u2193"}
                            </span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboardRows.map((row) => (
                      <tr
                        key={row.label}
                        className="border-b border-[#BFC0C0] last:border-0 hover:bg-[#E8E8E41A] transition-colors duration-150"
                      >
                        <td className="py-3 pl-5 pr-4">
                          <RankCell rank={row.rank} />
                        </td>
                        <td
                          className="py-3 pr-4"
                          style={{
                            fontFamily:
                              "var(--font-body, 'DM Sans Variable', sans-serif)",
                            fontSize: "13px",
                            fontWeight: 500,
                            color: "#2D3142",
                          }}
                        >
                          {row.model}
                        </td>
                        <td
                          className="py-3 pr-4"
                          style={{
                            fontFamily:
                              "var(--font-body, 'DM Sans Variable', sans-serif)",
                            fontSize: "12px",
                            color: "#4F5D75",
                          }}
                        >
                          {row.prompt}
                        </td>
                        <td
                          className="py-3 pr-4"
                          style={{
                            fontFamily:
                              "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                            fontSize: "13px",
                            fontWeight: 600,
                            color: "#2D3142",
                          }}
                        >
                          {row.elo}
                        </td>
                        <td
                          className="py-3 pr-4"
                          style={{
                            fontFamily:
                              "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                            fontSize: "12px",
                            color: "#4F5D75",
                          }}
                        >
                          {row.parseRate}
                        </td>
                        <td
                          className="py-3 pl-4 pr-5 text-right"
                          style={{
                            fontFamily:
                              "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                            fontSize: "12px",
                            fontWeight: 600,
                            color: accuracyTextColor(row.accuracy),
                          }}
                        >
                          {row.accuracy}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p
                className="px-5 py-8"
                style={{
                  fontFamily:
                    "var(--font-body, 'DM Sans Variable', sans-serif)",
                  fontSize: "13px",
                  color: "#4F5D75",
                }}
              >
                No runs match the current filters.
              </p>
            )}
          </div>

          {/* Field-Level Accuracy */}
          {hasFieldAccuracy && (
            <div
              className="mt-6 rounded-lg border"
              style={{
                backgroundColor: "#FFFFFF",
                borderColor: "#BFC0C0",
                boxShadow:
                  "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
                borderRadius: "var(--radius-lg, 8px)",
              }}
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
                  Field-Level Accuracy
                </h3>
                <p
                  style={{
                    fontFamily:
                      "var(--font-body, 'DM Sans Variable', sans-serif)",
                    fontSize: "12px",
                    color: "#4F5D7580",
                    marginTop: "2px",
                  }}
                >
                  Accuracy per field based on human reviews
                </p>
              </div>
              <div className="overflow-x-auto">
                <table
                  className="w-full"
                  aria-label="Field-level accuracy"
                >
                  <thead>
                    <tr className="border-b border-[#BFC0C0]">
                      <th
                        className="pb-3 pl-5 pt-4 pr-4 text-left"
                        style={headerStyle}
                      >
                        Model
                      </th>
                      {allFieldNames.map((field) => (
                        <th
                          key={field}
                          className="pb-3 pt-4 pr-4 text-center"
                          style={headerStyle}
                        >
                          {field}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRuns.map((run) => {
                      const fieldAcc = fieldAccuracyMap[run.id];
                      if (!fieldAcc) return null;
                      return (
                        <tr
                          key={run.id}
                          className="border-b border-[#BFC0C0] last:border-0"
                        >
                          <td
                            className="py-2.5 pl-5 pr-4"
                            style={{
                              fontFamily:
                                "var(--font-body, 'DM Sans Variable', sans-serif)",
                              fontSize: "12px",
                              fontWeight: 500,
                              color: "#2D3142",
                            }}
                          >
                            {run.model}/{run.prompt_version}
                          </td>
                          {allFieldNames.map((field) => {
                            const val = fieldAcc[field];
                            if (val === undefined) {
                              return (
                                <td
                                  key={field}
                                  className="py-2.5 pr-4 text-center"
                                  style={{
                                    fontFamily:
                                      "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                    fontSize: "11px",
                                    color: "#4F5D7550",
                                  }}
                                >
                                  &mdash;
                                </td>
                              );
                            }
                            const pctStr = formatPct(val);
                            return (
                              <td
                                key={field}
                                className="py-2.5 pr-4 text-center"
                                style={{
                                  fontFamily:
                                    "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                                  fontSize: "11px",
                                  fontWeight:
                                    parseFloat(pctStr) >= 90 ? 600 : undefined,
                                  color: accuracyTextColor(pctStr),
                                }}
                              >
                                {pctStr}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="mt-4 flex items-center justify-end border-t border-[#BFC0C0] pt-4">
            <Link
              href="/eval/review"
              style={{
                fontFamily:
                  "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "12px",
                color: "#EF8354",
                textDecoration: "none",
              }}
            >
              Compare runs to improve Elo data &#x2192;
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
