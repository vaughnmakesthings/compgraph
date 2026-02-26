"use client";

import { useState } from "react";
import * as RadixCheckbox from "@radix-ui/react-checkbox";
import * as RadixSwitch from "@radix-ui/react-switch";
import { Switch as HeadlessSwitch } from "@headlessui/react";
import { CheckIcon } from "@heroicons/react/24/outline";
import type { Variant } from "./comparison-panel";

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const groupStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 16,
  fontFamily: "var(--font-body)",
  fontSize: 13,
};

const rowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
};

const labelText: React.CSSProperties = { color: "#2D3142" };
const hintText: React.CSSProperties = { fontSize: 11, color: "#4F5D75", marginTop: 2 };
const sectionLabel: React.CSSProperties = { fontSize: 11, fontWeight: 600, color: "#4F5D75", textTransform: "uppercase" as const, letterSpacing: 0.5, margin: "0 0 8px" };

// ---------------------------------------------------------------------------
// Variant 1: Native HTML inputs
// ---------------------------------------------------------------------------

function NativeInputs() {
  const [checked, setChecked] = useState(true);
  const [toggle, setToggle] = useState(false);
  const [radio, setRadio] = useState("daily");

  return (
    <div style={groupStyle}>
      <div>
        <div style={sectionLabel}>Checkbox</div>
        <label style={rowStyle}>
          <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} style={{ width: 16, height: 16, accentColor: "#EF8354" }} />
          <div>
            <div style={labelText}>Enable auto-enrichment</div>
            <div style={hintText}>Run enrichment after each scrape cycle</div>
          </div>
        </label>
      </div>
      <div>
        <div style={sectionLabel}>Toggle</div>
        <label style={rowStyle}>
          <input type="checkbox" role="switch" checked={toggle} onChange={(e) => setToggle(e.target.checked)} style={{ width: 16, height: 16, accentColor: "#1B998B" }} />
          <div style={labelText}>Pipeline active</div>
        </label>
      </div>
      <div>
        <div style={sectionLabel}>Radio Group</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {["daily", "weekly", "manual"].map((v) => (
            <label key={v} style={rowStyle}>
              <input type="radio" name="native-freq" value={v} checked={radio === v} onChange={() => setRadio(v)} style={{ width: 16, height: 16, accentColor: "#EF8354" }} />
              <span style={labelText}>{v.charAt(0).toUpperCase() + v.slice(1)}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 2: Radix UI primitives
// ---------------------------------------------------------------------------

function RadixInputs() {
  const [checked, setChecked] = useState<boolean | "indeterminate">(true);
  const [toggle, setToggle] = useState(false);
  const [radio, setRadio] = useState("daily");

  const checkboxRoot: React.CSSProperties = {
    width: 18,
    height: 18,
    borderRadius: 4,
    border: "2px solid #BFC0C0",
    backgroundColor: checked ? "#EF8354" : "#FFFFFF",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    transition: "background-color 150ms, border-color 150ms",
    borderColor: checked ? "#EF8354" : "#BFC0C0",
    flexShrink: 0,
  };

  const switchRoot: React.CSSProperties = {
    width: 36,
    height: 20,
    borderRadius: 10,
    backgroundColor: toggle ? "#1B998B" : "#BFC0C0",
    position: "relative",
    cursor: "pointer",
    border: "none",
    transition: "background-color 150ms",
    flexShrink: 0,
  };

  const switchThumb: React.CSSProperties = {
    display: "block",
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: "#FFFFFF",
    transition: "transform 150ms",
    transform: toggle ? "translateX(18px)" : "translateX(2px)",
    marginTop: 2,
  };

  const radioBtn = (active: boolean): React.CSSProperties => ({
    width: 18,
    height: 18,
    borderRadius: 9,
    border: `2px solid ${active ? "#EF8354" : "#BFC0C0"}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    flexShrink: 0,
  });

  return (
    <div style={groupStyle}>
      <div>
        <div style={sectionLabel}>Checkbox</div>
        <div style={rowStyle}>
          <RadixCheckbox.Root checked={checked === true} onCheckedChange={setChecked} style={checkboxRoot}>
            <RadixCheckbox.Indicator>
              <CheckIcon style={{ width: 12, height: 12, color: "#FFFFFF", strokeWidth: 3 }} />
            </RadixCheckbox.Indicator>
          </RadixCheckbox.Root>
          <div>
            <div style={labelText}>Enable auto-enrichment</div>
            <div style={hintText}>Run enrichment after each scrape cycle</div>
          </div>
        </div>
      </div>
      <div>
        <div style={sectionLabel}>Toggle</div>
        <div style={rowStyle}>
          <RadixSwitch.Root checked={toggle} onCheckedChange={setToggle} style={switchRoot}>
            <RadixSwitch.Thumb style={switchThumb} />
          </RadixSwitch.Root>
          <div style={labelText}>Pipeline active</div>
        </div>
      </div>
      <div>
        <div style={sectionLabel}>Radio Group</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {["daily", "weekly", "manual"].map((v) => (
            <div key={v} style={rowStyle} onClick={() => setRadio(v)}>
              <div style={radioBtn(radio === v)}>
                {radio === v && <div style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: "#EF8354" }} />}
              </div>
              <span style={labelText}>{v.charAt(0).toUpperCase() + v.slice(1)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 3: Headless UI
// ---------------------------------------------------------------------------

function HeadlessInputs() {
  const [checked, setChecked] = useState(true);
  const [toggle, setToggle] = useState(false);
  const [radio, setRadio] = useState("daily");

  const switchStyle = (on: boolean): React.CSSProperties => ({
    width: 36,
    height: 20,
    borderRadius: 10,
    backgroundColor: on ? "#1B998B" : "#BFC0C0",
    position: "relative",
    cursor: "pointer",
    border: "none",
    transition: "background-color 150ms",
    flexShrink: 0,
  });

  const thumbStyle = (on: boolean): React.CSSProperties => ({
    display: "block",
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: "#FFFFFF",
    transition: "transform 150ms",
    transform: on ? "translateX(18px)" : "translateX(2px)",
    position: "absolute",
    top: 2,
    left: 0,
  });

  return (
    <div style={groupStyle}>
      <div>
        <div style={sectionLabel}>Toggle (as checkbox)</div>
        <div style={rowStyle}>
          <HeadlessSwitch checked={checked} onChange={setChecked} style={switchStyle(checked)}>
            <span style={thumbStyle(checked)} />
          </HeadlessSwitch>
          <div>
            <div style={labelText}>Enable auto-enrichment</div>
            <div style={hintText}>Run enrichment after each scrape cycle</div>
          </div>
        </div>
      </div>
      <div>
        <div style={sectionLabel}>Toggle</div>
        <div style={rowStyle}>
          <HeadlessSwitch checked={toggle} onChange={setToggle} style={switchStyle(toggle)}>
            <span style={thumbStyle(toggle)} />
          </HeadlessSwitch>
          <div style={labelText}>Pipeline active</div>
        </div>
      </div>
      <div>
        <div style={sectionLabel}>Radio-like (switches)</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {["daily", "weekly", "manual"].map((v) => (
            <div key={v} style={rowStyle}>
              <HeadlessSwitch checked={radio === v} onChange={() => setRadio(v)} style={switchStyle(radio === v)}>
                <span style={thumbStyle(radio === v)} />
              </HeadlessSwitch>
              <span style={labelText}>{v.charAt(0).toUpperCase() + v.slice(1)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant definitions
// ---------------------------------------------------------------------------

export const inputVariants: Variant[] = [
  {
    id: "native-inputs",
    name: "Native HTML",
    library: "vanilla checkbox/radio/switch",
    render: () => <NativeInputs />,
    scorecard: {
      bundleKb: "0",
      tokenCompliance: "none",
      a11y: "built-in",
      propsNeeded: 0,
      notes:
        "Zero dependency. accent-color provides basic theming. OS-native rendering for checkbox/radio — cannot fully customize appearance. role=\"switch\" on checkbox gives toggle semantics.",
    },
  },
  {
    id: "radix-inputs",
    name: "Radix UI",
    library: "@radix-ui/react-checkbox + switch",
    render: () => <RadixInputs />,
    scorecard: {
      bundleKb: "~6",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 8,
      notes:
        "Unstyled primitives — full visual control. Checkbox supports indeterminate state. Switch has proper ARIA role. Composable indicator pattern for custom checkmarks. Separate packages keep bundle lean.",
    },
  },
  {
    id: "headless-inputs",
    name: "Headless UI",
    library: "@headlessui/react Switch",
    render: () => <HeadlessInputs />,
    scorecard: {
      bundleKb: "~10",
      tokenCompliance: "full",
      a11y: "built-in",
      propsNeeded: 4,
      notes:
        "Switch component only — no Checkbox or RadioGroup primitives (uses Switch for all toggle states). Simpler API but less semantic variety. Checked/onChange controlled pattern.",
    },
  },
];
