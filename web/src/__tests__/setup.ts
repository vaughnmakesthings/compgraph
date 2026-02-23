import "@testing-library/jest-dom/vitest";
import "vitest-axe/extend-expect";
import * as matchers from "vitest-axe/matchers";
import { cleanup } from "@testing-library/react";
import { afterEach, expect, vi } from "vitest";

// Type augmentation for vitest-axe matchers
declare module "vitest" {
  interface Assertion {
    toHaveNoViolations(): void;
  }
  interface AsymmetricMatchersContaining {
    toHaveNoViolations(): void;
  }
}

// Polyfill ResizeObserver for jsdom (required by Radix UI Tooltip/Popper)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

expect.extend(matchers);

afterEach(() => {
  cleanup();
  try {
    localStorage.clear();
  } catch {
    // localStorage may not be available in all jsdom environments
  }
  vi.restoreAllMocks();
});
