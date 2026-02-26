"use client";

import { useState } from "react";
import * as RadixTooltip from "@radix-ui/react-tooltip";
import {
  useFloating,
  autoUpdate,
  offset,
  flip,
  shift,
  useHover,
  useFocus,
  useDismiss,
  useRole,
  useInteractions,
  FloatingPortal,
} from "@floating-ui/react";
import type { Variant } from "./comparison-panel";

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const tooltipStyle: React.CSSProperties = {
  backgroundColor: "#2D3142",
  color: "#FFFFFF",
  fontFamily: "var(--font-body)",
  fontSize: 12,
  padding: "5px 10px",
  borderRadius: 4,
  maxWidth: 220,
  lineHeight: 1.4,
  zIndex: 50,
};

const triggerStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  padding: "6px 12px",
  border: "1px dashed #BFC0C0",
  borderRadius: 6,
  backgroundColor: "#FAFAF7",
  fontFamily: "var(--font-body)",
  fontSize: 13,
  color: "#4F5D75",
  cursor: "default",
};

const TOOLTIP_TEXT = "Pipeline runs scrape → enrich → aggregate in sequence. Each stage must complete before the next begins.";

// ---------------------------------------------------------------------------
// Variant 1: CSS-only (title attribute)
// ---------------------------------------------------------------------------

function CSSTooltip() {
  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <span title={TOOLTIP_TEXT} style={triggerStyle}>
        Hover me (title attr)
      </span>
      <span
        style={{ ...triggerStyle, position: "relative" }}
        className="css-tooltip-trigger"
      >
        Hover me (CSS ::after)
        <style>{`
          .css-tooltip-trigger::after {
            content: '${TOOLTIP_TEXT.replace(/'/g, "\\'")}';
            position: absolute;
            bottom: calc(100% + 6px);
            left: 50%;
            transform: translateX(-50%);
            background: #2D3142;
            color: #FFF;
            font-family: var(--font-body);
            font-size: 12px;
            padding: 5px 10px;
            border-radius: 4px;
            max-width: 220px;
            white-space: normal;
            line-height: 1.4;
            pointer-events: none;
            opacity: 0;
            transition: opacity 150ms;
            z-index: 50;
          }
          .css-tooltip-trigger:hover::after {
            opacity: 1;
          }
        `}</style>
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 2: Radix UI Tooltip
// ---------------------------------------------------------------------------

function RadixTooltipDemo() {
  return (
    <RadixTooltip.Provider delayDuration={200}>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <RadixTooltip.Root>
          <RadixTooltip.Trigger asChild>
            <span style={triggerStyle}>Hover me</span>
          </RadixTooltip.Trigger>
          <RadixTooltip.Portal>
            <RadixTooltip.Content style={tooltipStyle} sideOffset={6}>
              {TOOLTIP_TEXT}
              <RadixTooltip.Arrow style={{ fill: "#2D3142" }} />
            </RadixTooltip.Content>
          </RadixTooltip.Portal>
        </RadixTooltip.Root>

        <RadixTooltip.Root>
          <RadixTooltip.Trigger asChild>
            <span style={triggerStyle}>With arrow</span>
          </RadixTooltip.Trigger>
          <RadixTooltip.Portal>
            <RadixTooltip.Content style={tooltipStyle} side="right" sideOffset={6}>
              Positioned to the right
              <RadixTooltip.Arrow style={{ fill: "#2D3142" }} />
            </RadixTooltip.Content>
          </RadixTooltip.Portal>
        </RadixTooltip.Root>
      </div>
    </RadixTooltip.Provider>
  );
}

// ---------------------------------------------------------------------------
// Variant 3: Floating UI
// ---------------------------------------------------------------------------

function FloatingTooltipItem({ text, label }: { text: string; label: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const { refs, floatingStyles, context } = useFloating({
    open: isOpen,
    onOpenChange: setIsOpen,
    placement: "top",
    whileElementsMounted: autoUpdate,
    middleware: [offset(6), flip(), shift({ padding: 8 })],
  });

  const hover = useHover(context, { move: false });
  const focus = useFocus(context);
  const dismiss = useDismiss(context);
  const role = useRole(context, { role: "tooltip" });
  const { getReferenceProps, getFloatingProps } = useInteractions([hover, focus, dismiss, role]);

  return (
    <>
      <span ref={refs.setReference} {...getReferenceProps()} style={triggerStyle}>
        {label}
      </span>
      {isOpen && (
        <FloatingPortal>
          {/* eslint-disable-next-line react-hooks/refs -- Floating UI's setFloating is a callback ref designed for render-time access */}
          <div ref={refs.setFloating} style={{ ...tooltipStyle, ...floatingStyles }} {...getFloatingProps()}>
            {text}
          </div>
        </FloatingPortal>
      )}
    </>
  );
}

function FloatingTooltipDemo() {
  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <FloatingTooltipItem text={TOOLTIP_TEXT} label="Hover me" />
      <FloatingTooltipItem text="Auto-repositions on scroll/resize" label="Smart placement" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant definitions
// ---------------------------------------------------------------------------

export const tooltipVariants: Variant[] = [
  {
    id: "css-tooltip",
    name: "CSS Only",
    library: "title attr + CSS ::after",
    render: () => <CSSTooltip />,
    scorecard: {
      bundleKb: "0",
      tokenCompliance: "partial",
      a11y: "built-in",
      propsNeeded: 0,
      notes:
        "Title attribute: zero CSS control, OS-rendered, accessible. CSS ::after: styleable but no portal (clips in overflow:hidden parents), no smart repositioning, no keyboard trigger.",
    },
  },
  {
    id: "radix-tooltip",
    name: "Radix UI",
    library: "@radix-ui/react-tooltip",
    render: () => <RadixTooltipDemo />,
    scorecard: {
      bundleKb: "~6",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 6,
      notes:
        "Provider/Root/Trigger/Content pattern. Portal rendering, configurable delay, built-in arrow, ARIA tooltip role. Side/align positioning. Already in project dependencies.",
    },
  },
  {
    id: "floating-tooltip",
    name: "Floating UI",
    library: "@floating-ui/react",
    render: () => <FloatingTooltipDemo />,
    scorecard: {
      bundleKb: "~8",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 12,
      notes:
        "Low-level positioning engine (successor to Popper.js). Middleware system for flip/shift/offset. Must compose hover/focus/dismiss/role hooks manually. Maximum control over positioning logic.",
    },
  },
];
