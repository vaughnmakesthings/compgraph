/**
 * ResizeObserver polyfill for jsdom (used by Tremor/Recharts).
 * Import this file at the top of any test that renders chart components.
 */
global.ResizeObserver = class ResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
};
