"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import * as RadixDialog from "@radix-ui/react-dialog";
import { Dialog as HeadlessDialog, DialogPanel, DialogTitle, DialogBackdrop } from "@headlessui/react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import type { Variant } from "./comparison-panel";

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(45, 49, 66, 0.4)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 100,
};

const panelStyle: React.CSSProperties = {
  backgroundColor: "#FFFFFF",
  borderRadius: 8,
  padding: 24,
  width: 400,
  maxWidth: "90vw",
  boxShadow: "0 10px 15px rgb(0 0 0 / 0.1)",
  fontFamily: "var(--font-body)",
  position: "relative",
};

const titleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)",
  fontSize: 16,
  fontWeight: 600,
  color: "#2D3142",
  margin: "0 0 8px",
};

const bodyStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#4F5D75",
  lineHeight: 1.6,
  margin: "0 0 20px",
};

const btnStyle: React.CSSProperties = {
  padding: "7px 16px",
  borderRadius: 6,
  border: "none",
  fontFamily: "var(--font-body)",
  fontSize: 13,
  fontWeight: 500,
  cursor: "pointer",
};

const primaryBtn: React.CSSProperties = { ...btnStyle, backgroundColor: "#EF8354", color: "#FFFFFF" };
const secondaryBtn: React.CSSProperties = { ...btnStyle, backgroundColor: "#E8E8E4", color: "#2D3142" };

const closeIconStyle: React.CSSProperties = {
  position: "absolute",
  top: 12,
  right: 12,
  width: 20,
  height: 20,
  color: "#4F5D75",
  cursor: "pointer",
  background: "none",
  border: "none",
  padding: 0,
};

const triggerBtnStyle: React.CSSProperties = {
  ...btnStyle,
  backgroundColor: "#EF8354",
  color: "#FFFFFF",
};

// ---------------------------------------------------------------------------
// Variant 1: Native HTML <dialog>
// ---------------------------------------------------------------------------

function NativeDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);

  const open = useCallback(() => dialogRef.current?.showModal(), []);
  const close = useCallback(() => dialogRef.current?.close(), []);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    const handler = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) close();
    };
    el.addEventListener("click", handler);
    return () => el.removeEventListener("click", handler);
  }, [close]);

  return (
    <div>
      <button type="button" onClick={open} style={triggerBtnStyle}>Open Dialog</button>
      <dialog
        ref={dialogRef}
        style={{
          ...panelStyle,
          border: "none",
          maxHeight: "80vh",
        }}
      >
        <button type="button" onClick={close} style={closeIconStyle} aria-label="Close">
          <XMarkIcon />
        </button>
        <h3 style={titleStyle}>Confirm Action</h3>
        <p style={bodyStyle}>Are you sure you want to proceed? This will update the pipeline configuration for the selected company.</p>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button type="button" onClick={close} style={secondaryBtn}>Cancel</button>
          <button type="button" onClick={close} style={primaryBtn}>Confirm</button>
        </div>
      </dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 2: Radix UI Dialog
// ---------------------------------------------------------------------------

function RadixDialogDemo() {
  return (
    <RadixDialog.Root>
      <RadixDialog.Trigger asChild>
        <button type="button" style={triggerBtnStyle}>Open Dialog</button>
      </RadixDialog.Trigger>
      <RadixDialog.Portal>
        <RadixDialog.Overlay style={overlayStyle}>
          <RadixDialog.Content style={panelStyle}>
            <RadixDialog.Close asChild>
              <button type="button" style={closeIconStyle} aria-label="Close"><XMarkIcon /></button>
            </RadixDialog.Close>
            <RadixDialog.Title style={titleStyle}>Confirm Action</RadixDialog.Title>
            <RadixDialog.Description style={bodyStyle}>
              Are you sure you want to proceed? This will update the pipeline configuration for the selected company.
            </RadixDialog.Description>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <RadixDialog.Close asChild>
                <button type="button" style={secondaryBtn}>Cancel</button>
              </RadixDialog.Close>
              <RadixDialog.Close asChild>
                <button type="button" style={primaryBtn}>Confirm</button>
              </RadixDialog.Close>
            </div>
          </RadixDialog.Content>
        </RadixDialog.Overlay>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

// ---------------------------------------------------------------------------
// Variant 3: Headless UI Dialog
// ---------------------------------------------------------------------------

function HeadlessDialogDemo() {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button type="button" onClick={() => setOpen(true)} style={triggerBtnStyle}>Open Dialog</button>
      <HeadlessDialog open={open} onClose={() => setOpen(false)} style={{ position: "relative", zIndex: 100 }}>
        <DialogBackdrop style={overlayStyle} />
        <div style={{ position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 101 }}>
          <DialogPanel style={panelStyle}>
            <button type="button" onClick={() => setOpen(false)} style={closeIconStyle} aria-label="Close"><XMarkIcon /></button>
            <DialogTitle style={titleStyle}>Confirm Action</DialogTitle>
            <p style={bodyStyle}>Are you sure you want to proceed? This will update the pipeline configuration for the selected company.</p>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button type="button" onClick={() => setOpen(false)} style={secondaryBtn}>Cancel</button>
              <button type="button" onClick={() => setOpen(false)} style={primaryBtn}>Confirm</button>
            </div>
          </DialogPanel>
        </div>
      </HeadlessDialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant definitions
// ---------------------------------------------------------------------------

export const dialogVariants: Variant[] = [
  {
    id: "native-dialog",
    name: "Native HTML",
    library: "vanilla <dialog>",
    render: () => <NativeDialog />,
    scorecard: {
      bundleKb: "0",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 0,
      notes:
        "Zero dependency. showModal() gives built-in backdrop, focus trap, and Escape to close. Backdrop click requires manual implementation. Limited animation support without additional CSS.",
    },
  },
  {
    id: "radix-dialog",
    name: "Radix UI",
    library: "@radix-ui/react-dialog",
    render: () => <RadixDialogDemo />,
    scorecard: {
      bundleKb: "~8",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 8,
      notes:
        "Unstyled primitives with built-in focus trap, scroll lock, and portal rendering. Composable Close/Trigger pattern. Title and Description map to ARIA automatically. Already in project dependencies.",
    },
  },
  {
    id: "headless-dialog",
    name: "Headless UI",
    library: "@headlessui/react Dialog",
    render: () => <HeadlessDialogDemo />,
    scorecard: {
      bundleKb: "~10",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 6,
      notes:
        "open/onClose controlled pattern. Built-in focus trap and scroll lock. DialogBackdrop component for overlay. Simpler API than Radix — fewer wrapper components. Already in project dependencies.",
    },
  },
];
