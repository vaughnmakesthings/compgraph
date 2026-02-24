"use client";

import { useState } from "react";
import { Dialog, DialogPanel } from "@tremor/react";

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmVariant?: "default" | "danger";
  /** May return a Promise; dialog stays open until it resolves. */
  onConfirm: () => void | Promise<void>;
}

const bodyFont = "var(--font-body, 'DM Sans Variable', sans-serif)";

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  confirmVariant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  const [confirming, setConfirming] = useState(false);
  const handleClose = () => onOpenChange(false);

  const handleConfirm = async () => {
    let isAsync = false;
    try {
      const result = onConfirm();
      if (result && typeof result.then === "function") {
        isAsync = true;
        setConfirming(true);
        await result;
      }
    } catch (err) {
      console.error("ConfirmDialog onConfirm failed:", err);
    } finally {
      if (isAsync) {
        setConfirming(false);
      }
      handleClose();
    }
  };

  const confirmBg = confirmVariant === "danger" ? "#8C2C23" : "#EF8354";

  return (
    <Dialog open={open} onClose={handleClose}>
      <DialogPanel
        className="max-w-lg"
        style={{
          fontFamily: bodyFont,
          backgroundColor: "#FFFFFF",
          border: "1px solid #BFC0C0",
          borderRadius: "var(--radius-lg, 8px)",
          padding: "24px",
          boxShadow: "var(--shadow-lg, 0 10px 15px -3px rgb(0 0 0 / 0.10))",
        }}
      >
        <h3
          className="text-lg font-semibold mb-2"
          style={{ color: "#2D3142", fontFamily: bodyFont }}
        >
          {title}
        </h3>
        <p
          className="mb-6 text-sm"
          style={{ color: "#4F5D75", fontFamily: bodyFont }}
        >
          {description}
        </p>
        <div className="flex flex-row gap-3 justify-end">
          <button
            type="button"
            onClick={handleClose}
            style={{
              fontFamily: bodyFont,
              fontSize: "14px",
              padding: "8px 16px",
              borderRadius: "var(--radius-md, 6px)",
              border: "1px solid #BFC0C0",
              color: "#4F5D75",
              backgroundColor: "transparent",
              cursor: "pointer",
            }}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={() => void handleConfirm()}
            disabled={confirming}
            style={{
              fontFamily: bodyFont,
              fontSize: "14px",
              padding: "8px 16px",
              borderRadius: "var(--radius-md, 6px)",
              border: "none",
              color: "#FFFFFF",
              backgroundColor: confirmBg,
              cursor: confirming ? "wait" : "pointer",
              opacity: confirming ? 0.8 : 1,
            }}
          >
            {confirming ? "Starting…" : confirmLabel}
          </button>
        </div>
      </DialogPanel>
    </Dialog>
  );
}
