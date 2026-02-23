"use client";

import { Suspense } from "react";
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { CheckCircle2, MinusCircle, PenLine, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { AppShell } from "@/components/app-shell";
import { StatusBadge } from "@/components/status-badge";
import {
  getRuns,
  getRunResults,
  getCorpus,
  getRunFieldReviews,
  createFieldReview,
  deleteFieldReview,
  type Run,
  type Result,
  type CorpusPosting,
  type FieldReview,
} from "@/lib/api-client";
import { formatRunLabel } from "@/lib/run-utils";

const REVIEWABLE_FIELDS = [
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

function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined) return "\u2014";
  if (Array.isArray(value)) {
    return value.length === 0 ? "\u2014" : value.join(", ");
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function valuesMatch(a: unknown, b: unknown): boolean {
  if (a === null || a === undefined) return b === null || b === undefined;
  if (b === null || b === undefined) return false;
  return String(a).toLowerCase() === String(b).toLowerCase();
}

function judgmentToStatus(review: FieldReview | undefined): string {
  if (!review) return "pending";
  if (review.is_correct === 1) return "correct";
  if (review.is_correct === -1) return "cant-assess";
  if (review.is_correct === 0 && review.correct_value === null) return "blank";
  return "replaced";
}

interface ReplaceModeState {
  fieldName: string;
  fieldIdx: number;
  draftValue: string;
}

function AccuracyPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // --- Data state ---
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(() => {
    const param = searchParams.get("run");
    return param ? Number(param) : null;
  });
  const [results, setResults] = useState<Result[]>([]);
  const [corpus, setCorpus] = useState<CorpusPosting[]>([]);
  const [reviews, setReviews] = useState<Record<string, FieldReview[]>>({});

  // --- UI state ---
  const [postingIdx, setPostingIdx] = useState(0);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingData, setLoadingData] = useState(false);
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});
  const [reviewError, setReviewError] = useState<string | null>(null);

  // --- Keyboard / focus state ---
  const [focusedFieldIdx, setFocusedFieldIdx] = useState(0);
  const [replaceMode, setReplaceMode] = useState<ReplaceModeState | null>(null);
  const [advanceWarning, setAdvanceWarning] = useState(false);
  const [savedField, setSavedField] = useState<string | null>(null);
  const [confirmAllCorrect, setConfirmAllCorrect] = useState(false);
  const replaceInputRef = useRef<HTMLInputElement>(null);
  const savedFieldTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const confirmAllTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // --- Fetch runs on mount ---
  useEffect(() => {
    let cancelled = false;
    setLoadingRuns(true);
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

  // --- Fetch results, corpus, reviews when run is selected ---
  useEffect(() => {
    if (selectedRunId === null) return;
    let cancelled = false;
    setLoadingData(true);
    setPostingIdx(0);

    Promise.all([
      getRunResults(selectedRunId),
      getCorpus(),
      getRunFieldReviews(selectedRunId),
    ])
      .then(([resData, corpusData, reviewData]) => {
        if (!cancelled) {
          setResults(resData);
          setCorpus(corpusData);
          setReviews(reviewData);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingData(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedRunId]);

  // --- Reset focus state when navigating postings ---
  useEffect(() => {
    setFocusedFieldIdx(0);
    setReplaceMode(null);
    setAdvanceWarning(false);
    setConfirmAllCorrect(false);
  }, [postingIdx]);

  // --- Auto-focus replace input ---
  useEffect(() => {
    if (replaceMode) replaceInputRef.current?.focus();
  }, [replaceMode]);

  // --- Cleanup timers on unmount ---
  useEffect(() => {
    return () => {
      if (savedFieldTimerRef.current) clearTimeout(savedFieldTimerRef.current);
      if (confirmAllTimerRef.current) clearTimeout(confirmAllTimerRef.current);
    };
  }, []);

  // --- Derived: corpus lookup ---
  const corpusMap = useMemo(() => {
    const m: Record<string, CorpusPosting> = {};
    for (const c of corpus) m[c.id] = c;
    return m;
  }, [corpus]);

  // --- Current result and posting ---
  const currentResult: Result | undefined = results[postingIdx];
  const currentPosting: CorpusPosting | undefined = currentResult
    ? corpusMap[currentResult.posting_id]
    : undefined;

  const parsedResult: Record<string, unknown> = useMemo(() => {
    if (!currentResult?.parsed_result) return {};
    try {
      return JSON.parse(currentResult.parsed_result);
    } catch {
      return {};
    }
  }, [currentResult]);

  const groundTruth: Record<string, unknown> = useMemo(() => {
    if (!currentPosting?.reference_pass1) return {};
    try {
      return JSON.parse(currentPosting.reference_pass1);
    } catch {
      return {};
    }
  }, [currentPosting]);

  // --- Reviews for current result ---
  const currentReviews: Record<string, FieldReview> = useMemo(() => {
    if (!currentResult) return {};
    const resultReviews = reviews[String(currentResult.id)] ?? [];
    const m: Record<string, FieldReview> = {};
    for (const r of resultReviews) {
      if (!m[r.field_name] || r.id > m[r.field_name].id) {
        m[r.field_name] = r;
      }
    }
    return m;
  }, [reviews, currentResult]);

  // --- Progress calculations ---
  const fieldCompletionCount = useMemo(
    () => REVIEWABLE_FIELDS.filter((f) => f in currentReviews).length,
    [currentReviews],
  );

  const isPostingComplete = fieldCompletionCount === REVIEWABLE_FIELDS.length;

  const totalFieldsReviewed = useMemo(
    () =>
      results.reduce(
        (acc, res) => acc + (reviews[String(res.id)]?.length ?? 0),
        0,
      ),
    [results, reviews],
  );

  const postingsComplete = useMemo(() => {
    let r = 0;
    for (const res of results) {
      const resultReviews = reviews[String(res.id)] ?? [];
      const judged = new Set(resultReviews.map((rv) => rv.field_name));
      if (REVIEWABLE_FIELDS.every((f) => judged.has(f))) r += 1;
    }
    return r;
  }, [results, reviews]);

  const nextUnreviewedIdx = useMemo(() => {
    for (let i = 0; i < results.length; i++) {
      const rv = reviews[String(results[i].id)] ?? [];
      const judged = new Set(rv.map((r) => r.field_name));
      if (!REVIEWABLE_FIELDS.every((f) => judged.has(f))) return i;
    }
    return null;
  }, [results, reviews]);

  const allPostingsComplete = results.length > 0 && postingsComplete === results.length;

  const totalFields = results.length * REVIEWABLE_FIELDS.length;
  const progressPct =
    totalFields > 0
      ? Math.round((totalFieldsReviewed / totalFields) * 100)
      : 0;

  // --- Submit a single field review ---
  const handleJudgment = useCallback(
    async (
      fieldName: string,
      isCorrect: number,
      correctValue: string | null,
    ) => {
      if (!currentResult) return;
      const key = `${currentResult.id}-${fieldName}`;
      setReviewError(null);
      setAdvanceWarning(false);
      setSubmitting((prev) => ({ ...prev, [key]: true }));

      const modelValue = formatFieldValue(parsedResult[fieldName]);

      try {
        await createFieldReview({
          result_id: currentResult.id,
          field_name: fieldName,
          model_value: modelValue === "\u2014" ? null : modelValue,
          is_correct: isCorrect,
          correct_value: correctValue,
        });

        const newReview: FieldReview = {
          id: Date.now(),
          created_at: new Date().toISOString(),
          result_id: currentResult.id,
          field_name: fieldName,
          model_value: modelValue === "\u2014" ? null : modelValue,
          is_correct: isCorrect,
          correct_value: correctValue,
        };

        setReviews((prev) => {
          const resultKey = String(currentResult.id);
          const existing = prev[resultKey] ?? [];
          return {
            ...prev,
            [resultKey]: [
              ...existing.filter((r) => r.field_name !== fieldName),
              newReview,
            ],
          };
        });
        if (savedFieldTimerRef.current) clearTimeout(savedFieldTimerRef.current);
        setSavedField(fieldName);
        savedFieldTimerRef.current = setTimeout(() => setSavedField(null), 600);
      } catch (err) {
        setReviewError(
          err instanceof Error ? err.message : "Failed to save review",
        );
      } finally {
        setSubmitting((prev) => ({ ...prev, [key]: false }));
      }
    },
    [currentResult, parsedResult],
  );

  // --- Delete a field review (Escape undo) ---
  const handleDeleteReview = useCallback(
    async (fieldName: string) => {
      if (!currentResult) return;
      const key = `${currentResult.id}-${fieldName}`;
      setSubmitting((prev) => ({ ...prev, [key]: true }));
      try {
        await deleteFieldReview(currentResult.id, fieldName);
        setReviews((prev) => {
          const resultKey = String(currentResult.id);
          return {
            ...prev,
            [resultKey]: (prev[resultKey] ?? []).filter(
              (r) => r.field_name !== fieldName,
            ),
          };
        });
      } catch (err) {
        setReviewError(
          err instanceof Error ? err.message : "Failed to reset field",
        );
      } finally {
        setSubmitting((prev) => ({ ...prev, [key]: false }));
      }
    },
    [currentResult],
  );

  // --- Mark all fields correct ---
  const handleMarkAllCorrect = useCallback(async () => {
    if (!currentResult) return;
    await Promise.all(
      REVIEWABLE_FIELDS.map((field) => handleJudgment(field, 1, null)),
    );
  }, [currentResult, handleJudgment]);

  // --- Focus advance helper ---
  const advanceFocus = useCallback(() => {
    setFocusedFieldIdx((prev) => Math.min(REVIEWABLE_FIELDS.length - 1, prev + 1));
  }, []);

  // --- Navigation helpers with advance warning ---
  const goPostingNext = useCallback(
    () => {
      if (postingIdx >= results.length - 1) return;
      if (!isPostingComplete && !advanceWarning) {
        setAdvanceWarning(true);
        return;
      }
      setAdvanceWarning(false);
      setPostingIdx((i) => Math.min(results.length - 1, i + 1));
    },
    [isPostingComplete, advanceWarning, results.length, postingIdx],
  );

  const goPostingPrev = useCallback(
    () => {
      if (postingIdx <= 0) return;
      if (!isPostingComplete && !advanceWarning) {
        setAdvanceWarning(true);
        return;
      }
      setAdvanceWarning(false);
      setPostingIdx((i) => Math.max(0, i - 1));
    },
    [isPostingComplete, advanceWarning, postingIdx],
  );

  // --- Commit replace mode ---
  const commitReplace = useCallback(() => {
    if (!replaceMode) return;
    handleJudgment(
      replaceMode.fieldName,
      0,
      replaceMode.draftValue.trim() || null,
    );
    setReplaceMode(null);
    advanceFocus();
  }, [replaceMode, handleJudgment, advanceFocus]);

  // --- Escape key handler ---
  const handleEscapeKey = useCallback(() => {
    setAdvanceWarning(false);
    if (replaceMode !== null) {
      setReplaceMode(null);
      return;
    }
    const fieldName = REVIEWABLE_FIELDS[focusedFieldIdx];
    if (fieldName && currentReviews[fieldName]) {
      handleDeleteReview(fieldName);
    }
  }, [replaceMode, focusedFieldIdx, currentReviews, handleDeleteReview]);

  // --- Document-level keyboard handler ---
  useEffect(() => {
    if (!selectedRunId || results.length === 0) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "SELECT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "INPUT"
      )
        return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      // In replace mode: only handle Enter and Escape
      if (replaceMode !== null) {
        if (e.key === "Enter") {
          e.preventDefault();
          commitReplace();
        } else if (e.key === "Escape") {
          e.preventDefault();
          handleEscapeKey();
        }
        return;
      }

      // Normal mode key bindings
      const field = REVIEWABLE_FIELDS[focusedFieldIdx];

      switch (e.key) {
        case "ArrowUp":
          e.preventDefault();
          setFocusedFieldIdx((prev) => Math.max(0, prev - 1));
          break;
        case "ArrowDown":
          e.preventDefault();
          setFocusedFieldIdx((prev) =>
            Math.min(REVIEWABLE_FIELDS.length - 1, prev + 1),
          );
          break;
        case "ArrowLeft":
          e.preventDefault();
          goPostingPrev();
          break;
        case "ArrowRight":
          e.preventDefault();
          goPostingNext();
          break;
        case "c":
          if (field) {
            handleJudgment(field, 1, null);
            advanceFocus();
          }
          break;
        case "b":
          if (field) {
            handleJudgment(field, 0, null);
            advanceFocus();
          }
          break;
        case "r":
          if (field) {
            const existingReview = currentReviews[field];
            setReplaceMode({
              fieldName: field,
              fieldIdx: focusedFieldIdx,
              draftValue: existingReview?.correct_value ?? "",
            });
          }
          break;
        case "n":
          if (field) {
            handleJudgment(field, -1, null);
            advanceFocus();
          }
          break;
        case "Escape":
          e.preventDefault();
          handleEscapeKey();
          break;
        case "a":
          if (!confirmAllCorrect) {
            if (confirmAllTimerRef.current) clearTimeout(confirmAllTimerRef.current);
            setConfirmAllCorrect(true);
            confirmAllTimerRef.current = setTimeout(() => setConfirmAllCorrect(false), 3000);
          } else {
            setConfirmAllCorrect(false);
            handleMarkAllCorrect();
          }
          break;
        case "j":
          if (nextUnreviewedIdx !== null) {
            setPostingIdx(nextUnreviewedIdx);
            setFocusedFieldIdx(0);
          }
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [
    selectedRunId,
    results.length,
    replaceMode,
    focusedFieldIdx,
    currentReviews,
    handleJudgment,
    advanceFocus,
    goPostingNext,
    goPostingPrev,
    commitReplace,
    handleEscapeKey,
    handleMarkAllCorrect,
    nextUnreviewedIdx,
    confirmAllCorrect,
  ]);

  // --- Run selector change ---
  const handleRunChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    const newId = val ? Number(val) : null;
    setSelectedRunId(newId);
    const params = new URLSearchParams(searchParams.toString());
    if (newId) {
      params.set("run", String(newId));
    } else {
      params.delete("run");
    }
    router.replace(`${pathname}?${params.toString()}`);
  };

  return (
    <AppShell title="Accuracy Review" subtitle="Field-level judgments">
      {/* Run selector */}
      <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
        <label
          htmlFor="run-select"
          className="mb-2 block text-[12px] font-medium text-muted-foreground"
        >
          Select Run
        </label>
        <select
          id="run-select"
          value={selectedRunId ?? ""}
          onChange={handleRunChange}
          disabled={loadingRuns}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option value="">
            {loadingRuns ? "Loading runs\u2026" : "Choose a run\u2026"}
          </option>
          {runs.map((run) => (
            <option key={run.id} value={run.id}>
              {formatRunLabel(run)}
            </option>
          ))}
        </select>
      </div>

      {/* Loading state */}
      {loadingData && (
        <div className="mt-6 flex items-center justify-center py-16">
          <div className="animate-pulse text-[13px] text-muted-foreground">
            Loading results\u2026
          </div>
        </div>
      )}

      {/* No run selected */}
      {!selectedRunId && !loadingData && (
        <div className="mt-6 flex items-center justify-center py-16">
          <div className="text-[13px] text-muted-foreground">
            Select a run to begin reviewing
          </div>
        </div>
      )}

      {/* Main content — visible when data is loaded */}
      {selectedRunId && !loadingData && results.length > 0 && (
        <>
          {/* Progress strip */}
          <div className="mt-6 rounded-lg border border-border bg-card px-5 py-3 shadow-sm">
            <div className="flex items-center gap-4">
              {/* Dual counters */}
              <div className="flex items-center gap-3 shrink-0">
                <div className="text-center">
                  <span className="font-mono text-[15px] tabular-nums font-semibold text-foreground">
                    {postingsComplete}/{results.length}
                  </span>
                  <span className="ml-1.5 text-[11px] text-muted-foreground">
                    postings
                  </span>
                </div>
                <div className="h-5 w-px bg-border" />
                <div className="text-center">
                  <span className="font-mono text-[15px] tabular-nums font-semibold text-foreground">
                    {totalFieldsReviewed}/{totalFields}
                  </span>
                  <span className="ml-1.5 text-[11px] text-muted-foreground">
                    fields
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="flex-1">
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-300"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>

              {/* Current posting mini-dots */}
              <div className="flex items-center gap-0.5 shrink-0">
                {REVIEWABLE_FIELDS.map((f) => (
                  <div
                    key={f}
                    className={cn(
                      "h-2 w-2 rounded-full",
                      currentReviews[f] ? "bg-primary" : "bg-muted",
                    )}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Navigation bar */}
          <div className="mt-3 flex items-center justify-between">
            <button
              onClick={() => goPostingPrev()}
              disabled={postingIdx === 0}
              className="rounded-md border border-border bg-card px-3 py-1.5 text-[13px] font-medium text-foreground shadow-sm transition-colors hover:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              &larr; Prev
            </button>

            {/* Center: label or advance warning */}
            {advanceWarning ? (
              <div className="flex items-center gap-2 rounded-md border border-warning/50 bg-warning-muted px-3 py-1">
                <span className="text-[12px] font-medium text-warning-foreground">
                  {REVIEWABLE_FIELDS.length - fieldCompletionCount} fields
                  unreviewed — skip?
                </span>
                <span className="text-[11px] text-muted-foreground/60">
                  Press ←/→ again to confirm · Esc to cancel
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <span className="text-[12px] text-muted-foreground">
                  Posting {postingIdx + 1} of {results.length}
                </span>
                <button
                  onClick={() => {
                    if (nextUnreviewedIdx !== null && nextUnreviewedIdx !== postingIdx) {
                      setPostingIdx(nextUnreviewedIdx);
                      setFocusedFieldIdx(0);
                    }
                  }}
                  disabled={
                    nextUnreviewedIdx === null ||
                    nextUnreviewedIdx === postingIdx
                  }
                  className="rounded border border-border px-2 py-0.5 text-[11px] text-muted-foreground transition-colors hover:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Jump [J]
                </button>
              </div>
            )}

            <button
              onClick={() => goPostingNext()}
              disabled={postingIdx === results.length - 1}
              className={cn(
                "rounded-md border px-3 py-1.5 text-[13px] font-medium shadow-sm transition-colors hover:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-40",
                isPostingComplete
                  ? "border-primary text-primary"
                  : "border-border bg-card text-foreground",
              )}
            >
              Next &rarr;
            </button>
          </div>

          {/* Main content grid — posting (2 cols) + judgments (3 cols) */}
          {allPostingsComplete && (
            <div className="mt-3 flex items-center justify-between rounded-md border border-success/30 bg-success-muted px-4 py-2.5">
              <span className="text-[12px] text-status-correct font-medium">
                All {results.length} postings reviewed
              </span>
              <Link
                href={`/review?runA=${selectedRunId}`}
                className="text-[12px] text-primary hover:underline font-medium"
              >
                Compare with another run →
              </Link>
            </div>
          )}

          <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-5">
            {/* Posting card */}
            <div className="flex flex-col rounded-lg border border-border bg-card shadow-sm lg:col-span-2">
              <div className="shrink-0 border-b border-border/50 px-5 py-3">
                <div className="flex items-baseline justify-between">
                  <h3 className="font-display text-[14px] font-semibold text-foreground">
                    Posting
                  </h3>
                  {currentResult && (
                    <span className="text-[12px] text-muted-foreground">
                      Result #{currentResult.id}
                    </span>
                  )}
                </div>
                {currentPosting && (
                  <div className="mt-2 space-y-0.5">
                    <div className="text-[13px] font-medium text-foreground">
                      {currentPosting.title}
                    </div>
                    <div className="text-[12px] text-muted-foreground">
                      {currentPosting.company_slug}
                      {currentPosting.location
                        ? ` \u00B7 ${currentPosting.location}`
                        : ""}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                {currentPosting ? (
                  <div className="text-[12px] leading-relaxed text-muted-foreground whitespace-pre-wrap">
                    {currentPosting.full_text}
                  </div>
                ) : (
                  <div className="text-[13px] text-muted-foreground">
                    Posting not found in corpus
                  </div>
                )}
              </div>
            </div>

            {/* Field judgments panel */}
            <div className="flex flex-col rounded-lg border border-border bg-card shadow-sm lg:col-span-3">
              {/* Panel header */}
              <div className="shrink-0 border-b border-border/50 px-5 py-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-[14px] font-semibold text-foreground">
                    Field Judgments
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-muted-foreground/60">
                      {fieldCompletionCount}/{REVIEWABLE_FIELDS.length} reviewed
                    </span>
                    {confirmAllCorrect ? (
                      <div className="flex items-center gap-1.5">
                        <span className="text-[11px] text-warning-foreground">Mark all {REVIEWABLE_FIELDS.length} correct?</span>
                        <button
                          onClick={() => { setConfirmAllCorrect(false); handleMarkAllCorrect(); }}
                          className="rounded border border-success/40 bg-success-muted px-2 py-0.5 text-[11px] font-medium text-status-correct transition-colors duration-150"
                        >
                          Yes [A]
                        </button>
                        <button
                          onClick={() => setConfirmAllCorrect(false)}
                          className="rounded border border-border px-2 py-0.5 text-[11px] font-medium text-muted-foreground transition-colors duration-150"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => {
                          if (confirmAllTimerRef.current) clearTimeout(confirmAllTimerRef.current);
                          setConfirmAllCorrect(true);
                          confirmAllTimerRef.current = setTimeout(() => setConfirmAllCorrect(false), 3000);
                        }}
                        className="rounded border border-success/40 bg-success-muted px-2 py-0.5 text-[11px] font-medium text-status-correct transition-colors duration-150 hover:bg-success-muted"
                      >
                        [A] All ✓
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {reviewError && (
                <div className="mx-3 mt-2 rounded border border-error/30 bg-error-muted px-3 py-1.5 text-[12px] text-status-wrong">
                  {reviewError}
                </div>
              )}

              {/* Field rows */}
              <div className="flex-1 overflow-y-auto">
                {REVIEWABLE_FIELDS.map((field, idx) => {
                  const modelVal = parsedResult[field];
                  const gtVal = groundTruth[field];
                  const review = currentReviews[field];
                  const status = judgmentToStatus(review);
                  const isFocused = focusedFieldIdx === idx;
                  const isInReplaceMode =
                    replaceMode?.fieldName === field;
                  const subKey = currentResult
                    ? `${currentResult.id}-${field}`
                    : field;
                  const isBusy = submitting[subKey] ?? false;

                  return (
                    <div
                      key={field}
                      onClick={() => setFocusedFieldIdx(idx)}
                      className={cn(
                        "flex cursor-pointer items-center gap-2 border-b border-border/40 border-l-2 border-l-transparent px-3 py-2 last:border-b-0",
                        isFocused && "border-l-primary bg-accent",
                        isInReplaceMode && "bg-warning-muted",
                      )}
                    >
                      {/* Field label */}
                      <div className="w-[22%] shrink-0">
                        <span className="text-[11px] text-muted-foreground">
                          {field}
                        </span>
                        {isFocused && !isInReplaceMode && (
                          <div className="flex gap-0.5 mt-0.5">
                            {["c", "b", "r", "n"].map((k) => (
                              <span
                                key={k}
                                className="font-mono text-[9px] text-muted-foreground/40"
                              >
                                [{k}]
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Model value */}
                      <div className="min-w-0 flex-1">
                        <span className="block truncate font-mono text-[12px] tabular-nums text-foreground">
                          {formatFieldValue(modelVal)}
                        </span>
                      </div>

                      {/* Reference indicator */}
                      {gtVal !== null && gtVal !== undefined && (
                        <span
                          title={`Reference: ${formatFieldValue(gtVal)}`}
                          className={cn(
                            "shrink-0 rounded px-1 py-0.5 font-mono text-[10px]",
                            valuesMatch(modelVal, gtVal)
                              ? "bg-success-muted text-status-correct"
                              : "bg-error-muted text-status-wrong",
                          )}
                        >
                          {valuesMatch(modelVal, gtVal) ? "= ref" : "\u2260 ref"}
                        </span>
                      )}

                      {/* Replace input or judgment buttons */}
                      {isInReplaceMode ? (
                        <div className="flex items-center gap-1 shrink-0">
                          <input
                            ref={replaceInputRef}
                            type="text"
                            value={replaceMode!.draftValue}
                            onChange={(e) =>
                              setReplaceMode((prev) =>
                                prev
                                  ? { ...prev, draftValue: e.target.value }
                                  : null,
                              )
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                e.preventDefault();
                                commitReplace();
                              } else if (e.key === "Escape") {
                                e.preventDefault();
                                setReplaceMode(null);
                              }
                            }}
                            className="w-28 rounded border border-warning/60 px-2 py-0.5 font-mono text-[12px] focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                          <span className="shrink-0 text-[10px] text-muted-foreground/50">
                            ↵ save · Esc cancel
                          </span>
                        </div>
                      ) : (
                        <div className="flex shrink-0 items-center gap-0.5">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleJudgment(field, 1, null);
                            }}
                            disabled={isBusy}
                            title="Correct (C)"
                            className={cn(
                              "rounded p-1 transition-colors",
                              review?.is_correct === 1
                                ? "text-status-correct"
                                : "text-muted-foreground/30 hover:text-status-correct",
                              "disabled:opacity-40",
                            )}
                          >
                            <CheckCircle2 size={16} />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleJudgment(field, 0, null);
                            }}
                            disabled={isBusy}
                            title="Wrong → Blank (B)"
                            className={cn(
                              "rounded p-1 transition-colors",
                              review?.is_correct === 0 &&
                                review.correct_value === null
                                ? "text-warning"
                                : "text-muted-foreground/30 hover:text-warning",
                              "disabled:opacity-40",
                            )}
                          >
                            <MinusCircle size={16} />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              const existingReview = currentReviews[field];
                              setReplaceMode({
                                fieldName: field,
                                fieldIdx: idx,
                                draftValue:
                                  existingReview?.correct_value ?? "",
                              });
                              setFocusedFieldIdx(idx);
                            }}
                            disabled={isBusy}
                            title="Wrong → Replace (R)"
                            className={cn(
                              "rounded p-1 transition-colors",
                              review?.is_correct === 0 &&
                                review.correct_value !== null
                                ? "text-status-wrong"
                                : "text-muted-foreground/30 hover:text-status-wrong",
                              "disabled:opacity-40",
                            )}
                          >
                            <PenLine size={16} />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleJudgment(field, -1, null);
                            }}
                            disabled={isBusy}
                            title="Can't Assess (N)"
                            className={cn(
                              "rounded p-1 transition-colors",
                              review?.is_correct === -1
                                ? "text-muted-foreground"
                                : "text-muted-foreground/30 hover:text-muted-foreground",
                              "disabled:opacity-40",
                            )}
                          >
                            <HelpCircle size={16} />
                          </button>
                        </div>
                      )}

                      {/* Status badge */}
                      {savedField === field ? (
                        <span className="shrink-0 text-[11px] font-medium text-status-correct animate-pulse">✓</span>
                      ) : (
                        <StatusBadge status={status} size="sm" />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Hotkey legend footer */}
              <div className="shrink-0 border-t border-border/50 px-3 py-2">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  {[
                    ["C", "Correct"],
                    ["B", "Blank"],
                    ["R", "Replace"],
                    ["N", "N/A"],
                    ["Esc", "Reset"],
                    ["\u2191\u2193", "Field"],
                    ["\u2190\u2192", "Posting"],
                    ["A", "All \u2713"],
                    ["J", "Jump"],
                  ].map(([key, label]) => (
                    <span
                      key={key}
                      className="flex items-center gap-1 text-[10px] text-muted-foreground/50"
                    >
                      <kbd className="rounded border border-border/50 bg-muted px-1 py-0.5 font-mono text-[10px] text-muted-foreground">
                        {key}
                      </kbd>
                      {label}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Empty results state */}
      {selectedRunId && !loadingData && results.length === 0 && (
        <div className="mt-6 flex items-center justify-center py-16">
          <div className="text-[13px] text-muted-foreground">
            No results found for this run
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default function AccuracyPage() {
  return (
    <Suspense fallback={null}>
      <AccuracyPageContent />
    </Suspense>
  );
}
