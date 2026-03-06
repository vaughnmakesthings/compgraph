"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { ExclamationTriangleIcon, ArrowPathIcon } from "@heroicons/react/24/outline";

export default function EvalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center py-24 px-4">
      <div
        className="w-full max-w-md rounded-lg border bg-white p-6 shadow-sm"
        style={{
          borderColor: "var(--color-silver)",
          boxShadow: "var(--shadow-sm)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <div className="flex items-start gap-3">
          <ExclamationTriangleIcon
            className="h-5 w-5 shrink-0 mt-0.5"
            style={{ color: "var(--color-chestnut)" }}
            aria-hidden="true"
          />
          <div className="flex-1 min-w-0">
            <h2
              className="text-base font-semibold"
              style={{
                fontFamily: "var(--font-display)",
                color: "var(--color-jet-black)",
              }}
            >
              Evaluation error
            </h2>
            <p
              className="mt-1 text-sm"
              style={{
                fontFamily: "var(--font-body)",
                color: "var(--color-blue-slate)",
              }}
            >
              Failed to load evaluation data. Please try again.
            </p>
            {error.digest && (
              <p
                className="mt-2 text-xs"
                style={{
                  fontFamily: "var(--font-mono)",
                  color: "var(--color-silver)",
                }}
              >
                Error ID: {error.digest}
              </p>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={reset}
          className="mt-4 flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition-opacity hover:opacity-80"
          style={{
            fontFamily: "var(--font-body)",
            backgroundColor: "var(--color-jet-black)",
            color: "#FFFFFF",
            borderRadius: "var(--radius-md)",
          }}
        >
          <ArrowPathIcon className="h-3.5 w-3.5" aria-hidden="true" />
          Try again
        </button>
      </div>
    </div>
  );
}
