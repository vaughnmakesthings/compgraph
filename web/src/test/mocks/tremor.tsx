/**
 * Tremor chart mocks for jsdom tests.
 *
 * Usage — simple stub (no data rendering):
 *   vi.mock("@tremor/react", async () => {
 *     const { tremorMockSimple } = await import("./mocks/tremor");
 *     return tremorMockSimple();
 *   });
 *
 * Usage — with data rendering (for tests that assert on chart data):
 *   vi.mock("@tremor/react", async () => {
 *     const { tremorMockWithData } = await import("./mocks/tremor");
 *     return tremorMockWithData();
 *   });
 *
 * Usage — with categories rendering (for tests that assert on category labels):
 *   vi.mock("@tremor/react", async () => {
 *     const { tremorMockWithCategories } = await import("./mocks/tremor");
 *     return tremorMockWithCategories();
 *   });
 */

/** Common dialog stubs shared by all factories */
function dialogStubs() {
  return {
    Dialog: ({
      open,
      children,
    }: {
      open: boolean;
      onClose: () => void;
      children: React.ReactNode;
    }) => {
      if (!open) return null;
      return <div role="dialog">{children}</div>;
    },
    DialogPanel: ({ children }: { children: React.ReactNode }) => (
      <div>{children}</div>
    ),
  };
}

/** Bare stubs — render testid divs only */
export function tremorMockSimple() {
  return {
    ...dialogStubs(),
    BarChart: () => <div data-testid="bar-chart" />,
    AreaChart: () => <div data-testid="area-chart" />,
    DonutChart: () => <div data-testid="donut-chart" />,
  };
}

/** Render chart data as hidden JSON (for asserting on passed data) */
export function tremorMockWithData() {
  return {
    ...dialogStubs(),
    BarChart: ({ data }: { data: Record<string, unknown>[] }) => (
      <div data-testid="bar-chart">
        <div data-testid="chart-data" style={{ display: "none" }}>
          {JSON.stringify(data)}
        </div>
      </div>
    ),
    AreaChart: () => <div data-testid="area-chart" />,
    DonutChart: () => <div data-testid="donut-chart" />,
  };
}

/** Render chart data + category labels (for asserting on both) */
export function tremorMockWithCategories() {
  return {
    ...dialogStubs(),
    BarChart: ({
      data,
      categories,
    }: {
      data: Record<string, unknown>[];
      categories: string[];
    }) => (
      <div data-testid="bar-chart">
        <div data-testid="chart-data" style={{ display: "none" }}>
          {JSON.stringify(data)}
        </div>
        {categories.map((c) => (
          <div key={c} data-testid={`bar-${c}`}>
            {c}
          </div>
        ))}
      </div>
    ),
    AreaChart: ({
      data,
      categories,
    }: {
      data: Record<string, unknown>[];
      categories: string[];
    }) => (
      <div data-testid="area-chart">
        <div data-testid="chart-data" style={{ display: "none" }}>
          {JSON.stringify(data)}
        </div>
        {categories.map((c) => (
          <div key={c} data-testid={`area-${c}`}>
            {c}
          </div>
        ))}
      </div>
    ),
    DonutChart: ({ data }: { data: { name: string; value: number }[] }) => (
      <div data-testid="donut-chart">
        <div data-testid="chart-data" style={{ display: "none" }}>
          {JSON.stringify(data)}
        </div>
        <div data-testid="pie" />
      </div>
    ),
  };
}
