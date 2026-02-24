import { render, screen } from "@testing-library/react";
import { KpiCard } from "@/components/data/kpi-card";
import { Badge } from "@/components/data/badge";
import { Callout } from "@/components/content/callout";
import { BarChart } from "@/components/charts/bar-chart";
import { AreaChart } from "@/components/charts/area-chart";
import { DonutChart } from "@/components/charts/donut-chart";

// Tremor charts use Recharts internally; jsdom has no layout engine.
// Mock Tremor chart components to render testable HTML.
global.ResizeObserver = class ResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
};

vi.mock("@tremor/react", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@tremor/react")>();
  return {
    ...mod,
    BarChart: ({ data, categories }: { data: Record<string, unknown>[]; categories: string[] }) => (
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
    AreaChart: ({ data, categories }: { data: Record<string, unknown>[]; categories: string[] }) => (
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
      <div data-testid="pie-chart">
        <div data-testid="chart-data" style={{ display: "none" }}>
          {JSON.stringify(data)}
        </div>
        <div data-testid="pie" />
      </div>
    ),
  };
});

// ────────────────────────────────────────────────────────────────────────────
// KpiCard
// ────────────────────────────────────────────────────────────────────────────

describe("KpiCard", () => {
  it("renders label and numeric value", () => {
    render(<KpiCard label="Active Jobs" value={42} />);
    expect(screen.getByText("Active Jobs")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders label and string value", () => {
    render(<KpiCard label="Enrichment Rate" value="94.2%" />);
    expect(screen.getByText("Enrichment Rate")).toBeInTheDocument();
    expect(screen.getByText("94.2%")).toBeInTheDocument();
  });

  it("renders positive trend with up arrow", () => {
    render(
      <KpiCard
        label="New Postings"
        value={120}
        trend={{ value: 12, label: "vs last week" }}
      />
    );
    expect(screen.getByText(/12%/)).toBeInTheDocument();
    expect(screen.getByText(/↑/)).toBeInTheDocument();
  });

  it("renders negative trend with down arrow", () => {
    render(
      <KpiCard
        label="Closed Postings"
        value={8}
        trend={{ value: -5, label: "vs last week" }}
      />
    );
    expect(screen.getByText(/5%/)).toBeInTheDocument();
    expect(screen.getByText(/↓/)).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(
      <KpiCard
        label="Companies"
        value={4}
        icon={<span aria-label="companies icon">C</span>}
      />
    );
    expect(screen.getByLabelText("companies icon")).toBeInTheDocument();
  });

  it("renders all variant types without crashing", () => {
    const variants = ["default", "success", "warning", "error"] as const;
    variants.forEach((variant) => {
      const { unmount } = render(
        <KpiCard label={variant} value={0} variant={variant} />
      );
      expect(screen.getByText(variant)).toBeInTheDocument();
      unmount();
    });
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Badge
// ────────────────────────────────────────────────────────────────────────────

describe("Badge", () => {
  it("renders success variant with text", () => {
    render(<Badge variant="success">Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders warning variant with text", () => {
    render(<Badge variant="warning">Review</Badge>);
    expect(screen.getByText("Review")).toBeInTheDocument();
  });

  it("renders error variant with text", () => {
    render(<Badge variant="error">Failed</Badge>);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("renders neutral variant with text", () => {
    render(<Badge variant="neutral">Pending</Badge>);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("renders info variant with text", () => {
    render(<Badge variant="info">Draft</Badge>);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("renders sm size without crashing", () => {
    render(
      <Badge variant="success" size="sm">
        Tiny
      </Badge>
    );
    expect(screen.getByText("Tiny")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Callout
// ────────────────────────────────────────────────────────────────────────────

describe("Callout", () => {
  it("renders title and body text for finding variant", () => {
    render(
      <Callout variant="finding" title="Key Finding">
        T-ROC is the only agency hiring in Miami.
      </Callout>
    );
    expect(screen.getByText("Key Finding")).toBeInTheDocument();
    expect(
      screen.getByText("T-ROC is the only agency hiring in Miami.")
    ).toBeInTheDocument();
  });

  it("renders positive variant", () => {
    render(
      <Callout variant="positive" title="Opportunity">
        BDS expanded into 3 new markets.
      </Callout>
    );
    expect(screen.getByText("Opportunity")).toBeInTheDocument();
    expect(screen.getByText("BDS expanded into 3 new markets.")).toBeInTheDocument();
  });

  it("renders risk variant", () => {
    render(
      <Callout variant="risk" title="Risk Signal">
        MarketSource cut 40% of field roles.
      </Callout>
    );
    expect(screen.getByText("Risk Signal")).toBeInTheDocument();
  });

  it("renders caution variant", () => {
    render(
      <Callout variant="caution" title="Watch">
        Enrichment confidence dropped below threshold.
      </Callout>
    );
    expect(screen.getByText("Watch")).toBeInTheDocument();
  });

  it("renders React children nodes", () => {
    render(
      <Callout variant="finding" title="Complex content">
        <strong>Bold signal</strong> with additional text.
      </Callout>
    );
    expect(screen.getByText("Bold signal")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// BarChart
// ────────────────────────────────────────────────────────────────────────────

describe("BarChart", () => {
  const chartData = [
    { month: "Jan", postings: 45, enriched: 40 },
    { month: "Feb", postings: 62, enriched: 58 },
    { month: "Mar", postings: 38, enriched: 35 },
  ];

  const bars = [
    { dataKey: "postings", name: "Postings" },
    { dataKey: "enriched", name: "Enriched" },
  ];

  it("renders without crashing", () => {
    render(<BarChart data={chartData} bars={bars} xDataKey="month" />);
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("renders a bar series for each bar definition", () => {
    render(<BarChart data={chartData} bars={bars} xDataKey="month" />);
    expect(screen.getByTestId("bar-postings")).toBeInTheDocument();
    expect(screen.getByTestId("bar-enriched")).toBeInTheDocument();
  });

  it("renders bar series names as text", () => {
    render(<BarChart data={chartData} bars={bars} xDataKey="month" />);
    expect(screen.getByText("postings")).toBeInTheDocument();
    expect(screen.getByText("enriched")).toBeInTheDocument();
  });

  it("accepts custom height prop without crashing", () => {
    render(
      <BarChart data={chartData} bars={bars} xDataKey="month" height={400} />
    );
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// AreaChart
// ────────────────────────────────────────────────────────────────────────────

describe("AreaChart", () => {
  const chartData = [
    { week: "W1", velocity: 12 },
    { week: "W2", velocity: 18 },
    { week: "W3", velocity: 9 },
  ];

  const areas = [{ dataKey: "velocity", name: "Hiring Velocity" }];

  it("renders without crashing", () => {
    render(<AreaChart data={chartData} areas={areas} xDataKey="week" />);
    expect(screen.getByTestId("area-chart")).toBeInTheDocument();
  });

  it("renders an area series for each area definition", () => {
    render(<AreaChart data={chartData} areas={areas} xDataKey="week" />);
    expect(screen.getByTestId("area-velocity")).toBeInTheDocument();
  });

  it("renders area series name as text", () => {
    render(<AreaChart data={chartData} areas={areas} xDataKey="week" />);
    expect(screen.getByText("velocity")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// DonutChart
// ────────────────────────────────────────────────────────────────────────────

describe("DonutChart", () => {
  const slices = [
    { name: "T-ROC", value: 142 },
    { name: "BDS", value: 87 },
    { name: "2020 Companies", value: 63 },
  ];

  it("renders without crashing", () => {
    render(<DonutChart data={slices} />);
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });

  it("renders a Pie element for the data", () => {
    render(<DonutChart data={slices} />);
    expect(screen.getByTestId("pie")).toBeInTheDocument();
  });

  it("renders with centerLabel prop without crashing", () => {
    render(<DonutChart data={slices} centerLabel="Total Postings" />);
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });

  it("accepts custom height without crashing", () => {
    render(<DonutChart data={slices} height={400} />);
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });
});
