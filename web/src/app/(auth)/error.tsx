"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { ArrowPathIcon } from "@heroicons/react/24/outline";

export default function AuthError({
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
    <div
      className="flex flex-col items-center justify-center px-4"
      style={{ minHeight: "100vh", backgroundColor: "var(--color-background)" }}
    >
      <div
        className="w-full max-w-sm rounded-lg border bg-white p-6"
        style={{
          borderColor: "var(--color-silver)",
          boxShadow: "var(--shadow-sm)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <h2
          className="text-base font-semibold"
          style={{
            fontFamily: "var(--font-display)",
            color: "var(--color-jet-black)",
          }}
        >
          Authentication error
        </h2>
        <p
          className="mt-1 text-sm"
          style={{
            fontFamily: "var(--font-body)",
            color: "var(--color-blue-slate)",
          }}
        >
          {error.message || "Something went wrong during authentication. Please try again."}
        </p>
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
