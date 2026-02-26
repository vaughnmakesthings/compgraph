"use client";

import { useState, Fragment } from "react";
import * as RadixSelect from "@radix-ui/react-select";
import * as RadixDropdownMenu from "@radix-ui/react-dropdown-menu";
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from "@headlessui/react";
import { ChevronDownIcon, CheckIcon } from "@heroicons/react/24/outline";
import type { Variant } from "./comparison-panel";

// ---------------------------------------------------------------------------
// Canonical select data — identical for all variants
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

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const triggerStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 8,
  padding: "7px 12px",
  minWidth: 180,
  border: "1px solid #BFC0C0",
  borderRadius: 6,
  backgroundColor: "#FFFFFF",
  fontFamily: "var(--font-body)",
  fontSize: 13,
  color: "#2D3142",
  cursor: "pointer",
  outline: "none",
};

const dropdownStyle: React.CSSProperties = {
  backgroundColor: "#FFFFFF",
  border: "1px solid #BFC0C0",
  borderRadius: 6,
  boxShadow: "0 4px 6px rgb(0 0 0 / 0.07)",
  padding: 4,
  fontFamily: "var(--font-body)",
  fontSize: 13,
  minWidth: 180,
  zIndex: 50,
};

const itemStyle: React.CSSProperties = {
  padding: "6px 10px 6px 28px",
  borderRadius: 4,
  cursor: "pointer",
  color: "#2D3142",
  position: "relative",
  outline: "none",
};

const checkStyle: React.CSSProperties = {
  position: "absolute",
  left: 8,
  top: "50%",
  transform: "translateY(-50%)",
  width: 14,
  height: 14,
  color: "#1B998B",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontFamily: "var(--font-body)",
  fontSize: 11,
  fontWeight: 600,
  color: "#4F5D75",
  marginBottom: 6,
};

// ---------------------------------------------------------------------------
// Variant 1: Native HTML select
// ---------------------------------------------------------------------------

function NativeSelect() {
  const [company, setCompany] = useState("troc");
  const [status, setStatus] = useState("all");

  const selectStyle: React.CSSProperties = {
    ...triggerStyle,
    appearance: "auto",
    width: "100%",
  };

  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <div style={{ flex: 1, minWidth: 160 }}>
        <label style={labelStyle}>Company</label>
        <select value={company} onChange={(e) => setCompany(e.target.value)} style={selectStyle}>
          {COMPANIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      </div>
      <div style={{ flex: 1, minWidth: 160 }}>
        <label style={labelStyle}>Status</label>
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={selectStyle}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 2: Radix UI Select
// ---------------------------------------------------------------------------

function RadixSelectDemo() {
  const [company, setCompany] = useState("troc");
  const [status, setStatus] = useState("all");

  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <div style={{ flex: 1, minWidth: 160 }}>
        <label style={labelStyle}>Company</label>
        <RadixSelect.Root value={company} onValueChange={setCompany}>
          <RadixSelect.Trigger style={triggerStyle}>
            <RadixSelect.Value />
            <RadixSelect.Icon>
              <ChevronDownIcon style={{ width: 14, height: 14, color: "#4F5D75" }} />
            </RadixSelect.Icon>
          </RadixSelect.Trigger>
          <RadixSelect.Portal>
            <RadixSelect.Content style={dropdownStyle} position="popper" sideOffset={4}>
              <RadixSelect.Viewport>
                {COMPANIES.map((c) => (
                  <RadixSelect.Item key={c.value} value={c.value} style={itemStyle}>
                    <RadixSelect.ItemIndicator style={checkStyle}>
                      <CheckIcon />
                    </RadixSelect.ItemIndicator>
                    <RadixSelect.ItemText>{c.label}</RadixSelect.ItemText>
                  </RadixSelect.Item>
                ))}
              </RadixSelect.Viewport>
            </RadixSelect.Content>
          </RadixSelect.Portal>
        </RadixSelect.Root>
      </div>
      <div style={{ flex: 1, minWidth: 160 }}>
        <label style={labelStyle}>Status</label>
        <RadixSelect.Root value={status} onValueChange={setStatus}>
          <RadixSelect.Trigger style={triggerStyle}>
            <RadixSelect.Value />
            <RadixSelect.Icon>
              <ChevronDownIcon style={{ width: 14, height: 14, color: "#4F5D75" }} />
            </RadixSelect.Icon>
          </RadixSelect.Trigger>
          <RadixSelect.Portal>
            <RadixSelect.Content style={dropdownStyle} position="popper" sideOffset={4}>
              <RadixSelect.Viewport>
                {STATUS_OPTIONS.map((s) => (
                  <RadixSelect.Item key={s.value} value={s.value} style={itemStyle}>
                    <RadixSelect.ItemIndicator style={checkStyle}>
                      <CheckIcon />
                    </RadixSelect.ItemIndicator>
                    <RadixSelect.ItemText>{s.label}</RadixSelect.ItemText>
                  </RadixSelect.Item>
                ))}
              </RadixSelect.Viewport>
            </RadixSelect.Content>
          </RadixSelect.Portal>
        </RadixSelect.Root>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 3: Headless UI Listbox
// ---------------------------------------------------------------------------

function HeadlessListbox() {
  const [company, setCompany] = useState(COMPANIES[0]);
  const [status, setStatus] = useState(STATUS_OPTIONS[0]);

  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <div style={{ flex: 1, minWidth: 160, position: "relative" }}>
        <label style={labelStyle}>Company</label>
        <Listbox value={company} onChange={setCompany}>
          <ListboxButton style={triggerStyle}>
            <span>{company.label}</span>
            <ChevronDownIcon style={{ width: 14, height: 14, color: "#4F5D75" }} />
          </ListboxButton>
          <ListboxOptions style={{ ...dropdownStyle, position: "absolute", top: "100%", left: 0, marginTop: 4 }}>
            {COMPANIES.map((c) => (
              <ListboxOption key={c.value} value={c} as={Fragment}>
                {({ selected, focus }) => (
                  <div style={{ ...itemStyle, backgroundColor: focus ? "#FAFAF7" : "transparent" }}>
                    {selected && <CheckIcon style={checkStyle} />}
                    {c.label}
                  </div>
                )}
              </ListboxOption>
            ))}
          </ListboxOptions>
        </Listbox>
      </div>
      <div style={{ flex: 1, minWidth: 160, position: "relative" }}>
        <label style={labelStyle}>Status</label>
        <Listbox value={status} onChange={setStatus}>
          <ListboxButton style={triggerStyle}>
            <span>{status.label}</span>
            <ChevronDownIcon style={{ width: 14, height: 14, color: "#4F5D75" }} />
          </ListboxButton>
          <ListboxOptions style={{ ...dropdownStyle, position: "absolute", top: "100%", left: 0, marginTop: 4 }}>
            {STATUS_OPTIONS.map((s) => (
              <ListboxOption key={s.value} value={s} as={Fragment}>
                {({ selected, focus }) => (
                  <div style={{ ...itemStyle, backgroundColor: focus ? "#FAFAF7" : "transparent" }}>
                    {selected && <CheckIcon style={checkStyle} />}
                    {s.label}
                  </div>
                )}
              </ListboxOption>
            ))}
          </ListboxOptions>
        </Listbox>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant definitions
// ---------------------------------------------------------------------------

export const selectVariants: Variant[] = [
  {
    id: "native-select",
    name: "Native HTML",
    library: "vanilla <select>",
    render: () => <NativeSelect />,
    scorecard: {
      bundleKb: "0",
      tokenCompliance: "none",
      a11y: "built-in",
      propsNeeded: 0,
      notes:
        "Zero dependency. Browser-native keyboard nav and screen reader support. Cannot be styled beyond basic CSS — dropdown popup uses OS-native rendering. No custom checkmarks, animations, or portaling.",
    },
  },
  {
    id: "radix-select",
    name: "Radix UI",
    library: "@radix-ui/react-select",
    render: () => <RadixSelectDemo />,
    scorecard: {
      bundleKb: "~12",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 10,
      notes:
        "Unstyled primitives — full design token control via style props. Built-in ARIA roles, keyboard navigation, focus management. Portal rendering avoids overflow clipping. Already in project dependencies.",
    },
  },
  {
    id: "headless-listbox",
    name: "Headless UI",
    library: "@headlessui/react Listbox",
    render: () => <HeadlessListbox />,
    scorecard: {
      bundleKb: "~10",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 8,
      notes:
        "Render-prop pattern with focus/selected state exposed. Designed for Tailwind but works with inline styles. Lighter API than Radix — fewer wrapper components needed. Already in project dependencies.",
    },
  },
];
