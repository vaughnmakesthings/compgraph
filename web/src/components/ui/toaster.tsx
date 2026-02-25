"use client";

import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      toastOptions={{
        style: {
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          fontSize: "14px",
          borderRadius: "var(--radius-md, 6px)",
          border: "1px solid var(--color-border, #BFC0C0)",
          color: "var(--color-foreground, #2D3142)",
        },
      }}
    />
  );
}
