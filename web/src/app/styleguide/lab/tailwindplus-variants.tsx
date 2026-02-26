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
  Switch,
  Field,
  Label,
} from "@headlessui/react";
import {
  ChevronUpDownIcon,
  CheckIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import clsx from "clsx";
import type { Variant } from "./comparison-panel";
import { TABLE_DATA, type Posting } from "./table-variants";

// ---------------------------------------------------------------------------
// 1. Dialog
// ---------------------------------------------------------------------------

function TailwindPlusDialog() {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md bg-[#EF8354] px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#e07545] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#EF8354]"
      >
        Open Dialog
      </button>

      <Transition show={open}>
        <Dialog onClose={() => setOpen(false)} className="relative z-50">
          <TransitionChild
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <DialogBackdrop className="fixed inset-0 bg-gray-500/75 transition-opacity" />
          </TransitionChild>

          <div className="fixed inset-0 z-10 w-screen overflow-y-auto">
            <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
              <TransitionChild
                enter="ease-out duration-300"
                enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
                enterTo="opacity-100 translate-y-0 sm:scale-100"
                leave="ease-in duration-200"
                leaveFrom="opacity-100 translate-y-0 sm:scale-100"
                leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              >
                <DialogPanel className="relative overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl ring-1 ring-gray-900/5 sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                  <div>
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#EF8354]/10">
                      <ExclamationTriangleIcon
                        className="h-6 w-6 text-[#EF8354]"
                        aria-hidden="true"
                      />
                    </div>
                    <div className="mt-3 text-center sm:mt-5">
                      <DialogTitle className="text-base font-semibold text-gray-900">
                        Confirm Action
                      </DialogTitle>
                      <div className="mt-2">
                        <p className="text-sm text-gray-500">
                          Are you sure you want to proceed? This will update the
                          pipeline configuration for the selected company.
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                    <button
                      type="button"
                      onClick={() => setOpen(false)}
                      className="inline-flex w-full justify-center rounded-md bg-[#EF8354] px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#e07545] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#EF8354] sm:col-start-2"
                    >
                      Confirm
                    </button>
                    <button
                      type="button"
                      onClick={() => setOpen(false)}
                      className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:mt-0"
                    >
                      Cancel
                    </button>
                  </div>
                </DialogPanel>
              </TransitionChild>
            </div>
          </div>
        </Dialog>
      </Transition>
    </div>
  );
}

export const tailwindPlusDialogVariant: Variant = {
  id: "tailwindplus-dialog",
  name: "Tailwind Plus",
  library: "Headless UI + Tailwind CSS (Tailwind Plus examples)",
  render: () => <TailwindPlusDialog />,
  scorecard: {
    bundleKb: "~10",
    tokenCompliance: "full",
    a11y: "built-in",
    propsNeeded: 6,
    notes:
      "Tailwind Plus component examples — hand-crafted patterns with expressive styling. More decorative than Catalyst (ring/shadow layering, accent colors, icon-led dialogs). Copy-paste from tailwindcss.com/plus.",
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

function TailwindPlusSelect() {
  const [company, setCompany] = useState(COMPANIES[0]);
  const [status, setStatus] = useState(STATUS_OPTIONS[0]);

  return (
    <div className="flex flex-wrap gap-4">
      <div className="min-w-[180px] flex-1">
        <label className="mb-1 block text-sm font-medium text-gray-900">
          Company
        </label>
        <Listbox value={company} onChange={setCompany}>
          <div className="relative">
            <ListboxButton className="relative w-full cursor-pointer rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-sm text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-[#EF8354]">
              <span className="block truncate">{company.label}</span>
              <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <ChevronUpDownIcon
                  className="h-5 w-5 text-gray-400"
                  aria-hidden="true"
                />
              </span>
            </ListboxButton>
            <Transition
              leave="transition-opacity duration-100 ease-in"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 shadow-lg ring-1 ring-black/5 focus:outline-none">
                {COMPANIES.map((c) => (
                  <ListboxOption key={c.value} value={c} as={Fragment}>
                    {({ selected, focus }) => (
                      <div
                        className={clsx(
                          "relative cursor-pointer select-none py-2 pl-3 pr-9 text-sm",
                          focus
                            ? "bg-[#EF8354] text-white"
                            : "text-gray-900",
                        )}
                      >
                        <span
                          className={clsx(
                            "block truncate",
                            selected ? "font-semibold" : "font-normal",
                          )}
                        >
                          {c.label}
                        </span>
                        {selected && (
                          <span
                            className={clsx(
                              "absolute inset-y-0 right-0 flex items-center pr-4",
                              focus ? "text-white" : "text-[#EF8354]",
                            )}
                          >
                            <CheckIcon
                              className="h-5 w-5"
                              aria-hidden="true"
                            />
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

      <div className="min-w-[180px] flex-1">
        <label className="mb-1 block text-sm font-medium text-gray-900">
          Status
        </label>
        <Listbox value={status} onChange={setStatus}>
          <div className="relative">
            <ListboxButton className="relative w-full cursor-pointer rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-sm text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-[#EF8354]">
              <span className="block truncate">{status.label}</span>
              <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <ChevronUpDownIcon
                  className="h-5 w-5 text-gray-400"
                  aria-hidden="true"
                />
              </span>
            </ListboxButton>
            <Transition
              leave="transition-opacity duration-100 ease-in"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 shadow-lg ring-1 ring-black/5 focus:outline-none">
                {STATUS_OPTIONS.map((s) => (
                  <ListboxOption key={s.value} value={s} as={Fragment}>
                    {({ selected, focus }) => (
                      <div
                        className={clsx(
                          "relative cursor-pointer select-none py-2 pl-3 pr-9 text-sm",
                          focus
                            ? "bg-[#EF8354] text-white"
                            : "text-gray-900",
                        )}
                      >
                        <span
                          className={clsx(
                            "block truncate",
                            selected ? "font-semibold" : "font-normal",
                          )}
                        >
                          {s.label}
                        </span>
                        {selected && (
                          <span
                            className={clsx(
                              "absolute inset-y-0 right-0 flex items-center pr-4",
                              focus ? "text-white" : "text-[#EF8354]",
                            )}
                          >
                            <CheckIcon
                              className="h-5 w-5"
                              aria-hidden="true"
                            />
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

export const tailwindPlusSelectVariant: Variant = {
  id: "tailwindplus-select",
  name: "Tailwind Plus",
  library: "Headless UI + Tailwind CSS (Tailwind Plus examples)",
  render: () => <TailwindPlusSelect />,
  scorecard: {
    bundleKb: "~10",
    tokenCompliance: "full",
    a11y: "built-in",
    propsNeeded: 6,
    notes:
      "Headless UI Listbox with Tailwind Plus styling. Coral accent on hover and focus ring, ring-1 ring-inset ring-gray-300 trigger, shadow-lg dropdown with ring-1 ring-black/5. Checkmark indicator in coral. Full keyboard nav and ARIA built-in.",
  },
};

// ---------------------------------------------------------------------------
// 3. Table
// ---------------------------------------------------------------------------

type SortKey = keyof Posting;

function TailwindPlusStatusBadge({ status }: { status: Posting["status"] }) {
  const dotColors: Record<Posting["status"], string> = {
    active: "bg-[#1B998B]",
    stale: "bg-[#DCB256]",
    closed: "bg-[#8C2C23]",
  };

  return (
    <span className="inline-flex items-center gap-x-1.5 rounded-md px-2 py-1 text-xs font-medium text-gray-900 ring-1 ring-inset ring-gray-200">
      <span
        className={clsx("h-1.5 w-1.5 rounded-full", dotColors[status])}
        aria-hidden="true"
      />
      <span className="capitalize">{status}</span>
    </span>
  );
}

function TailwindPlusTable() {
  const [sortCol, setSortCol] = useState<SortKey>("postedDate");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = [...TABLE_DATA].sort((a, b) => {
    const av = a[sortCol];
    const bv = b[sortCol];
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === "asc" ? cmp : -cmp;
  });

  const handleSort = (col: SortKey) => {
    if (col === sortCol) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortCol(col);
      setSortDir("asc");
    }
  };

  const arrow = (col: SortKey) =>
    sortCol === col ? (sortDir === "asc" ? " \u2191" : " \u2193") : "";

  const headers: { key: SortKey; label: string }[] = [
    { key: "company", label: "Company" },
    { key: "title", label: "Title" },
    { key: "location", label: "Location" },
    { key: "payMin", label: "Pay" },
    { key: "status", label: "Status" },
    { key: "postedDate", label: "Posted" },
  ];

  return (
    <div className="overflow-hidden rounded-lg ring-1 ring-gray-300">
      <div className="max-h-80 overflow-y-auto">
        <table className="min-w-full divide-y divide-gray-300">
          <thead className="bg-gray-50">
            <tr>
              {headers.map((h) => (
                <th
                  key={h.key}
                  scope="col"
                  onClick={() => handleSort(h.key)}
                  className="cursor-pointer select-none px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-900"
                >
                  {h.label}
                  {arrow(h.key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {sorted.map((row) => (
              <tr
                key={row.id}
                className="transition-colors hover:bg-gray-50"
              >
                <td className="whitespace-nowrap px-3 py-3 text-sm font-medium text-gray-900">
                  {row.company}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-gray-500">
                  {row.title}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm text-gray-500">
                  {row.location}
                </td>
                <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-gray-500">
                  ${row.payMin}&ndash;${row.payMax}/hr
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-sm">
                  <TailwindPlusStatusBadge status={row.status} />
                </td>
                <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-gray-500">
                  {row.postedDate}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export const tailwindPlusTableVariant: Variant = {
  id: "tailwindplus-table",
  name: "Tailwind Plus",
  library: "Tailwind CSS (Tailwind Plus table examples)",
  render: () => <TailwindPlusTable />,
  scorecard: {
    bundleKb: "~0",
    tokenCompliance: "full",
    a11y: "manual",
    propsNeeded: 0,
    notes:
      "Native HTML table with Tailwind Plus stacked table styling. ring-1 ring-gray-300 container, bg-gray-50 header with uppercase tracking-wide labels, divide-y row borders, dot-badge status pattern. More expressive than Catalyst (ring borders, colored dots).",
  },
};

// ---------------------------------------------------------------------------
// 4. Tooltip
// ---------------------------------------------------------------------------

const TOOLTIP_TEXT =
  "Pipeline runs scrape \u2192 enrich \u2192 aggregate in sequence. Each stage must complete before the next begins.";

function TailwindPlusTooltipTrigger({
  text,
  label,
  id,
}: {
  text: string;
  label: string;
  id: string;
}) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    timeoutRef.current = setTimeout(() => setVisible(true), 150);
  }, []);

  const hide = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(false);
  }, []);

  return (
    <span
      className="relative inline-flex cursor-default items-center gap-1.5 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      tabIndex={0}
      role="button"
      aria-describedby={visible ? id : undefined}
    >
      {label}
      <span
        id={id}
        role="tooltip"
        className={clsx(
          "absolute bottom-full left-1/2 z-50 mb-2 max-w-[240px] -translate-x-1/2 rounded-md bg-gray-900 px-3 py-2 text-sm font-normal text-white shadow-lg transition-opacity duration-150",
          visible ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      >
        {text}
        <span className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
      </span>
    </span>
  );
}

function TailwindPlusTooltip() {
  return (
    <div className="flex flex-wrap gap-4">
      <TailwindPlusTooltipTrigger
        text={TOOLTIP_TEXT}
        label="Hover me"
        id="tp-tooltip-1"
      />
      <TailwindPlusTooltipTrigger
        text="Auto-dismiss on mouse leave"
        label="With arrow"
        id="tp-tooltip-2"
      />
    </div>
  );
}

export const tailwindPlusTooltipVariant: Variant = {
  id: "tailwindplus-tooltip",
  name: "Tailwind Plus",
  library: "Tailwind CSS (Tailwind Plus tooltip pattern)",
  render: () => <TailwindPlusTooltip />,
  scorecard: {
    bundleKb: "~0",
    tokenCompliance: "full",
    a11y: "built-in",
    propsNeeded: 3,
    notes:
      "Pure CSS/JS tooltip with bg-gray-900, white text, rounded-md, shadow-lg. CSS arrow via border trick. Fade transition via opacity. Keyboard accessible (focus/blur triggers). No portal — positioned absolutely within trigger container.",
  },
};

// ---------------------------------------------------------------------------
// 5. Toast / Notification
// ---------------------------------------------------------------------------

interface ToastItem {
  id: number;
  title: string;
  message: string;
  type: "success" | "error" | "info";
}

const TOAST_ICONS = {
  success: CheckCircleIcon,
  error: XCircleIcon,
  info: InformationCircleIcon,
} as const;

const TOAST_ICON_COLORS = {
  success: "text-green-400",
  error: "text-red-400",
  info: "text-blue-400",
} as const;

const TOAST_TITLES: Record<ToastItem["type"], string> = {
  success: "Success",
  error: "Error",
  info: "Information",
};

function TailwindPlusToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const idRef = useRef(0);

  const add = useCallback(
    (title: string, message: string, type: ToastItem["type"]) => {
      const id = ++idRef.current;
      setToasts((prev) => [...prev, { id, title, message, type }]);
      setTimeout(
        () => setToasts((prev) => prev.filter((t) => t.id !== id)),
        4000,
      );
    },
    [],
  );

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() =>
            add(
              TOAST_TITLES.success,
              "Pipeline completed successfully",
              "success",
            )
          }
          className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
        >
          Success
        </button>
        <button
          type="button"
          onClick={() =>
            add(TOAST_TITLES.error, "Scraper failed: timeout", "error")
          }
          className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
        >
          Error
        </button>
        <button
          type="button"
          onClick={() =>
            add(TOAST_TITLES.info, "Enrichment batch queued", "info")
          }
          className="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
        >
          Info
        </button>
      </div>

      <div
        className="mt-3 flex min-h-[60px] flex-col gap-2"
        aria-live="polite"
      >
        {toasts.map((t) => {
          const Icon = TOAST_ICONS[t.type];
          const iconColor = TOAST_ICON_COLORS[t.type];
          return (
            <div
              key={t.id}
              className="pointer-events-auto w-full max-w-sm overflow-hidden rounded-lg bg-white shadow-lg ring-1 ring-black/5"
            >
              <div className="p-4">
                <div className="flex items-start">
                  <div className="shrink-0">
                    <Icon
                      className={clsx("h-6 w-6", iconColor)}
                      aria-hidden="true"
                    />
                  </div>
                  <div className="ml-3 w-0 flex-1 pt-0.5">
                    <p className="text-sm font-medium text-gray-900">
                      {t.title}
                    </p>
                    <p className="mt-1 text-sm text-gray-500">{t.message}</p>
                  </div>
                  <div className="ml-4 flex shrink-0">
                    <button
                      type="button"
                      onClick={() =>
                        setToasts((prev) =>
                          prev.filter((x) => x.id !== t.id),
                        )
                      }
                      className="inline-flex rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[#EF8354] focus:ring-offset-2"
                      aria-label="Dismiss"
                    >
                      <XMarkIcon className="h-5 w-5" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const tailwindPlusToastVariant: Variant = {
  id: "tailwindplus-toast",
  name: "Tailwind Plus",
  library: "Tailwind CSS (Tailwind Plus notification pattern)",
  render: () => <TailwindPlusToast />,
  scorecard: {
    bundleKb: "~0",
    tokenCompliance: "full",
    a11y: "built-in",
    propsNeeded: 3,
    notes:
      "Tailwind Plus notification panel pattern. rounded-lg bg-white shadow-lg ring-1 ring-black/5. Icon left (CheckCircle green-400, XCircle red-400, InformationCircle blue-400) + title/body right + dismiss X. Auto-dismiss after 4s. ARIA live region.",
  },
};

// ---------------------------------------------------------------------------
// 6. Input (Checkbox / Toggle / Radio)
// ---------------------------------------------------------------------------

function TailwindPlusInputs() {
  const [checked, setChecked] = useState(true);
  const [toggle, setToggle] = useState(false);
  const [radio, setRadio] = useState("daily");

  return (
    <div className="flex flex-col gap-6 text-sm">
      {/* Checkbox */}
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Checkbox
        </p>
        <div className="relative flex items-start">
          <div className="flex h-6 items-center">
            <input
              id="tp-checkbox"
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-[#EF8354] focus:ring-[#EF8354]"
              style={{ accentColor: "#EF8354" }}
            />
          </div>
          <div className="ml-3">
            <label
              htmlFor="tp-checkbox"
              className="text-sm font-medium text-gray-900"
            >
              Enable auto-enrichment
            </label>
            <p className="text-sm text-gray-500">
              Run enrichment after each scrape cycle
            </p>
          </div>
        </div>
      </div>

      {/* Toggle */}
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Toggle
        </p>
        <Field className="flex items-center gap-3">
          <Switch
            checked={toggle}
            onChange={setToggle}
            className={clsx(
              "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#EF8354] focus:ring-offset-2",
              toggle ? "bg-[#EF8354]" : "bg-gray-200",
            )}
          >
            <span
              className={clsx(
                "pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm ring-1 ring-gray-900/5 transition-transform duration-200 ease-in-out",
                toggle ? "translate-x-5" : "translate-x-0",
              )}
            />
          </Switch>
          <Label className="text-sm font-medium text-gray-900">
            Pipeline active
          </Label>
        </Field>
      </div>

      {/* Radio */}
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Radio Group
        </p>
        <fieldset>
          <legend className="sr-only">Schedule frequency</legend>
          <div className="flex flex-col gap-3">
            {["daily", "weekly", "manual"].map((v) => (
              <div key={v} className="flex items-center">
                <input
                  id={`tp-radio-${v}`}
                  name="tp-schedule"
                  type="radio"
                  checked={radio === v}
                  onChange={() => setRadio(v)}
                  className="h-4 w-4 border-gray-300 text-[#EF8354] focus:ring-[#EF8354]"
                  style={{ accentColor: "#EF8354" }}
                />
                <label
                  htmlFor={`tp-radio-${v}`}
                  className="ml-3 block text-sm font-medium text-gray-900"
                >
                  {v.charAt(0).toUpperCase() + v.slice(1)}
                </label>
              </div>
            ))}
          </div>
        </fieldset>
      </div>
    </div>
  );
}

export const tailwindPlusInputVariant: Variant = {
  id: "tailwindplus-inputs",
  name: "Tailwind Plus",
  library: "Headless UI + Tailwind CSS (Tailwind Plus examples)",
  render: () => <TailwindPlusInputs />,
  scorecard: {
    bundleKb: "~10",
    tokenCompliance: "full",
    a11y: "built-in",
    propsNeeded: 4,
    notes:
      "Native checkbox/radio with accent-color coral + Headless UI Switch for toggle. Coral accent on all controls. Fieldset with sr-only legend for radio group. Switch uses ring-1 ring-gray-900/5 thumb with shadow-sm, focus:ring-2 focus:ring-[#EF8354].",
  },
};
