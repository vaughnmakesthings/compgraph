"use client";

import { useEffect, useRef, useState } from "react";
import {
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
} from "@headlessui/react";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  /** Shown during async onConfirm. Defaults to "Confirming…". */
  confirmingLabel?: string;
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
  confirmingLabel = "Confirming…",
  cancelLabel = "Cancel",
  confirmVariant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  const [confirming, setConfirming] = useState(false);
  const dismissedRef = useRef(false);

  useEffect(() => {
    if (!open) {
      setConfirming(false);
      dismissedRef.current = false;
    }
  }, [open]);

  function handleClose() {
    if (confirming) dismissedRef.current = true;
    onOpenChange(false);
  }

  async function handleConfirm() {
    dismissedRef.current = false;
    let isAsync = false;
    try {
      const result = onConfirm();
      if (result && typeof result.then === "function") {
        isAsync = true;
        setConfirming(true);
        await result;
      }
      if (!dismissedRef.current) handleClose();
    } catch (err) {
      console.error("ConfirmDialog onConfirm failed:", err);
    } finally {
      if (isAsync) setConfirming(false);
    }
  }

  const isDanger = confirmVariant === "danger";

  return (
    <Dialog open={open} onClose={handleClose} className="relative z-50">
      <DialogBackdrop
        transition
        className="fixed inset-0 bg-gray-500/50 transition-opacity data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in"
      />
      <div className="fixed inset-0 z-50 w-screen overflow-y-auto">
        <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <DialogPanel
            transition
            className="relative transform overflow-hidden rounded-lg bg-white px-4 pt-5 pb-4 text-left shadow-xl transition-all data-closed:translate-y-4 data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in sm:my-8 sm:w-full sm:max-w-lg sm:p-6 data-closed:sm:translate-y-0 data-closed:sm:scale-95"
          >
            <div className="sm:flex sm:items-start">
              {isDanger && (
                <div className="mx-auto flex size-12 shrink-0 items-center justify-center rounded-full bg-red-100 sm:mx-0 sm:size-10">
                  <ExclamationTriangleIcon
                    aria-hidden="true"
                    className="size-6 text-red-600"
                  />
                </div>
              )}
              <div
                className={[
                  "mt-3 text-center sm:mt-0 sm:text-left",
                  isDanger ? "sm:ml-4" : "",
                ].join(" ")}
              >
                <DialogTitle
                  as="h3"
                  className="text-base font-semibold text-gray-900"
                  style={{ fontFamily: bodyFont }}
                >
                  {title}
                </DialogTitle>
                <div className="mt-2">
                  <p
                    className="text-sm text-gray-500"
                    style={{ fontFamily: bodyFont }}
                  >
                    {description}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse gap-2">
              <button
                type="button"
                disabled={confirming}
                onClick={() => void handleConfirm()}
                className={[
                  "inline-flex w-full justify-center rounded-md px-3 py-2 text-sm font-semibold text-white shadow-xs sm:w-auto",
                  isDanger
                    ? "bg-red-600 hover:bg-red-500"
                    : "hover:opacity-85",
                ].join(" ")}
                style={{
                  fontFamily: bodyFont,
                  backgroundColor: isDanger ? undefined : "#EF8354",
                  cursor: confirming ? "wait" : "pointer",
                  opacity: confirming ? 0.75 : 1,
                }}
              >
                {confirming ? confirmingLabel : confirmLabel}
              </button>
              <button
                type="button"
                data-autofocus
                onClick={handleClose}
                className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-xs ring-1 ring-gray-300 ring-inset hover:bg-gray-50 sm:mt-0 sm:w-auto"
                style={{ fontFamily: bodyFont }}
              >
                {cancelLabel}
              </button>
            </div>
          </DialogPanel>
        </div>
      </div>
    </Dialog>
  );
}
