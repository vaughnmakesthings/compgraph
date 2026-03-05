"use client";

import { Suspense, useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getRunsApiV1EvalRunsGetOptions,
  getRunResultsApiV1EvalRunsRunIdResultsGetOptions,
  getCorpusApiV1EvalCorpusGetOptions,
  getComparisonsApiV1EvalComparisonsGetOptions,
  getComparisonsApiV1EvalComparisonsGetQueryKey,
  createComparisonApiV1EvalComparisonsPostMutation
} from "@/api-client/@tanstack/react-query.gen";
import type { EvalRun, EvalResult, EvalComparison, PostingListItem } from "@/lib/types";
import {
  EVAL_FIELDS as PASS1_FIELDS,
  formatFieldValue,
  formatRunLabel,
  getParsedResult,
} from "@/lib/eval-utils";

type VoteWinner = "a" | "b" | "tie" | "both_bad";

const VOTE_BUTTONS: { label: string; value: VoteWinner }[] = [
  { label: "A is Better", value: "a" },
  { label: "B is Better", value: "b" },
  { label: "Tie", value: "tie" },
  { label: "Both Bad", value: "both_bad" },
];

const VOTE_KEY_MAP: Record<string, VoteWinner> = {
  a: "a",
  b: "b",
  t: "tie",
  x: "both_bad",
};

function FieldComparisonPanel({
  label,
  fields,
  otherFields,
}: {
  label: string;
  fields: Record<string, unknown>;
  otherFields: Record<string, unknown>;
}) {
  return (
    <div className="rounded-lg border border-[#BFC0C0] bg-white shadow-sm">
      <div className="border-b border-[#BFC0C0] px-5 py-3">
        <h3 className="font-semibold font-display text-sm text-[#2D3142]">
          {label}
        </h3>
      </div>
      <div className="p-1">
        {PASS1_FIELDS.map((field) => {
          const val = formatFieldValue(fields[field]);
          const otherVal = formatFieldValue(otherFields[field]);
          const disagree = val !== otherVal;
          return (
            <div
              key={field}
              className="flex items-baseline justify-between border-b border-[#BFC0C04D] px-4 py-2 last:border-0"
            >
              <span className={`font-body text-xs ${disagree ? 'font-medium text-[#A07D28]' : 'text-[#4F5D75]'}`}>
                {field}
              </span>
              <span className={`font-mono text-[13px] max-w-[60%] break-words text-right ${disagree ? 'text-[#A07D28]' : 'text-[#2D3142]'}`}>
                {val}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReviewPageContent() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const runAId = searchParams.get("runA");
  const runBId = searchParams.get("runB");

  const [currentIndex, setCurrentIndex] = useState(0);
  const [notes, setNotes] = useState("");
  const [voteError, setVoteError] = useState<string | null>(null);
  const [lastSavedPostingId, setLastSavedPostingId] = useState<string | null>(null);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentIndexRef = useRef(currentIndex);

  useEffect(() => {
    currentIndexRef.current = currentIndex;
  }, [currentIndex]);

  const { data: runs = [], isLoading: runsLoading } = useQuery({
    ...getRunsApiV1EvalRunsGetOptions(),
    select: (data) => data as unknown as EvalRun[],
  });

  const runA = useMemo(() => runs.find((r) => r.id === runAId), [runs, runAId]);
  const runB = useMemo(() => runs.find((r) => r.id === runBId), [runs, runBId]);
  const passMismatch = !!(runA && runB && runA.pass_number !== runB.pass_number);

  const { data: resultsA = [], isLoading: loadingResultsA } = useQuery({
    ...getRunResultsApiV1EvalRunsRunIdResultsGetOptions({ 
      path: { run_id: runAId! },
    }),
    enabled: !!runAId && !passMismatch,
    select: (data) => data as unknown as EvalResult[],
  });

  const { data: resultsB = [], isLoading: loadingResultsB } = useQuery({
    ...getRunResultsApiV1EvalRunsRunIdResultsGetOptions({ 
      path: { run_id: runBId! },
    }),
    enabled: !!runBId && !passMismatch,
    select: (data) => data as unknown as EvalResult[],
  });

  const { data: corpus = [], isLoading: loadingCorpus } = useQuery({
    ...getCorpusApiV1EvalCorpusGetOptions(),
    enabled: !!runAId && !!runBId && !passMismatch,
    select: (data) => data as unknown as PostingListItem[],
  });

  const { data: comparisons = [], isLoading: loadingComparisons } = useQuery({
    ...getComparisonsApiV1EvalComparisonsGetOptions(),
    enabled: !!runAId && !!runBId && !passMismatch,
    select: (data) => data as unknown as EvalComparison[],
  });

  const dataLoading = loadingResultsA || loadingResultsB || loadingCorpus || loadingComparisons;

  const swapMap = useMemo(() => {
    if (!resultsA.length || !resultsB.length) return {};
    const idsA = new Set(resultsA.map((r) => r.posting_id));
    const commonIds = resultsB
      .map((r) => r.posting_id)
      .filter((id) => idsA.has(id));
    const map: Record<string, boolean> = {};
    for (const id of commonIds) {
      let hash = 0;
      for (let i = 0; i < id.length; i++) hash = (hash << 5) - hash + id.charCodeAt(i);
      map[id] = hash % 2 === 0;
    }
    return map;
  }, [resultsA, resultsB]);

  const votes = useMemo(() => {
    const resultIdsA = new Set(resultsA.map((r) => r.id));
    const resultIdsB = new Set(resultsB.map((r) => r.id));
    const restoredVotes: Record<string, VoteWinner> = {};
    for (const comp of comparisons) {
      const aInRunA = resultIdsA.has(comp.result_a_id) && resultIdsB.has(comp.result_b_id);
      const aInRunB = resultIdsA.has(comp.result_b_id) && resultIdsB.has(comp.result_a_id);
      if (aInRunA || aInRunB) {
        restoredVotes[comp.posting_id] = comp.winner as VoteWinner;
      }
    }
    return restoredVotes;
  }, [comparisons, resultsA, resultsB]);

  const commonPostings = useMemo(() => {
    const mapA = new Map(resultsA.map((r) => [r.posting_id, r]));
    const mapB = new Map(resultsB.map((r) => [r.posting_id, r]));
    const corpusMap = new Map(corpus.map((c) => [c.id, c]));

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const common: any[] = [];
    for (const [postingId, rA] of mapA) {
      const rB = mapB.get(postingId);
      if (rB) {
        common.push({
          postingId,
          resultA: rA,
          resultB: rB,
          posting: corpusMap.get(postingId),
        });
      }
    }
    return common;
  }, [resultsA, resultsB, corpus]);

  const totalComparisons = commonPostings.length;
  const clampedIndex = totalComparisons > 0 ? Math.min(currentIndex, totalComparisons - 1) : 0;
  const currentItem = commonPostings[clampedIndex] ?? null;

  const displayedPair = useMemo(() => {
    if (!currentItem) return null;
    const shouldSwap = swapMap[currentItem.postingId] ?? false;
    if (shouldSwap) {
      return {
        displayA: currentItem.resultB,
        displayB: currentItem.resultA,
        actualAIsRunA: false,
      };
    }
    return {
      displayA: currentItem.resultA,
      displayB: currentItem.resultB,
      actualAIsRunA: true,
    };
  }, [currentItem, swapMap]);

  const runALabel = useMemo(() => (runA ? formatRunLabel(runA) : "Run A"), [runA]);
  const runBLabel = useMemo(() => (runB ? formatRunLabel(runB) : "Run B"), [runB]);

  const displayALabel = displayedPair?.actualAIsRunA ? runALabel : runBLabel;
  const displayBLabel = displayedPair?.actualAIsRunA ? runBLabel : runALabel;

  const fieldsA = useMemo(() => (displayedPair ? getParsedResult(displayedPair.displayA) : {}), [displayedPair]);
  const fieldsB = useMemo(() => (displayedPair ? getParsedResult(displayedPair.displayB) : {}), [displayedPair]);

  const allVoted = totalComparisons > 0 && Object.keys(votes).length >= totalComparisons;

  const goNext = useCallback(() => {
    if (currentIndex < totalComparisons - 1) {
      setCurrentIndex((i) => i + 1);
      setNotes("");
    }
  }, [currentIndex, totalComparisons]);

  const goPrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1);
      setNotes("");
    }
  }, [currentIndex]);

  const syncRunParams = useCallback(
    (aId: string | null, bId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (aId) params.set("runA", aId);
      else params.delete("runA");
      if (bId) params.set("runB", bId);
      else params.delete("runB");
      router.replace(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname],
  );

  const voteMutation = useMutation({
    ...createComparisonApiV1EvalComparisonsPostMutation(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: getComparisonsApiV1EvalComparisonsGetQueryKey() });
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setLastSavedPostingId((variables as any).body.posting_id);
      savedTimerRef.current = setTimeout(() => setLastSavedPostingId(null), 800);
      setNotes("");
      if (currentIndexRef.current < totalComparisons - 1) {
        setCurrentIndex((i) => i + 1);
      }
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (err: any) => {
      setVoteError(err.message || "Failed to save vote");
    }
  });

  const handleVote = useCallback(
    async (winner: VoteWinner) => {
      if (!currentItem || !displayedPair || voteMutation.isPending) return;
      setVoteError(null);
      voteMutation.mutate({
        body: {
          posting_id: currentItem.postingId,
          result_a_id: displayedPair.displayA.id,
          result_b_id: displayedPair.displayB.id,
          winner,
          notes: notes.trim() || undefined,
        }
      });
    },
    [currentItem, displayedPair, voteMutation, notes]
  );

  useEffect(() => {
    if (!currentItem || totalComparisons === 0 || passMismatch) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.tagName === "INPUT") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const voteWinner = VOTE_KEY_MAP[e.key];
      if (voteWinner) {
        e.preventDefault();
        void handleVote(voteWinner);
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [currentItem, totalComparisons, passMismatch, handleVote, goPrev, goNext]);

  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    };
  }, []);

  const progressPct = totalComparisons > 0 ? ((Object.keys(votes).length / totalComparisons) * 100).toFixed(1) : "0";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight font-display text-[#2D3142]">
          Review
        </h1>
        <p className="mt-1 text-sm font-body text-muted-foreground">
          Head-to-head comparison of extraction quality
        </p>
      </div>

      <div className="rounded-lg border border-[#BFC0C0] p-5 bg-white shadow-sm">
        <h3 className="mb-4 font-semibold font-display text-sm text-[#2D3142]">
          Select Runs to Compare
        </h3>
        <div className="flex flex-col gap-4 sm:flex-row">
          {(
            [
              {
                id: "run-a-select",
                label: "Run A",
                value: runAId,
                other: runBId,
                onChange: (id: string | null) => syncRunParams(id, runBId),
              },
              {
                id: "run-b-select",
                label: "Run B",
                value: runBId,
                other: runAId,
                onChange: (id: string | null) => syncRunParams(runAId, id),
              },
            ] as const
          ).map((sel) => (
            <div key={sel.id} className="flex flex-1 flex-col gap-1">
              <label htmlFor={sel.id} className="font-body text-xs font-medium text-[#4F5D75]">
                {sel.label}
              </label>
              <select
                id={sel.id}
                value={sel.value ?? ""}
                onChange={(e) => sel.onChange(e.target.value || null)}
                disabled={runsLoading}
                className="rounded border border-[#BFC0C0] px-2 py-1.5 bg-white font-body text-[13px] text-[#2D3142]"
              >
                <option value="">
                  {runsLoading ? "Loading runs\u2026" : "Select a run\u2026"}
                </option>
                {runs.map((run) => (
                  <option key={run.id} value={run.id} disabled={run.id === sel.other}>
                    {formatRunLabel(run)}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      </div>

      {passMismatch && (
        <div className="mt-4 rounded-lg border border-[#8C2C2330] px-4 py-3 text-sm bg-[#8C2C231A] text-[#8C2C23] font-body" role="alert">
          Cannot compare runs with different pass numbers.
        </div>
      )}

      {(!runAId || !runBId) && (
        <div className="mt-6 flex items-center justify-center rounded-lg border border-dashed border-[#BFC0C0] py-12 bg-white">
          <p className="font-body text-[13px] text-[#4F5D75]">
            Select two runs above to begin reviewing comparisons.
          </p>
        </div>
      )}

      {runAId && runBId && !passMismatch && dataLoading && (
        <div className="mt-6 flex items-center justify-center rounded-lg border border-[#BFC0C0] py-12 bg-white">
          <p className="font-body text-[13px] text-[#4F5D75]">
            Loading results\u2026
          </p>
        </div>
      )}

      {runAId && runBId && !passMismatch && !dataLoading && totalComparisons === 0 && (
        <div className="mt-6 flex items-center justify-center rounded-lg border border-dashed border-[#BFC0C0] py-12 bg-white">
          <p className="font-body text-[13px] text-[#4F5D75]">
            No common postings found between these two runs.
          </p>
        </div>
      )}

      {runAId && runBId && !passMismatch && !dataLoading && totalComparisons > 0 && (
        <>
          <div className="mt-6 rounded-lg border border-[#BFC0C0] p-5 bg-white shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold font-display text-sm text-[#2D3142]">
                Posting Context
              </h3>
              <div className="flex items-center gap-3">
                <button
                  onClick={goPrev}
                  disabled={currentIndex === 0}
                  className="rounded border border-[#BFC0C0] px-2.5 py-1 text-xs font-medium text-[#4F5D75] transition-colors duration-150 hover:bg-[#E8E8E4] disabled:opacity-40 disabled:hover:bg-transparent font-body"
                >
                  Prev
                </button>
                <span className="font-body text-xs text-[#4F5D75]">
                  {clampedIndex + 1} of {totalComparisons}
                </span>
                <button
                  onClick={goNext}
                  disabled={currentIndex >= totalComparisons - 1}
                  className="rounded border border-[#BFC0C0] px-2.5 py-1 text-xs font-medium text-[#4F5D75] transition-colors duration-150 hover:bg-[#E8E8E4] disabled:opacity-40 disabled:hover:bg-transparent font-body"
                >
                  Next
                </button>
              </div>
            </div>
            <div>
              <p className="font-body text-[13px] font-medium text-[#2D3142]">
                {currentItem?.posting?.title ?? currentItem?.postingId}
              </p>
              {currentItem?.postingId && !currentItem.posting && (
                <p className="font-mono text-[11px] text-[#4F5D75] mt-0.5">
                  {currentItem.postingId}
                </p>
              )}
            </div>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#E8E8E4]">
              <div
                className="h-full rounded-full bg-[#EF8354] transition-[width] duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <div className="mt-1.5 flex items-center justify-between">
              <span className="font-body text-[11px] text-[#4F5D75]">
                {Object.keys(votes).length} of {totalComparisons} voted
              </span>
              {votes[currentItem?.postingId ?? ""] && (
                <span className="font-mono text-[11px] font-medium text-[#EF8354]">
                  &#x2713; Voted
                </span>
              )}
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <FieldComparisonPanel label={displayALabel} fields={fieldsA} otherFields={fieldsB} />
            <FieldComparisonPanel label={displayBLabel} fields={fieldsB} otherFields={fieldsA} />
          </div>

          <p className="mt-4 text-center font-body text-[11px] text-[#4F5D75]/50">
            Sides are randomized per posting to reduce bias.
          </p>

          <div className="mt-6 rounded-lg border border-[#BFC0C0] p-5 bg-white shadow-sm">
            <h3 className="mb-4 flex items-center gap-2 font-semibold font-display text-sm text-[#2D3142]">
              Which extraction is better?
              {lastSavedPostingId && (
                <span className="animate-pulse font-body text-[11px] font-normal text-[#1B998B]">
                  &#x2713; Saved
                </span>
              )}
            </h3>
            <div className="mb-4">
              <label htmlFor="comparison-notes" className="mb-1 block font-body text-xs font-medium text-[#4F5D75]">
                Notes (optional)
              </label>
              <textarea
                id="comparison-notes"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any observations about this comparison\u2026"
                className="w-full rounded border border-[#BFC0C0] px-3 py-2 bg-white font-body text-[13px] text-[#2D3142] focus:outline-none focus:ring-1 focus:ring-[#EF8354]"
              />
            </div>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {VOTE_BUTTONS.map(({ label, value }) => (
                <button
                  key={value}
                  onClick={() => void handleVote(value)}
                  disabled={voteMutation.isPending}
                  className="rounded border border-[#BFC0C0] px-4 py-2.5 font-medium font-body text-[13px] text-[#2D3142] transition-colors duration-150 hover:border-[#EF8354] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {voteMutation.isPending ? "\u2026" : label}
                </button>
              ))}
            </div>
            {voteError && (
              <p className="mt-3 font-body text-xs text-[#8C2C23]">
                {voteError}
              </p>
            )}
            <div className="mt-3 border-t border-[#BFC0C0] pt-2">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                {[
                  ["A", "A Better"],
                  ["B", "B Better"],
                  ["T", "Tie"],
                  ["X", "Both Bad"],
                  ["\u2190", "Prev"],
                  ["\u2192", "Next"],
                ].map(([key, lbl]) => (
                  <span key={key} className="flex items-center gap-1 font-body text-[10px] text-[#4F5D75]/50">
                    <kbd className="rounded border border-[#BFC0C0]/50 bg-[#E8E8E4] px-1 py-0.5 font-mono text-[10px] text-[#4F5D75]">
                      {key}
                    </kbd>
                    {lbl}
                  </span>
                ))}
              </div>
            </div>
            {allVoted && (
              <div className="mt-4 flex items-center justify-between rounded-md border border-[#1B998B30] bg-[#1B998B1A] px-4 py-2.5">
                <span className="font-body text-xs font-medium text-[#1B998B]">
                  All {totalComparisons} comparisons complete
                </span>
                <Link href="/eval/leaderboard" className="font-body text-xs font-medium text-[#EF8354] hover:underline">
                  View updated rankings &#x2192;
                </Link>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<div className="p-6 font-body text-[#4F5D75]">Loading&hellip;</div>}>
      <ReviewPageContent />
    </Suspense>
  );
}
