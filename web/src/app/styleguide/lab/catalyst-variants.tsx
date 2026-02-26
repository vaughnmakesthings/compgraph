"use client";

import { useState, useRef, useCallback, Fragment } from "react";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  DialogBackdrop,
  Transition,
  TransitionChild,
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
  Checkbox,
  Switch,
  Field,
  Label,
  Description,
  Radio,
  RadioGroup,
} from "@headlessui/react";
import {
  ChevronUpDownIcon,
  CheckIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import clsx from "clsx";
import type { Variant } from "./comparison-panel";
import { TABLE_DATA, STATUS_COLORS, type Posting } from "./table-variants";

// ---------------------------------------------------------------------------
// 1. Dialog
// ---------------------------------------------------------------------------

function CatalystDialog() {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
      >
        Open Dialog
      </button>

      <Transition show={open}>
        <Dialog onClose={() => setOpen(false)} className="relative z-50">
          <TransitionChild
            enter="duration-200 ease-out"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="duration-150 ease-in"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <DialogBackdrop className="fixed inset-0 bg-zinc-950/25" />
          </TransitionChild>

          <div className="fixed inset-0 flex items-center justify-center p-4">
            <TransitionChild
              enter="duration-200 ease-out"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="duration-150 ease-in"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <DialogPanel className="w-full max-w-md rounded-2xl bg-white p-6 shadow-lg ring-1 ring-zinc-950/10">
                <DialogTitle className="text-base font-semibold text-zinc-900">
                  Confirm Action
                </DialogTitle>
                <p className="mt-2 text-sm text-zinc-500">
                  Are you sure you want to proceed? This will update the
                  pipeline configuration for the selected company.
                </p>
                <div className="mt-6 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    className="rounded-lg px-3 py-1.5 text-sm font-medium text-zinc-500 hover:bg-zinc-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    className="rounded-lg bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
                  >
                    Confirm
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </Dialog>
      </Transition>
    </div>
  );
}

export const catalystDialogVariant: Variant = {
  id: "catalyst-dialog",
  name: "Catalyst",
  library: "@tailwindlabs/catalyst (Headless UI + Tailwind)",
  render: () => <CatalystDialog />,
  scorecard: {
    bundleKb: "~12",
    tokenCompliance: "full",
    a11y: "built-in",
    propsNeeded: 5,
    notes:
      "Tailwind Labs' official UI kit. Pre-styled Headless UI primitives with zinc palette. Copy-paste distribution model -- you own the source. Clean, production-ready defaults with minimal configuration.",
  },
};

// ---------------------------------------------------------------------------
// 2. Select (Listbox)
// ---------------------------------------------------------------------------

const COMPANIES = [
  { value: "troc", label: "T-ROC" },
  { value: "bds", label: "BDS" },
  { value: "marketsource", label: "MarketSource" },
  { value: "osl", label: "OSL" },
  { value: "2020", label: "2020 Companies" },
];

const STATUS_OPTIONS = [
  { value: "all", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "stale", label: "Stale" },
  { value: "closed", label: "Closed" },
];

function CatalystSelect() {
  const [company, setCompany] = useState(COMPANIES[0]);
  const [status, setStatus] = useState(STATUS_OPTIONS[0]);

  return (
    <div className="flex flex-wrap gap-4">
      <div className="min-w-[160px] flex-1">
        <span className="mb-1 block text-xs font-semibold text-zinc-500">
          Company
        </span>
        <Listbox value={company} onChange={setCompany}>
          <div className="relative">
            <ListboxButton className="relative w-full rounded-lg border border-zinc-300 bg-white py-1.5 pl-3 pr-10 text-left text-sm text-zinc-900 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900">
              <span className="block truncate">{company.label}</span>
              <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <ChevronUpDownIcon className="h-4 w-4 text-zinc-400" />
              </span>
            </ListboxButton>
            <Transition
              leave="transition-opacity duration-100 ease-in"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <ListboxOptions className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-xl bg-white py-1 shadow-lg ring-1 ring-zinc-200 focus:outline-none">
                {COMPANIES.map((c) => (
                  <ListboxOption key={c.value} value={c} as={Fragment}>
                    {({ selected, focus }) => (
                      <div
                        className={clsx(
                          "relative cursor-pointer select-none py-2 pl-9 pr-4 text-sm",
                          focus ? "bg-zinc-100 text-zinc-900" : "text-zinc-700",
                        )}
                      >
                        <span
                          className={clsx(
                            "block truncate",
                            selected && "font-semibold",
                          )}
                        >
                          {c.label}
                        </span>
                        {selected && (
                          <span className="absolute inset-y-0 left-0 flex items-center pl-2.5">
                            <CheckIcon className="h-4 w-4 text-zinc-900" />
                          </span>
                        )}
                      </div>
                    )}
                  </ListboxOption>
                ))}
              </ListboxOptions>
            </Transition>
          </div>
        </Listbox>
      </div>

      <div className="min-w-[160px] flex-1">
        <span className="mb-1 block text-xs font-semibold text-zinc-500">
          Status
        </span>
        <Listbox value={status} onChange={setStatus}>
          <div className="relative">
            <ListboxButton className="relative w-full rounded-lg border border-zinc-300 bg-white py-1.5 pl-3 pr-10 text-left text-sm text-zinc-900 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900">
              <span className="block truncate">{status.label}</span>
              <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <ChevronUpDownIcon className="h-4 w-4 text-zinc-400" />
              </span>
            </ListboxButton>
            <Transition
              leave="transition-opacity duration-100 ease-in"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <ListboxOptions className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-xl bg-white py-1 shadow-lg ring-1 ring-zinc-200 focus:outline-none">
                {STATUS_OPTIONS.map((s) => (
                  <ListboxOption key={s.value} value={s} as={Fragment}>
                    {({ selected, focus }) => (
                      <div
                        className={clsx(
                          "relative cursor-pointer select-none py-2 pl-9 pr-4 text-sm",
                          focus ? "bg-zinc-100 text-zinc-900" : "text-zinc-700",
                        )}
                      >
                        <span
                          className={clsx(
                            "block truncate",
                            selected && "font-semibold",
                          )}
                        >
                          {s.label}
                        </span>
                        {selected && (
                          <span className="absolute inset-y-0 left-0 flex items-center pl-2.5">
                            <CheckIcon className="h-4 w-4 text-zinc-900" />
                          </span>
                        )}
                      </div>
                    )}
                  </ListboxOption>
                ))}
              </ListboxOptions>
            </Transition>
          </div>
        </Listbox>
      </div>
    </div>
  );
}

export const catalystSelectVariant: Variant = {
  id: "catalyst-select",
  name: "Catalyst",
  library: "@tailwindlabs/catalyst (Headless UI + Tailwind)",
  render: () => <CatalystSelect />,
  scorecard: {
    bundleKb: "~12",
    tokenCompliance: "full",
    a11y: "built-in",
    propsNeeded: 6,
    notes:
      "Headless UI Listbox with Tailwind utility styling. Zinc palette, rounded-xl dropdown, ring-1 border, chevron indicator. Transition component handles open/close animation. Full keyboard nav and ARIA built-in.",
  },
};

// ---------------------------------------------------------------------------
// 3. Table
// ---------------------------------------------------------------------------

function CatalystStatusBadge({ status }: { status: Posting["status"] }) {
  const colors = STATUS_COLORS[status];
  return (
    <span
      className="inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold capitalize"
      style={{ backgroundColor: colors.bg, color: colors.text }}
    >
      {status}
    </span>
  );
}

function CatalystTable() {
  const [sortCol, setSortCol] = useState<keyof Posting>("postedDate");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = [...TABLE_DATA].sort((a, b) => {
    const av = a[sortCol];
    const bv = b[sortCol];
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  const handleSort = (col: keyof Posting) => {
    if (col === sortCol) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortCol(col);
      setSortDir("asc");
    }
  };

  const arrow = (col: keyof Posting) =>
    sortCol === col ? (sortDir === "asc" ? " \u2191" : " \u2193") : "";

  const headers: { key: keyof Posting; label: string }[] = [
    { key: "company", label: "Company" },
    { key: "title", label: "Title" },
    { key: "location", label: "Location" },
    { key: "payMin", label: "Pay" },
    { key: "status", label: "Status" },
    { key: "postedDate", label: "Posted" },
  ];

  return (
    <div className="max-h-80 overflow-y-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr>
            {headers.map((h) => (
              <th
                key={h.key}
                onClick={() => handleSort(h.key)}
                className="cursor-pointer select-none whitespace-nowrap border-b border-zinc-950/10 px-3 py-2 text-xs font-medium text-zinc-500"
              >
                {h.label}
                {arrow(h.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr
              key={row.id}
              className="border-b border-zinc-950/5 transition-colors hover:bg-zinc-50"
            >
              <td className="px-3 py-2 font-medium text-zinc-950">
                {row.company}
              </td>
              <td className="px-3 py-2 text-zinc-500">{row.title}</td>
              <td className="px-3 py-2 text-zinc-500">{row.location}</td>
              <td className="px-3 py-2 font-mono text-xs text-zinc-500">
                ${row.payMin}&ndash;${row.payMax}/hr
              </td>
              <td className="px-3 py-2">
                <CatalystStatusBadge status={row.status} />
              </td>
              <td className="px-3 py-2 font-mono text-xs text-zinc-500">
                {row.postedDate}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const catalystTableVariant: Variant = {
  id: "catalyst-table",
  name: "Catalyst",
  library: "@tailwindlabs/catalyst (Tailwind table)",
  render: () => <CatalystTable />,
  scorecard: {
    bundleKb: "~0",
    tokenCompliance: "full",
    a11y: "manual",
    propsNeeded: 0,
    notes:
      "Native HTML table styled with Tailwind utilities matching Catalyst's Table component. Zinc-950 headers, zinc-950/5 row borders, hover:bg-zinc-50 rows. No outer border -- clean, minimal aesthetic. Sorting is manual.",
  },
};

// ---------------------------------------------------------------------------
// 4. Tooltip
// ---------------------------------------------------------------------------

const TOOLTIP_TEXT =
  "Pipeline runs scrape \u2192 enrich \u2192 aggregate in sequence. Each stage must complete before the next begins.";

function CatalystTooltipTrigger({
  text,
  label,
}: {
  text: string;
  label: string;
}) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = () => {
    timeoutRef.current = setTimeout(() => setVisible(true), 200);
  };

  const hide = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  };

  return (
    <span
      className="relative inline-flex cursor-default items-center gap-1.5 rounded-md border border-dashed border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-500"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      tabIndex={0}
      role="button"
      aria-describedby={visible ? "catalyst-tooltip" : undefined}
    >
      {label}
      {visible && (
        <span
          id="catalyst-tooltip"
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-2 max-w-[220px] -translate-x-1/2 rounded-md bg-zinc-900 px-2.5 py-1.5 text-xs leading-snug text-white shadow-lg"
        >
          {text}
          <span className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-zinc-900" />
        </span>
      )}
    </span>
  );
}

function CatalystTooltip() {
  return (
    <div className="flex flex-wrap gap-4">
      <CatalystTooltipTrigger text={TOOLTIP_TEXT} label="Hover me" />
      <CatalystTooltipTrigger
        text="Auto-dismiss on mouse leave"
        label="With arrow"
      />
    </div>
  );
}

export const catalystTooltipVariant: Variant = {
  id: "catalyst-tooltip",
  name: "Catalyst",
  library: "@tailwindlabs/catalyst (Tailwind tooltip)",
  render: () => <CatalystTooltip />,
  scorecard: {
    bundleKb: "~0",
    tokenCompliance: "full",
    a11y: "manual",
    propsNeeded: 2,
    notes:
      "Simple hover tooltip using useState + delay. Zinc-900 bg, white text, rounded-md, shadow-lg. CSS arrow via border trick. No portal rendering -- positioned absolutely within trigger's relative container.",
  },
};

// ---------------------------------------------------------------------------
// 5. Toast
// ---------------------------------------------------------------------------

interface CatalystToastItem {
  id: number;
  message: string;
  type: "success" | "error" | "info";
}

const TOAST_ICONS = {
  success: CheckCircleIcon,
  error: XCircleIcon,
  info: InformationCircleIcon,
} as const;

const TOAST_ICON_COLORS = {
  success: "text-green-500",
  error: "text-red-500",
  info: "text-blue-500",
} as const;

function CatalystToast() {
  const [toasts, setToasts] = useState<CatalystToastItem[]>([]);
  const idRef = useRef(0);

  const add = useCallback(
    (message: string, type: CatalystToastItem["type"]) => {
      const id = ++idRef.current;
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(
        () => setToasts((prev) => prev.filter((t) => t.id !== id)),
        3000,
      );
    },
    [],
  );

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => add("Pipeline completed successfully", "success")}
          className="rounded-lg border border-green-300 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-50"
        >
          Success
        </button>
        <button
          type="button"
          onClick={() => add("Scraper failed: timeout", "error")}
          className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
        >
          Error
        </button>
        <button
          type="button"
          onClick={() => add("Enrichment batch queued", "info")}
          className="rounded-lg border border-blue-300 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50"
        >
          Info
        </button>
      </div>
      <div className="relative mt-3 min-h-[60px]">
        {toasts.map((t) => {
          const Icon = TOAST_ICONS[t.type];
          const iconColor = TOAST_ICON_COLORS[t.type];
          return (
            <div
              key={t.id}
              className="mb-2 flex items-start gap-3 rounded-xl bg-white p-3 shadow-lg ring-1 ring-zinc-200 animate-in fade-in slide-in-from-bottom-2 duration-200"
            >
              <Icon className={clsx("mt-0.5 h-5 w-5 shrink-0", iconColor)} />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-zinc-900">{t.message}</p>
                <p className="mt-0.5 text-xs text-zinc-500">Just now</p>
              </div>
              <button
                type="button"
                onClick={() =>
                  setToasts((prev) => prev.filter((x) => x.id !== t.id))
                }
                className="shrink-0 text-zinc-400 hover:text-zinc-600"
                aria-label="Dismiss"
              >
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M4 4l8 8M12 4l-8 8" />
                </svg>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const catalystToastVariant: Variant = {
  id: "catalyst-toast",
  name: "Catalyst",
  library: "@tailwindlabs/catalyst (Tailwind toast)",
  render: () => <CatalystToast />,
  scorecard: {
    bundleKb: "~0",
    tokenCompliance: "full",
    a11y: "manual",
    propsNeeded: 0,
    notes:
      "Custom toast with useState + setTimeout. White bg, rounded-xl, shadow-lg, ring-1 ring-zinc-200. Heroicon indicators: CheckCircle (green-500), XCircle (red-500), InformationCircle (blue-500). Zinc-900 message, zinc-500 timestamp.",
  },
};

// ---------------------------------------------------------------------------
// 6. Input (Checkbox / Switch / Radio)
// ---------------------------------------------------------------------------

function CatalystInputs() {
  const [checked, setChecked] = useState(true);
  const [toggle, setToggle] = useState(false);
  const [radio, setRadio] = useState("daily");

  return (
    <div className="flex flex-col gap-5 text-sm">
      {/* Checkbox */}
      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
          Checkbox
        </p>
        <Field className="flex items-start gap-3">
          <Checkbox
            checked={checked}
            onChange={setChecked}
            className={clsx(
              "mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded border-2 transition-colors",
              checked
                ? "border-zinc-900 bg-zinc-900"
                : "border-zinc-300 bg-white",
            )}
          >
            {checked && (
              <CheckIcon className="h-3 w-3 text-white" strokeWidth={3} />
            )}
          </Checkbox>
          <div>
            <Label className="text-sm text-zinc-900">
              Enable auto-enrichment
            </Label>
            <Description className="text-[11px] text-zinc-500">
              Run enrichment after each scrape cycle
            </Description>
          </div>
        </Field>
      </div>

      {/* Switch */}
      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
          Toggle
        </p>
        <Field className="flex items-center gap-3">
          <Switch
            checked={toggle}
            onChange={setToggle}
            className={clsx(
              "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
              toggle ? "bg-zinc-900" : "bg-zinc-200",
            )}
          >
            <span
              className={clsx(
                "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm ring-0 transition-transform",
                toggle ? "translate-x-4" : "translate-x-0",
              )}
            />
          </Switch>
          <Label className="text-sm text-zinc-900">Pipeline active</Label>
        </Field>
      </div>

      {/* Radio */}
      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
          Radio Group
        </p>
        <RadioGroup
          value={radio}
          onChange={setRadio}
          className="flex flex-col gap-2"
        >
          {["daily", "weekly", "manual"].map((v) => (
            <Field key={v} className="flex items-center gap-3">
              <Radio
                value={v}
                className={clsx(
                  "flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                  radio === v ? "border-zinc-900" : "border-zinc-300",
                )}
              >
                {radio === v && (
                  <span className="h-2 w-2 rounded-full bg-zinc-900" />
                )}
              </Radio>
              <Label className="text-sm text-zinc-900">
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </Label>
            </Field>
          ))}
        </RadioGroup>
      </div>
    </div>
  );
}

export const catalystInputVariant: Variant = {
  id: "catalyst-inputs",
  name: "Catalyst",
  library: "@tailwindlabs/catalyst (Headless UI + Tailwind)",
  render: () => <CatalystInputs />,
  scorecard: {
    bundleKb: "~12",
    tokenCompliance: "full",
    a11y: "built-in",
    propsNeeded: 6,
    notes:
      "Headless UI Checkbox, Switch, Radio, RadioGroup with Field/Label/Description pattern. Zinc-900 checked bg, white checkmark, rounded borders. Full keyboard nav and ARIA semantics built-in.",
  },
};
