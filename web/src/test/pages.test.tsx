import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MarketPage from "../app/market/page";
import HiringPage from "../app/hiring/page";
import SettingsPage from "../app/settings/page";
import type { DailyVelocity, CoverageGap, PostingListResponse } from "../lib/types";

vi.mock("../lib/api-client", () => ({
  api: {
    getVelocity: vi.fn(),
    getCoverageGaps: vi.fn(),
    listPostings: vi.fn(),
    getCompanies: vi.fn(),
    health: vi.fn(),
    triggerAggregation: vi.fn(),
    getPipelineRuns: vi.fn(),
    getSchedulerStatus: vi.fn(),
    triggerScrape: vi.fn(),
    pauseScrape: vi.fn(),
    resumeScrape: vi.fn(),
    stopScrape: vi.fn(),
    forceStopScrape: vi.fn(),
    getScrapeStatus: vi.fn(),
    triggerEnrichment: vi.fn(),
    getEnrichStatus: vi.fn(),
    triggerSchedulerJob: vi.fn(),
    pauseSchedulerJob: vi.fn(),
    resumeSchedulerJob: vi.fn(),
  },
}));

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 800, height: 400 }}>{children}</div>
    ),
    AreaChart: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="area-chart">{children}</div>
    ),
    Area: ({ name }: { name: string }) => <div data-testid={`area-${name}`}>{name}</div>,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
  };
});

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

import { api } from "../lib/api-client";

const mockVelocity: DailyVelocity[] = [
  {
    date: "2026-02-01",
    company_id: "troc",
    company_name: "T-ROC",
    new_postings: 10,
    closed_postings: 2,
    active_postings: 80,
  },
  {
    date: "2026-02-01",
    company_id: "bds",
    company_name: "BDS",
    new_postings: 5,
    closed_postings: 1,
    active_postings: 40,
  },
];

const mockGaps: CoverageGap[] = [
  {
    market: "Miami",
    state: "FL",
    companies_present: ["troc"],
    companies_absent: ["bds", "marketsource"],
  },
];

const mockPostingsResponse: PostingListResponse = {
  items: [
    {
      id: "posting-1",
      company_id: "troc-uuid",
      company_name: "T-ROC",
      company_slug: "troc",
      title: "Field Marketing Rep",
      location: "Miami, FL",
      first_seen_at: "2026-01-15T10:00:00Z",
      last_seen_at: "2026-02-15T10:00:00Z",
      is_active: true,
      role_archetype: "FMR",
      pay_min: 45000,
      pay_max: 65000,
      employment_type: "full_time",
    },
  ],
  total: 1,
};

beforeEach(() => {
  vi.mocked(api.getVelocity).mockResolvedValue(mockVelocity);
  vi.mocked(api.getCoverageGaps).mockResolvedValue(mockGaps);
  vi.mocked(api.listPostings).mockResolvedValue(mockPostingsResponse);
  vi.mocked(api.getCompanies).mockResolvedValue([]);
  vi.mocked(api.health).mockResolvedValue({ status: "ok", version: "0.1.0" });
  vi.mocked(api.triggerAggregation).mockResolvedValue({ status: "started" });
  vi.mocked(api.getPipelineRuns).mockResolvedValue({ scrape_runs: [], enrichment_runs: [] });
  vi.mocked(api.getSchedulerStatus).mockResolvedValue({
    enabled: true,
    schedules: [],
    last_pipeline_finished_at: null,
    last_pipeline_success: null,
    missed_run: false,
  });
  // Return terminal status on mount so resumeIfActive does not start polling
  vi.mocked(api.getScrapeStatus).mockResolvedValue({
    run_id: "",
    status: "success",
    started_at: null,
    finished_at: null,
    total_postings_found: 0,
    total_snapshots_created: 0,
    total_errors: 0,
    companies_succeeded: 0,
    companies_failed: 0,
    company_states: {},
    company_results: {},
  });
  vi.mocked(api.getEnrichStatus).mockResolvedValue({
    run_id: "",
    status: "success",
    started_at: null,
    finished_at: null,
    pass1_result: null,
    pass2_result: null,
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_api_calls: 0,
    total_dedup_saved: 0,
    circuit_breaker_tripped: false,
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

// ────────────────────────────────────────────────────────────────────────────
// Market Overview
// ────────────────────────────────────────────────────────────────────────────

describe("Market Overview page", () => {
  it("renders the Market Overview heading", () => {
    render(<MarketPage />);
    expect(
      screen.getByRole("heading", { name: /market overview/i })
    ).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    render(<MarketPage />);
    expect(
      screen.getByText(/hiring velocity and competitive positioning/i)
    ).toBeInTheDocument();
  });

  it("renders the Posting Velocity section heading", () => {
    render(<MarketPage />);
    expect(
      screen.getByRole("heading", { name: /posting velocity/i })
    ).toBeInTheDocument();
  });

  it("renders the Coverage Gaps section heading", () => {
    render(<MarketPage />);
    expect(
      screen.getByRole("heading", { name: /coverage gaps/i })
    ).toBeInTheDocument();
  });

  it("renders KPI cards after data loads", async () => {
    render(<MarketPage />);
    await waitFor(() =>
      expect(screen.getByText("Total Active Postings")).toBeInTheDocument()
    );
    expect(screen.getByText("Most Active Company")).toBeInTheDocument();
    // "Coverage Gaps" appears as both a KPI card label and a section heading
    expect(screen.getAllByText("Coverage Gaps").length).toBeGreaterThanOrEqual(1);
  });

  it("renders total active postings value from mock data", async () => {
    render(<MarketPage />);
    // totalActive = 80 + 40 = 120
    await waitFor(() =>
      expect(screen.getByText("120")).toBeInTheDocument()
    );
  });

  it("renders the coverage gap market row after data loads", async () => {
    render(<MarketPage />);
    await waitFor(() =>
      expect(screen.getByText("Miami, FL")).toBeInTheDocument()
    );
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Job Feed
// ────────────────────────────────────────────────────────────────────────────

describe("Job Feed page", () => {
  it("renders the Job Feed heading", () => {
    render(<HiringPage />);
    expect(
      screen.getByRole("heading", { name: /job feed/i })
    ).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    render(<HiringPage />);
    expect(
      screen.getByText(/all tracked postings across competitors/i)
    ).toBeInTheDocument();
  });

  it("renders the search input in the filter bar", () => {
    render(<HiringPage />);
    expect(
      screen.getByRole("searchbox", { name: /search postings/i })
    ).toBeInTheDocument();
  });

  it("renders the company filter select", () => {
    render(<HiringPage />);
    expect(
      screen.getByRole("combobox", { name: /filter by company/i })
    ).toBeInTheDocument();
  });

  it("renders the status filter select", () => {
    render(<HiringPage />);
    expect(
      screen.getByRole("combobox", { name: /filter by status/i })
    ).toBeInTheDocument();
  });

  it("renders the role filter select", () => {
    render(<HiringPage />);
    expect(
      screen.getByRole("combobox", { name: /filter by role/i })
    ).toBeInTheDocument();
  });

  it("renders table column headers", () => {
    render(<HiringPage />);
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Company")).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
    // Status column now includes the date — "First Seen" header removed (#182)
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders Prev and Next pagination buttons", () => {
    render(<HiringPage />);
    expect(screen.getByRole("button", { name: /prev/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
  });

  it("disables Prev button on first page", () => {
    render(<HiringPage />);
    expect(screen.getByRole("button", { name: /prev/i })).toBeDisabled();
  });

  it("disables Next button when total fits on one page", async () => {
    // mockPostingsResponse has total: 1, which is < PAGE_SIZE (50)
    render(<HiringPage />);
    await waitFor(() =>
      expect(screen.getByText(/Showing/)).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });

  it("renders posting row after data loads", async () => {
    render(<HiringPage />);
    await waitFor(() =>
      expect(screen.getByText("Field Marketing Rep")).toBeInTheDocument()
    );
    // "T-ROC" appears in both the table row and the company filter dropdown option
    expect(screen.getAllByText("T-ROC").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Miami, FL")).toBeInTheDocument();
  });

  it("filters job feed by status", async () => {
    const user = userEvent.setup();
    render(<HiringPage />);

    await waitFor(() =>
      expect(screen.getByText("Field Marketing Rep")).toBeInTheDocument()
    );

    const statusSelect = screen.getByRole("combobox", { name: /filter by status/i });
    await user.selectOptions(statusSelect, "inactive");

    // The mock posting is active, so filtering for inactive hides it
    await waitFor(() =>
      expect(screen.queryByText("Field Marketing Rep")).not.toBeInTheDocument()
    );
    expect(screen.getByText("No postings match your filters")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Settings
// ────────────────────────────────────────────────────────────────────────────

describe("Settings page", () => {
  it("renders the Settings heading", () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: /^settings$/i })
    ).toBeInTheDocument();
  });

  it("renders the API Health section", () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: /api health/i })
    ).toBeInTheDocument();
  });

  it("renders the Check Health button", () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("button", { name: /check health/i })
    ).toBeInTheDocument();
  });

  it("renders the Pipeline Controls section", () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: /pipeline controls/i })
    ).toBeInTheDocument();
  });

  it("renders the Trigger Aggregation button", () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("button", { name: /trigger aggregation/i })
    ).toBeInTheDocument();
  });

  it("renders enabled Scrape and Enrichment trigger buttons", () => {
    render(<SettingsPage />);
    const scrapeBtn = screen.getByRole("button", { name: /trigger scrape/i });
    const enrichBtn = screen.getByRole("button", { name: /trigger enrichment/i });
    expect(scrapeBtn).not.toBeDisabled();
    expect(enrichBtn).not.toBeDisabled();
  });

  it("renders the System Info section", () => {
    render(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: /system info/i })
    ).toBeInTheDocument();
  });

  it("renders system info key-value rows", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Database")).toBeInTheDocument();
    expect(screen.getByText("Supabase Postgres 17")).toBeInTheDocument();
    expect(screen.getByText("Platform")).toBeInTheDocument();
    expect(screen.getByText("Digital Ocean")).toBeInTheDocument();
  });

  it("shows OK status after health check succeeds", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /check health/i }));

    await waitFor(() =>
      expect(screen.getByText("OK")).toBeInTheDocument()
    );
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Settings — scheduler section
// ────────────────────────────────────────────────────────────────────────────

describe("Settings page — scheduler section", () => {
  it("renders the Scheduler heading", async () => {
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { name: /scheduler/i })).toBeInTheDocument();
  });

  it("shows Enabled badge when scheduler is enabled", async () => {
    render(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("Enabled")).toBeInTheDocument());
  });

  it("shows schedule row and action buttons for active schedule", async () => {
    vi.mocked(api.getSchedulerStatus).mockResolvedValueOnce({
      enabled: true,
      schedules: [
        {
          schedule_id: "daily_pipeline",
          next_fire_time: "2026-02-24T06:00:00Z",
          last_fire_time: "2026-02-23T06:00:00Z",
          paused: false,
        },
      ],
      last_pipeline_finished_at: "2026-02-23T07:00:00Z",
      last_pipeline_success: true,
      missed_run: false,
    });
    render(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("daily_pipeline")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /^trigger$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^pause$/i })).toBeInTheDocument();
  });

  it("shows Resume button for a paused schedule", async () => {
    vi.mocked(api.getSchedulerStatus).mockResolvedValueOnce({
      enabled: true,
      schedules: [
        {
          schedule_id: "daily_pipeline",
          next_fire_time: null,
          last_fire_time: null,
          paused: true,
        },
      ],
      last_pipeline_finished_at: null,
      last_pipeline_success: null,
      missed_run: false,
    });
    render(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("daily_pipeline")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /^resume$/i })).toBeInTheDocument();
  });

  it("shows missed run warning when missed_run is true", async () => {
    vi.mocked(api.getSchedulerStatus).mockResolvedValueOnce({
      enabled: true,
      schedules: [],
      last_pipeline_finished_at: "2026-02-20T10:00:00Z",
      last_pipeline_success: false,
      missed_run: true,
    });
    render(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByText(/no pipeline completed in the last 80 hours/i)
      ).toBeInTheDocument()
    );
  });

  it("shows 'Could not load scheduler status' when API fails", async () => {
    vi.mocked(api.getSchedulerStatus).mockRejectedValueOnce(new Error("network"));
    render(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(/could not load scheduler status/i)).toBeInTheDocument()
    );
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Settings — trigger error handling
// ────────────────────────────────────────────────────────────────────────────

describe("Settings page — trigger errors", () => {
  it("shows error banner when Trigger Scrape fails", async () => {
    vi.mocked(api.triggerScrape).mockRejectedValueOnce(new Error("Backend unreachable"));
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /trigger scrape/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument()
    );
    expect(screen.getByText(/scrape error/i)).toBeInTheDocument();
  });

  it("shows error banner when Trigger Enrichment fails", async () => {
    vi.mocked(api.triggerEnrichment).mockRejectedValueOnce(new Error("Backend unreachable"));
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /trigger enrichment/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument()
    );
    expect(screen.getByText(/enrichment error/i)).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Settings — run history with data
// ────────────────────────────────────────────────────────────────────────────

describe("Settings page — run history with data", () => {
  beforeEach(() => {
    vi.mocked(api.getPipelineRuns).mockResolvedValue({
      scrape_runs: [
        {
          id: "run-1",
          company_name: "T-ROC",
          company_slug: "troc",
          status: "completed",
          started_at: "2026-02-23T10:00:00Z",
          completed_at: "2026-02-23T10:05:00Z",
          jobs_found: 42,
          snapshots_created: 10,
          postings_closed: 2,
        },
      ],
      enrichment_runs: [
        {
          id: "enrich-1",
          status: "completed",
          started_at: "2026-02-23T10:06:00Z",
          finished_at: "2026-02-23T10:10:00Z",
          pass1_total: 100,
          pass1_succeeded: 95,
          pass2_total: 95,
          pass2_succeeded: 90,
        },
      ],
    });
  });

  it("renders company name in scrape run history", async () => {
    render(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("T-ROC")).toBeInTheDocument());
  });

  it("renders pass1 succeeded count in enrichment run history", async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      const cells = screen.getAllByText("95");
      expect(cells.length).toBeGreaterThan(0);
    });
  });
});
