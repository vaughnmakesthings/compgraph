import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "../app/(app)/page";
import { api } from "@/lib/api-client";
import type { PipelineStatus, DailyVelocity } from "@/lib/types";

vi.mock("@/lib/api-client", () => ({
  api: {
    getPipelineStatus: vi.fn(),
    getVelocity: vi.fn(),
  },
}));

global.ResizeObserver = class ResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
};

vi.mock("@tremor/react", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@tremor/react")>();
  return {
    ...mod,
    BarChart: ({
      data,
    }: {
      data: Record<string, unknown>[];
    }) => (
      <div data-testid="bar-chart">
        <div data-testid="chart-data" style={{ display: "none" }}>
          {JSON.stringify(data)}
        </div>
      </div>
    ),
    AreaChart: () => <div data-testid="area-chart" />,
    DonutChart: () => <div data-testid="donut-chart" />,
  };
});

const mockStatus: PipelineStatus = {
  status: "idle",
  scrape: {
    current_run: null,
    last_completed_at: "2026-02-23T10:00:00Z",
    next_run_at: "2026-02-23T12:00:00Z",
  },
  enrich: {
    current_run: { pass1_completed: 200, pass2_completed: 180 },
    last_completed_at: "2026-02-23T09:45:00Z",
  },
  scheduler: { next_run_at: "2026-02-23T12:00:00Z" },
};

const today = new Date();
const fmtDate = (d: Date) => d.toISOString().slice(0, 10);
const yesterday = new Date(today);
yesterday.setDate(today.getDate() - 1);
const twoDaysAgo = new Date(today);
twoDaysAgo.setDate(today.getDate() - 2);

// Newest-first order — verifies totalActive uses max-date, not last-write-wins
const mockVelocity: DailyVelocity[] = [
  {
    date: fmtDate(yesterday),
    company_id: "troc",
    company_name: "T-ROC",
    new_postings: 7,
    closed_postings: 3,
    active_postings: 124,
  },
  {
    date: fmtDate(yesterday),
    company_id: "bds",
    company_name: "BDS",
    new_postings: 4,
    closed_postings: 2,
    active_postings: 87,
  },
  {
    date: fmtDate(twoDaysAgo),
    company_id: "troc",
    company_name: "T-ROC",
    new_postings: 5,
    closed_postings: 2,
    active_postings: 120,
  },
  {
    date: fmtDate(twoDaysAgo),
    company_id: "bds",
    company_name: "BDS",
    new_postings: 3,
    closed_postings: 1,
    active_postings: 85,
  },
];

const mockedApi = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DashboardPage", () => {
  it('renders "Pipeline Health" heading', () => {
    mockedApi.getPipelineStatus.mockResolvedValue(mockStatus);
    mockedApi.getVelocity.mockResolvedValue(mockVelocity);

    render(<DashboardPage />);

    expect(
      screen.getByRole("heading", { name: /pipeline health/i })
    ).toBeInTheDocument();
  });

  it("shows subtitle text", () => {
    mockedApi.getPipelineStatus.mockResolvedValue(mockStatus);
    mockedApi.getVelocity.mockResolvedValue(mockVelocity);

    render(<DashboardPage />);

    expect(
      screen.getByText(/hiring activity across tracked competitors/i)
    ).toBeInTheDocument();
  });

  it("shows skeleton loading state initially before data resolves", () => {
    mockedApi.getPipelineStatus.mockReturnValue(new Promise(() => {}));
    mockedApi.getVelocity.mockReturnValue(new Promise(() => {}));

    render(<DashboardPage />);

    const skeletons = document.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThan(0);

    expect(screen.queryByText("Active Postings")).not.toBeInTheDocument();
  });

  it("renders KPI cards when data loads", async () => {
    mockedApi.getPipelineStatus.mockResolvedValue(mockStatus);
    mockedApi.getVelocity.mockResolvedValue(mockVelocity);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Active Postings")).toBeInTheDocument();
    });

    expect(screen.getByText("New This Week")).toBeInTheDocument();
    expect(screen.getByText("Enriched")).toBeInTheDocument();
    expect(screen.getByText("Pipeline Status")).toBeInTheDocument();
  });

  it("displays active postings total derived from velocity data", async () => {
    mockedApi.getPipelineStatus.mockResolvedValue(mockStatus);
    mockedApi.getVelocity.mockResolvedValue(mockVelocity);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Active Postings")).toBeInTheDocument();
    });

    expect(screen.getByText("211")).toBeInTheDocument();
  });

  it("displays enrichment coverage percentage", async () => {
    mockedApi.getPipelineStatus.mockResolvedValue(mockStatus);
    mockedApi.getVelocity.mockResolvedValue(mockVelocity);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("90%")).toBeInTheDocument();
    });
  });

  it("renders the pipeline status badge with idle label", async () => {
    mockedApi.getPipelineStatus.mockResolvedValue(mockStatus);
    mockedApi.getVelocity.mockResolvedValue(mockVelocity);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("idle")).toBeInTheDocument();
    });
  });

  it("renders the bar chart section after data loads", async () => {
    mockedApi.getPipelineStatus.mockResolvedValue(mockStatus);
    mockedApi.getVelocity.mockResolvedValue(mockVelocity);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /daily posting velocity/i })
      ).toBeInTheDocument();
    });

    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("KPI grid has aria-busy during loading and aria-label", () => {
    mockedApi.getPipelineStatus.mockReturnValue(new Promise(() => {}));
    mockedApi.getVelocity.mockReturnValue(new Promise(() => {}));

    render(<DashboardPage />);

    const kpiGrid = screen.getByLabelText("KPI metrics");
    expect(kpiGrid).toHaveAttribute("aria-busy", "true");
    expect(kpiGrid).toHaveAttribute("aria-label", "KPI metrics");
  });

  it("shows an error alert when the API call fails", async () => {
    mockedApi.getPipelineStatus.mockRejectedValue(
      new Error("Network error: /api/pipeline/status")
    );
    mockedApi.getVelocity.mockRejectedValue(
      new Error("Network error: /api/aggregation/velocity")
    );

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });
});
