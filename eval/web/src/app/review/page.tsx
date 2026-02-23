"use client";

import { Suspense } from "react";
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import {
  getRuns,
  getRunResults,
  getCorpus,
  getComparisons,
  createComparison,
  type Run,
  type Result,
  type CorpusPosting,
} from "@/lib/api-client";
import { formatRunLabel } from "@/lib/run-utils";

const PASS1_FIELDS = [
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
] as const;

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

function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined) return "\u2014";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) {
    if (value.length === 0) return "\u2014";
    return value.join(", ");
  }
  return String(value);
}

function parseParsedResult(result: Result): Record<string, unknown> {
  if (!result.parsed_result) return {};
  try {
    return JSON.parse(result.parsed_result);
  } catch {
    return {};
  }
}

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
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
      <div className="mb-4">
        <h3 className="font-display text-[14px] font-semibold text-foreground">
          {label}
        </h3>
      </div>
      {PASS1_FIELDS.map((field) => {
        const val = formatFieldValue(fields[field]);
        const otherVal = formatFieldValue(otherFields[field]);
        const disagree = val !== otherVal;
        return (
          <div
            key={field}
            className="flex items-baseline justify-between border-b border-border/50 py-2 last:border-0"
          >
            <span
              className={`text-[12px] ${disagree ? "text-warning font-medium" : "text-muted-foreground"}`}
            >
              {field}
            </span>
            <span
              className={`font-mono text-[13px] tabular-nums text-right max-w-[60%] break-words ${disagree ? "text-warning" : "text-foreground"}`}
            >
              {val}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ReviewPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // --- State: runs & selectors ---
  const [runs, setRuns] = useState<Run[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runAId, setRunAId] = useState<number | null>(() => {
    const p = searchParams.get("runA");
    return p ? Number(p) : null;
  });
  const [runBId, setRunBId] = useState<number | null>(() => {
    const p = searchParams.get("runB");
    return p ? Number(p) : null;
  });

  // --- State: loaded data ---
  const [resultsA, setResultsA] = useState<Result[]>([]);
  const [resultsB, setResultsB] = useState<Result[]>([]);
  const [corpus, setCorpus] = useState<CorpusPosting[]>([]);
  const [dataLoading, setDataLoading] = useState(false);

  // --- State: comparison navigation ---
  const [currentIndex, setCurrentIndex] = useState(0);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [votes, setVotes] = useState<Record<string, VoteWinner>>({});
  const [voteError, setVoteError] = useState<string | null>(null);

  // --- State: save confirmation flash ---
  const [lastSavedPostingId, setLastSavedPostingId] = useState<string | null>(null);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- State: A/B randomization map (posting_id -> boolean where true = swap) ---
  const [swapMap, setSwapMap] = useState<Record<string, boolean>>({});

  // --- Load available runs ---
  useEffect(() => {
    let cancelled = false;
    setRunsLoading(true);
    getRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch(() => {
        if (!cancelled) setRuns([]);
      })
      .finally(() => {
        if (!cancelled) setRunsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // --- Pass mismatch derived value ---
  const passMismatch = useMemo(() => {
    if (runAId === null || runBId === null) return false;
    const runA = runs.find((r) => r.id === runAId);
    const runB = runs.find((r) => r.id === runBId);
    return !!(runA && runB && runA.pass_number !== runB.pass_number);
  }, [runs, runAId, runBId]);

  // --- Load results + corpus when both runs selected ---
  useEffect(() => {
    if (runAId === null || runBId === null) {
      setDataLoading(false);
      setResultsA([]);
      setResultsB([]);
      setCorpus([]);
      setCurrentIndex(0);
      setVotes({});
      setNotes("");
      setSwapMap({});
      return;
    }

    // Show loading immediately so the render doesn't briefly show an empty-state
    // message while waiting for runs metadata to arrive.
    setDataLoading(true);

    // Defer until runs metadata is loaded so the cross-pass guard can fire correctly
    if (runs.length === 0) return;

    const runA = runs.find((r) => r.id === runAId);
    const runB = runs.find((r) => r.id === runBId);
    if (runA && runB && runA.pass_number !== runB.pass_number) {
      setDataLoading(false);
      return;
    }

    let cancelled = false;

    Promise.all([getRunResults(runAId), getRunResults(runBId), getCorpus(), getComparisons()])
      .then(([rA, rB, c, existingComparisons]) => {
        if (cancelled) return;
        setResultsA(rA);
        setResultsB(rB);
        setCorpus(c);
        setCurrentIndex(0);
        setNotes("");

        // Build set of result IDs for each run
        const resultIdsA = new Set(rA.map((r) => r.id));
        const resultIdsB = new Set(rB.map((r) => r.id));

        // Restore votes from existing comparisons between these two runs
        const restoredVotes: Record<string, VoteWinner> = {};
        for (const comp of existingComparisons) {
          const aInRunA = resultIdsA.has(comp.result_a_id) && resultIdsB.has(comp.result_b_id);
          const aInRunB = resultIdsA.has(comp.result_b_id) && resultIdsB.has(comp.result_a_id);
          if (aInRunA || aInRunB) {
            restoredVotes[comp.posting_id] = comp.winner;
          }
        }
        setVotes(restoredVotes);

        // Build randomization map for common postings
        const idsA = new Set(rA.map((r) => r.posting_id));
        const commonIds = rB
          .map((r) => r.posting_id)
          .filter((id) => idsA.has(id));
        const newSwapMap: Record<string, boolean> = {};
        for (const id of commonIds) {
          newSwapMap[id] = Math.random() > 0.5;
        }
        setSwapMap(newSwapMap);
      })
      .catch(() => {
        if (!cancelled) {
          setResultsA([]);
          setResultsB([]);
          setCorpus([]);
          setSwapMap({});
        }
      })
      .finally(() => {
        if (!cancelled) setDataLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [runAId, runBId, runs]);

  // --- Computed: common postings ---
  const commonPostings = useMemo(() => {
    const mapA = new Map(resultsA.map((r) => [r.posting_id, r]));
    const mapB = new Map(resultsB.map((r) => [r.posting_id, r]));
    const corpusMap = new Map(corpus.map((c) => [c.id, c]));

    const common: {
      postingId: string;
      resultA: Result;
      resultB: Result;
      posting: CorpusPosting | undefined;
    }[] = [];

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
  const currentItem = commonPostings[currentIndex] ?? null;

  // --- Determine displayed A/B based on swap map ---
  const displayedPair = useMemo(() => {
    if (!currentItem) return null;
    const shouldSwap = swapMap[currentItem.postingId] ?? false;
    if (shouldSwap) {
      return {
        displayA: currentItem.resultB,
        displayB: currentItem.resultA,
        // When swapped: display-A is actually run B, display-B is actually run A
        actualAIsRunA: false,
      };
    }
    return {
      displayA: currentItem.resultA,
      displayB: currentItem.resultB,
      actualAIsRunA: true,
    };
  }, [currentItem, swapMap]);

  // --- Run labels (resolved from actual run metadata) ---
  const runALabel = useMemo(() => {
    const run = runs.find((r) => r.id === runAId);
    return run ? formatRunLabel(run) : "Run A";
  }, [runs, runAId]);

  const runBLabel = useMemo(() => {
    const run = runs.find((r) => r.id === runBId);
    return run ? formatRunLabel(run) : "Run B";
  }, [runs, runBId]);

  const displayALabel = displayedPair?.actualAIsRunA ? runALabel : runBLabel;
  const displayBLabel = displayedPair?.actualAIsRunA ? runBLabel : runALabel;

  // --- Parsed fields ---
  const fieldsA = useMemo(
    () => (displayedPair ? parseParsedResult(displayedPair.displayA) : {}),
    [displayedPair],
  );
  const fieldsB = useMemo(
    () => (displayedPair ? parseParsedResult(displayedPair.displayB) : {}),
    [displayedPair],
  );

  // --- All voted derived value ---
  const allVoted = totalComparisons > 0 && Object.keys(votes).length >= totalComparisons;

  // --- Handlers ---
  const handleVote = useCallback(
    async (winner: VoteWinner) => {
      if (!currentItem || !displayedPair || submitting) return;

      setSubmitting(true);
      setVoteError(null);

      // Map the displayed winner back to actual result IDs
      // displayA and displayB may be swapped, so we need to pass the actual result IDs
      // result_a_id and result_b_id in the API correspond to display A and display B
      const result_a_id = displayedPair.displayA.id;
      const result_b_id = displayedPair.displayB.id;

      try {
        await createComparison({
          posting_id: currentItem.postingId,
          result_a_id,
          result_b_id,
          winner,
          notes: notes.trim() || undefined,
        });

        setVotes((prev) => ({ ...prev, [currentItem.postingId]: winner }));
        if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
        setLastSavedPostingId(currentItem.postingId);
        savedTimerRef.current = setTimeout(() => setLastSavedPostingId(null), 800);
        setNotes("");

        // Auto-advance to next if available
        if (currentIndex < totalComparisons - 1) {
          setCurrentIndex((i) => i + 1);
        }
      } catch (err) {
        setVoteError(err instanceof Error ? err.message : "Failed to save vote");
      } finally {
        setSubmitting(false);
      }
    },
    [currentItem, displayedPair, submitting, notes, currentIndex, totalComparisons],
  );

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

  const syncRunParams = useCallback((aId: number | null, bId: number | null) => {
    const params = new URLSearchParams(searchParams.toString());
    if (aId !== null) params.set("runA", String(aId)); else params.delete("runA");
    if (bId !== null) params.set("runB", String(bId)); else params.delete("runB");
    router.replace(`${pathname}?${params.toString()}`);
  }, [searchParams, router, pathname]);

  // --- Keyboard shortcuts ---
  useEffect(() => {
    if (!currentItem || totalComparisons === 0 || passMismatch) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.tagName === "INPUT") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const voteWinner = VOTE_KEY_MAP[e.key];
      if (voteWinner) {
        e.preventDefault();
        handleVote(voteWinner);
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

  // --- Cleanup saved timer on unmount ---
  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    };
  }, []);

  const progressPct =
    totalComparisons > 0
      ? ((Object.keys(votes).length / totalComparisons) * 100).toFixed(1)
      : "0";

  // --- Render ---
  return (
    <AppShell title="Review" subtitle="Head-to-head comparison">
      {/* Run selectors */}
      <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
        <h3 className="font-display mb-4 text-[14px] font-semibold text-foreground">
          Select Runs to Compare
        </h3>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex flex-1 flex-col gap-1">
            <label
              htmlFor="run-a-select"
              className="text-[12px] font-medium text-muted-foreground"
            >
              Run A
            </label>
            <select
              id="run-a-select"
              value={runAId ?? ""}
              onChange={(e) => {
                const id = e.target.value ? Number(e.target.value) : null;
                setRunAId(id);
                syncRunParams(id, runBId);
              }}
              disabled={runsLoading}
              className="rounded-md border border-border bg-background px-2 py-1.5 text-[13px]"
            >
              <option value="">
                {runsLoading ? "Loading runs\u2026" : "Select a run\u2026"}
              </option>
              {runs.map((run) => (
                <option key={run.id} value={run.id} disabled={run.id === runBId}>
                  {formatRunLabel(run)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label
              htmlFor="run-b-select"
              className="text-[12px] font-medium text-muted-foreground"
            >
              Run B
            </label>
            <select
              id="run-b-select"
              value={runBId ?? ""}
              onChange={(e) => {
                const id = e.target.value ? Number(e.target.value) : null;
                setRunBId(id);
                syncRunParams(runAId, id);
              }}
              disabled={runsLoading}
              className="rounded-md border border-border bg-background px-2 py-1.5 text-[13px]"
            >
              <option value="">
                {runsLoading ? "Loading runs\u2026" : "Select a run\u2026"}
              </option>
              {runs.map((run) => (
                <option key={run.id} value={run.id} disabled={run.id === runAId}>
                  {formatRunLabel(run)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Pass number mismatch — blocking error */}
      {passMismatch && (
        <div className="mt-4 rounded-lg border border-error/30 bg-error-muted p-4 text-[13px] text-status-wrong">
          Cannot compare runs with different pass numbers. Please select two Pass 1 or two Pass 2 runs.
        </div>
      )}

      {/* Empty state */}
      {runAId === null || runBId === null ? (
        <div className="mt-6 rounded-lg border border-dashed border-border bg-card p-12 text-center shadow-sm">
          <p className="text-[13px] text-muted-foreground">
            Select two runs above to begin reviewing comparisons.
          </p>
        </div>
      ) : passMismatch ? null : dataLoading ? (
        <div className="mt-6 rounded-lg border border-border bg-card p-12 text-center shadow-sm">
          <p className="text-[13px] text-muted-foreground">
            Loading results and corpus\u2026
          </p>
        </div>
      ) : totalComparisons === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed border-border bg-card p-12 text-center shadow-sm">
          <p className="text-[13px] text-muted-foreground">
            No common postings found between these two runs.
          </p>
        </div>
      ) : (
        <>
          {/* Posting context card */}
          <div className="mt-6 rounded-lg border border-border bg-card p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-display text-[14px] font-semibold">
                Posting Context
              </h3>
              <div className="flex items-center gap-3">
                <button
                  onClick={goPrev}
                  disabled={currentIndex === 0}
                  className="rounded-md border border-border px-2.5 py-1 text-[12px] font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:border-primary/30 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Prev
                </button>
                <span className="text-[12px] text-muted-foreground">
                  Comparison {currentIndex + 1} of {totalComparisons}
                </span>
                <button
                  onClick={goNext}
                  disabled={currentIndex >= totalComparisons - 1}
                  className="rounded-md border border-border px-2.5 py-1 text-[12px] font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:border-primary/30 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-[13px] font-medium text-foreground">
                {currentItem?.posting?.title ?? currentItem?.postingId}
              </div>
              <div className="text-[12px] text-muted-foreground">
                {currentItem?.posting?.company_slug ?? ""}
                {currentItem?.posting?.location
                  ? ` \u00B7 ${currentItem.posting.location}`
                  : ""}
              </div>
              {currentItem?.postingId && (
                <div className="text-[11px] text-muted-foreground/70">
                  Posting ID: {currentItem.postingId}
                </div>
              )}
            </div>
            {/* Progress bar */}
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <div className="mt-1.5 flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground/70">
                {Object.keys(votes).length} of {totalComparisons} voted
              </span>
              {votes[currentItem?.postingId ?? ""] && (
                <span className="text-[11px] font-medium text-primary">
                  &#x2713; Voted
                </span>
              )}
            </div>
          </div>

          {/* Two-column comparison */}
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <FieldComparisonPanel label={displayALabel} fields={fieldsA} otherFields={fieldsB} />
            <FieldComparisonPanel label={displayBLabel} fields={fieldsB} otherFields={fieldsA} />
          </div>

          {/* Randomization notice */}
          <p className="mt-4 text-[11px] text-muted-foreground/50 text-center">
            Sides are randomized per posting to reduce bias — judge by content, not position.
          </p>

          {/* Vote section */}
          <div className="mt-6 rounded-lg border border-border bg-card p-5 shadow-sm">
            <h3 className="font-display mb-4 text-[14px] font-semibold text-foreground flex items-center gap-2">
              Which extraction is better?
              {lastSavedPostingId && (
                <span className="text-[11px] font-normal text-status-correct animate-pulse">&#x2713; Saved</span>
              )}
            </h3>
            {/* Notes */}
            <div className="mb-4">
              <label
                htmlFor="comparison-notes"
                className="mb-1 block text-[12px] font-medium text-muted-foreground"
              >
                Notes (optional)
              </label>
              <textarea
                id="comparison-notes"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any observations about this comparison\u2026"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-[13px] text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40"
              />
            </div>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {VOTE_BUTTONS.map(({ label, value }) => (
                <button
                  key={value}
                  onClick={() => handleVote(value)}
                  disabled={submitting}
                  className="rounded-md border border-border px-4 py-2.5 text-[13px] font-medium text-foreground transition-colors hover:bg-muted/50 hover:border-primary/30 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? "\u2026" : label}
                </button>
              ))}
            </div>
            {voteError && (
              <p className="mt-3 text-[12px] text-status-wrong">
                {voteError}
              </p>
            )}
            {/* Hotkey legend */}
            <div className="mt-3 border-t border-border/50 pt-2">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                {[
                  ["A", "A Better"],
                  ["B", "B Better"],
                  ["T", "Tie"],
                  ["X", "Both Bad"],
                  ["←", "Prev"],
                  ["→", "Next"],
                ].map(([key, label]) => (
                  <span key={key} className="flex items-center gap-1 text-[10px] text-muted-foreground/50">
                    <kbd className="rounded border border-border/50 bg-muted px-1 py-0.5 font-mono text-[10px] text-muted-foreground">
                      {key}
                    </kbd>
                    {label}
                  </span>
                ))}
              </div>
            </div>
            {/* All voted: next-step link to leaderboard */}
            {allVoted && (
              <div className="mt-4 flex items-center justify-between rounded-md border border-success/30 bg-success-muted px-4 py-2.5">
                <span className="text-[12px] text-status-correct font-medium">
                  All {totalComparisons} comparisons complete
                </span>
                <Link href="/leaderboard" className="text-[12px] text-primary hover:underline font-medium">
                  View updated rankings &#x2192;
                </Link>
              </div>
            )}
          </div>
        </>
      )}
    </AppShell>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={null}>
      <ReviewPageContent />
    </Suspense>
  );
}
