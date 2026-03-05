"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getLeaderboardDataApiV1EvalLeaderboardDataGetOptions } from "@/api-client/@tanstack/react-query.gen";
import type { EvalRun } from "@/lib/types";

interface LeaderboardResponse {
  runs: EvalRun[];
  elo: Record<string, number>;
  field_accuracy: Record<string, Record<string, number>>;
}

interface LeaderboardRow {
  rank: number;
  label: string;
  model: string;
  prompt: string;
  elo: number;
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
  if (pctStr === "\u2014") return "text-[#4F5D75]";
  const num = parseFloat(pctStr);
  if (num >= 90) return "text-[#1B998B]";
  if (num >= 70) return "text-[#A07D28]";
  return "text-[#8C2C23]";
}

function RankCell({ rank }: { rank: number }) {
  const color =
    rank === 1 ? "text-[#DCB256]" : rank === 2 ? "text-[#9EA0A5]" : rank === 3 ? "text-[#A07050]" : "text-[#4F5D75]";
  return (
    <span className={`font-mono text-[13px] ${rank <= 3 ? 'font-semibold' : ''} ${color}`}>
      #{rank}
    </span>
  );
}

export default function LeaderboardPage() {
  const [passFilter, setPassFilter] = useState<PassFilter>("all");
  const [modelFilter, setModelFilter] = useState("all");
  const [sortKey, setSortKey] = useState<keyof LeaderboardRow>("elo");
  const [sortAsc, setSortAsc] = useState(false);

  const { data: rawData, isLoading, error: queryError } = useQuery({
    ...getLeaderboardDataApiV1EvalLeaderboardDataGetOptions(),
    select: (data) => data as unknown as LeaderboardResponse,
  });

  const error = queryError instanceof Error ? queryError.message : null;

  const runs = useMemo(() => rawData?.runs ?? [], [rawData]);
  const eloRatings = useMemo(() => rawData?.elo ?? {}, [rawData]);
  const fieldAccuracyMap = useMemo(() => rawData?.field_accuracy ?? {}, [rawData]);

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
      const parseRate = bestRun.total_items > 0 ? bestRun.completed_items / bestRun.total_items : null;

      unsorted.push({
        rank: 0,
        label,
        model: bestRun.model,
        prompt: bestRun.prompt_version,
        elo,
        parseRate: parseRate !== null ? formatPct(parseRate) : "\u2014",
        accuracy: accuracyVal !== undefined ? formatPct(accuracyVal) : "\u2014",
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

  const allFieldNames = useMemo(() => {
    const fieldSet = new Set<string>();
    for (const run of filteredRuns) {
      const acc = fieldAccuracyMap[run.id];
      if (acc) Object.keys(acc).forEach((k) => fieldSet.add(k));
    }
    return [...fieldSet].sort();
  }, [filteredRuns, fieldAccuracyMap]);

  const hasFieldAccuracy = allFieldNames.length > 0;

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
        <h1 className="text-2xl font-semibold tracking-tight font-display text-[#2D3142]">
          Leaderboard
        </h1>
        <p className="mt-1 text-sm font-body text-muted-foreground">
          Model and prompt rankings by accuracy and Elo score
        </p>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <span className="font-body text-[11px] text-[#4F5D75]/60 mr-1">Pass</span>
          {(["all", 1, 2] as const).map((v) => (
            <button
              key={String(v)}
              onClick={() => setPassFilter(v)}
              className={`rounded px-2 py-1 font-body text-xs font-medium transition-colors duration-150 ${
                passFilter === v ? 'bg-[#EF8354] text-white' : 'bg-[#E8E8E4] text-[#4F5D75]'
              }`}
            >
              {v === "all" ? "All" : `Pass ${v}`}
            </button>
          ))}
        </div>
        {modelOptions.length > 2 && (
          <div className="flex items-center gap-1">
            <span className="font-body text-[11px] text-[#4F5D75]/60 mr-1">Model</span>
            {modelOptions.map((m) => (
              <button
                key={m}
                onClick={() => setModelFilter(m)}
                className={`rounded px-2 py-1 font-body text-xs font-medium transition-colors duration-150 ${
                  modelFilter === m ? 'bg-[#EF8354] text-white' : 'bg-[#E8E8E4] text-[#4F5D75]'
                }`}
              >
                {m === "all" ? "All" : m}
              </button>
            ))}
          </div>
        )}
        <span className="ml-auto font-body text-[11px] text-[#4F5D75]/60">
          {filteredRuns.length} of {runs.length} runs
        </span>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-[#8C2C2333] px-4 py-3 bg-[#8C2C231A] text-[#8C2C23] font-body text-[13px]" role="alert">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-16 font-body text-[13px] text-[#4F5D75]">
          Loading leaderboard data\u2026
        </div>
      ) : (
        <>
          <div className="rounded-lg border border-[#BFC0C0] bg-white shadow-sm overflow-hidden">
            <div className="border-b border-[#BFC0C0] px-5 py-4">
              <h3 className="font-semibold font-display text-sm text-[#2D3142]">
                Elo Rankings
              </h3>
            </div>
            {leaderboardRows.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full" aria-label="Elo rankings">
                  <thead>
                    <tr className="border-b border-[#BFC0C0] bg-[#E8E8E41A]">
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
                          className={`pb-3 pl-5 pt-4 pr-4 text-left last:text-right font-body text-[11px] font-semibold uppercase tracking-wider cursor-pointer select-none transition-colors ${
                            sortKey === key ? 'text-[#EF8354]' : 'text-[#4F5D75]'
                          }`}
                        >
                          {label}
                          {sortKey === key && (
                            <span className="ml-1">{sortAsc ? "\u2191" : "\u2193"}</span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#BFC0C0]">
                    {leaderboardRows.map((row) => (
                      <tr key={row.label} className="hover:bg-[#E8E8E40D]">
                        <td className="py-3 pl-5 pr-4">
                          <RankCell rank={row.rank} />
                        </td>
                        <td className="py-3 pr-4 font-body text-[13px] font-medium text-[#2D3142]">
                          {row.model}
                        </td>
                        <td className="py-3 pr-4 font-body text-xs text-[#4F5D75]">
                          {row.prompt}
                        </td>
                        <td className="py-3 pr-4 font-mono text-[13px] font-semibold text-[#2D3142]">
                          {row.elo}
                        </td>
                        <td className="py-3 pr-4 font-mono text-xs text-[#4F5D75]">
                          {row.parseRate}
                        </td>
                        <td className={`py-3 pl-4 pr-5 text-right font-mono text-xs font-semibold ${accuracyTextColor(row.accuracy)}`}>
                          {row.accuracy}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="px-5 py-8 font-body text-[13px] text-[#4F5D75]">
                No runs match the current filters.
              </p>
            )}
          </div>

          {hasFieldAccuracy && (
            <div className="mt-6 rounded-lg border border-[#BFC0C0] bg-white shadow-sm overflow-hidden">
              <div className="border-b border-[#BFC0C0] px-5 py-4">
                <h3 className="font-semibold font-display text-sm text-[#2D3142]">
                  Field-Level Accuracy
                </h3>
                <p className="font-body text-xs text-[#4F5D75]/50 mt-0.5">
                  Accuracy per field based on human reviews
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full" aria-label="Field-level accuracy">
                  <thead>
                    <tr className="border-b border-[#BFC0C0] bg-[#E8E8E41A]">
                      <th className="pb-3 pl-5 pt-4 pr-4 text-left font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider">
                        Model
                      </th>
                      {allFieldNames.map((field) => (
                        <th key={field} className="pb-3 pt-4 pr-4 text-center font-body text-[11px] font-semibold text-[#4F5D75] uppercase tracking-wider">
                          {field}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#BFC0C0]">
                    {filteredRuns.map((run) => {
                      const fieldAcc = fieldAccuracyMap[run.id];
                      if (!fieldAcc) return null;
                      return (
                        <tr key={run.id} className="hover:bg-[#E8E8E40D]">
                          <td className="py-2.5 pl-5 pr-4 font-body text-xs font-medium text-[#2D3142]">
                            {run.model}/{run.prompt_version}
                          </td>
                          {allFieldNames.map((field) => {
                            const val = fieldAcc[field];
                            if (val === undefined) {
                              return (
                                <td key={field} className="py-2.5 pr-4 text-center font-mono text-[11px] text-[#4F5D75]/50">
                                  &mdash;
                                </td>
                              );
                            }
                            const pctStr = formatPct(val);
                            return (
                              <td
                                key={field}
                                className={`py-2.5 pr-4 text-center font-mono text-[11px] ${
                                  parseFloat(pctStr) >= 90 ? 'font-bold' : ''
                                } ${accuracyTextColor(pctStr)}`}
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
            <Link href="/eval/review" className="font-body text-xs text-[#EF8354] hover:underline">
              Compare runs to improve Elo data &#x2192;
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
