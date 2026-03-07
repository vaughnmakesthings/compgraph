import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MarketPage from "../app/(app)/market/page";
import HiringPage from "../app/(app)/hiring/page";
import SettingsPage from "../app/(app)/settings/page";
import type { DailyVelocity, CoverageGap, PostingListResponse } from "../lib/types";
import { renderWithQueryClient } from "./test-utils";

vi.mock("../lib/auth-context", () => ({
  useAuth: vi.fn().mockReturnValue({
    session: null,
    user: null,
    role: "admin",
    loading: false,
    signOut: vi.fn(),
  }),
}));

vi.mock("../lib/api-client", () => ({
  api: {},
}));

vi.mock("@/api-client/@tanstack/react-query.gen", async () => {
  const { apiClientRqMock } = await import("./mocks/api-client-rq");
  return apiClientRqMock();
});

vi.mock("@/api-client/sdk.gen", () => ({
  pauseScrapeApiV1ScrapePausePost: vi.fn(),
  resumeScrapeApiV1ScrapeResumePost: vi.fn(),
  stopScrapeApiV1ScrapeStopPost: vi.fn(),
  forceStopScrapeApiV1ScrapeForceStopPost: vi.fn(),
  triggerJobApiV1SchedulerJobsJobIdTriggerPost: vi.fn(),
  pauseJobApiV1SchedulerJobsJobIdPausePost: vi.fn(),
  resumeJobApiV1SchedulerJobsJobIdResumePost: vi.fn(),
}));

vi.mock("@/components/ui/confirm-dialog", () => ({
  ConfirmDialog: ({ open, onConfirm, confirmLabel = "Confirm" }: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    title: string;
    description: string;
    confirmLabel?: string;
    onConfirm: () => void | Promise<void>;
  }) => open ? (
    <div role="dialog">
      <button onClick={() => {
        const result = onConfirm();
        if (result && typeof (result as Promise<void>).catch === "function") {
          (result as Promise<void>).catch(() => {});
        }
      }}>{confirmLabel}</button>
    </div>
  ) : null,
}));

vi.mock("@/components/auth/user-management-section", () => ({
  UserManagementSection: () => <div data-testid="user-mgmt" />,
}));

import "./mocks/resize-observer";
vi.mock("@tremor/react", async () => {
  const { tremorMockSimple } = await import("./mocks/tremor");
  return tremorMockSimple();
});

import {
  getVelocityApiV1AggregationVelocityGetOptions,
  getCoverageGapsApiV1AggregationCoverageGapsGetOptions,
  listPostingsApiV1PostingsGetOptions,
  listCompaniesApiV1CompaniesGetOptions,
  pipelineRunsApiV1PipelineRunsGetOptions,
  schedulerStatusApiV1SchedulerStatusGetOptions,
  scrapeStatusApiV1ScrapeStatusGetOptions,
  enrichStatusApiV1EnrichStatusGetOptions,
  triggerScrapeApiV1ScrapeTriggerPostMutation,
  triggerFullApiV1EnrichTriggerPostMutation,
} from "@/api-client/@tanstack/react-query.gen";

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
      pay_currency: "USD",
      employment_type: "full_time",
    },
  ],
  total: 1,
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function overrideQuery(optionsFn: any, key: string, data: unknown) {
  vi.mocked(optionsFn).mockReturnValue({
    queryKey: [key],
    queryFn: vi.fn().mockResolvedValue(data),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function overrideQueryReject(optionsFn: any, key: string, err: Error) {
  vi.mocked(optionsFn).mockReturnValue({
    queryKey: [key],
    queryFn: vi.fn().mockRejectedValue(err),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
}

beforeEach(() => {
  overrideQuery(getVelocityApiV1AggregationVelocityGetOptions, "velocity", mockVelocity);
  overrideQuery(getCoverageGapsApiV1AggregationCoverageGapsGetOptions, "coverageGaps", mockGaps);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  vi.mocked(listPostingsApiV1PostingsGetOptions).mockImplementation((params?: any) => {
    const isActive = params?.query?.is_active;
    const key = JSON.stringify(params?.query ?? {});
    const data = (isActive === false)
      ? { items: [], total: 0 }
      : mockPostingsResponse;
    return {
      queryKey: ["postings", key],
      queryFn: vi.fn().mockResolvedValue(data),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;
  });
  overrideQuery(listCompaniesApiV1CompaniesGetOptions, "companies", []);
  overrideQuery(pipelineRunsApiV1PipelineRunsGetOptions, "pipelineRuns", { scrape_runs: [], enrichment_runs: [] });
  overrideQuery(schedulerStatusApiV1SchedulerStatusGetOptions, "schedulerStatus", {
    enabled: true,
    schedules: [],
    last_pipeline_finished_at: null,
    last_pipeline_success: null,
    missed_run: false,
  });
  overrideQuery(scrapeStatusApiV1ScrapeStatusGetOptions, "scrapeStatus", {
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
  overrideQuery(enrichStatusApiV1EnrichStatusGetOptions, "enrichStatus", {
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
    renderWithQueryClient(<MarketPage />);
    expect(
      screen.getByRole("heading", { name: /market overview/i })
    ).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    renderWithQueryClient(<MarketPage />);
    expect(
      screen.getByText(/hiring velocity and competitive positioning/i)
    ).toBeInTheDocument();
  });

  it("renders the Posting Velocity section heading", () => {
    renderWithQueryClient(<MarketPage />);
    expect(
      screen.getByRole("heading", { name: /posting velocity/i })
    ).toBeInTheDocument();
  });

  it("renders the Coverage Gaps section heading", () => {
    renderWithQueryClient(<MarketPage />);
    expect(
      screen.getByRole("heading", { name: /coverage gaps/i })
    ).toBeInTheDocument();
  });

  it("renders KPI cards after data loads", async () => {
    renderWithQueryClient(<MarketPage />);
    await waitFor(() =>
      expect(screen.getByText("Total Active Postings")).toBeInTheDocument()
    );
    expect(screen.getByText("Most Active Company")).toBeInTheDocument();
    // "Coverage Gaps" appears as both a KPI card label and a section heading
    expect(screen.getAllByText("Coverage Gaps").length).toBeGreaterThanOrEqual(1);
  });

  it("renders total active postings value from mock data", async () => {
    renderWithQueryClient(<MarketPage />);
    // totalActive = 80 + 40 = 120
    await waitFor(() =>
      expect(screen.getByText("120")).toBeInTheDocument()
    );
  });

  it("renders the coverage gap market row after data loads", async () => {
    renderWithQueryClient(<MarketPage />);
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
    renderWithQueryClient(<HiringPage />);
    expect(
      screen.getByRole("heading", { name: /job feed/i })
    ).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    renderWithQueryClient(<HiringPage />);
    expect(
      screen.getByText(/all tracked postings across competitors/i)
    ).toBeInTheDocument();
  });

  it("renders the search input in the filter bar", () => {
    renderWithQueryClient(<HiringPage />);
    expect(
      screen.getByRole("searchbox", { name: /search postings/i })
    ).toBeInTheDocument();
  });

  it("renders the company filter select", () => {
    renderWithQueryClient(<HiringPage />);
    expect(
      screen.getByRole("combobox", { name: /filter by company/i })
    ).toBeInTheDocument();
  });

  it("renders the status filter select", () => {
    renderWithQueryClient(<HiringPage />);
    expect(
      screen.getByRole("combobox", { name: /filter by status/i })
    ).toBeInTheDocument();
  });

  it("renders the role filter select", () => {
    renderWithQueryClient(<HiringPage />);
    expect(
      screen.getByRole("combobox", { name: /filter by role/i })
    ).toBeInTheDocument();
  });

  it("renders the sort select", () => {
    renderWithQueryClient(<HiringPage />);
    expect(
      screen.getByRole("combobox", { name: /sort by/i })
    ).toBeInTheDocument();
  });

  it("renders table column headers", () => {
    renderWithQueryClient(<HiringPage />);
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Company")).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
    // Status column now includes the date — "First Seen" header removed (#182)
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders Prev and Next pagination buttons", () => {
    renderWithQueryClient(<HiringPage />);
    expect(screen.getByRole("button", { name: /prev/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
  });

  it("disables Prev button on first page", () => {
    renderWithQueryClient(<HiringPage />);
    expect(screen.getByRole("button", { name: /prev/i })).toBeDisabled();
  });

  it("disables Next button when total fits on one page", async () => {
    // mockPostingsResponse has total: 1, which is < PAGE_SIZE (50)
    renderWithQueryClient(<HiringPage />);
    await waitFor(() =>
      expect(screen.getByText(/Showing/)).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });

  it("renders posting row after data loads", async () => {
    renderWithQueryClient(<HiringPage />);
    await waitFor(() =>
      expect(screen.getByText("Field Marketing Rep")).toBeInTheDocument()
    );
    // "T-ROC" appears in both the table row and the company filter dropdown option
    expect(screen.getAllByText("T-ROC").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Miami, FL")).toBeInTheDocument();
  });

  it("filters job feed by status", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<HiringPage />);

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

  it("shows Clear all when filters are active and resets on click", async () => {
    const user = userEvent.setup();
    overrideQuery(listCompaniesApiV1CompaniesGetOptions, "companies", [
      { id: "troc-uuid", name: "T-ROC", slug: "troc", ats_platform: "icims" },
    ]);
    renderWithQueryClient(<HiringPage />);

    await waitFor(() =>
      expect(screen.getByText("Field Marketing Rep")).toBeInTheDocument()
    );

    const statusSelect = screen.getByRole("combobox", { name: /filter by status/i });
    await user.selectOptions(statusSelect, "inactive");

    await waitFor(() =>
      expect(screen.getByText("No postings match your filters")).toBeInTheDocument()
    );
    expect(screen.getByText("Clear all")).toBeInTheDocument();

    await user.click(screen.getByText("Clear all"));

    await waitFor(() =>
      expect(screen.getByText("Field Marketing Rep")).toBeInTheDocument()
    );
    expect(screen.queryByText("Clear all")).not.toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Settings
// ────────────────────────────────────────────────────────────────────────────

describe("Settings page", () => {
  it("renders the Settings heading", () => {
    renderWithQueryClient(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: /^settings$/i })
    ).toBeInTheDocument();
  });

  it("renders the Pipeline Controls section", () => {
    renderWithQueryClient(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: /pipeline controls/i })
    ).toBeInTheDocument();
  });

  it("renders the Trigger Aggregation button", () => {
    renderWithQueryClient(<SettingsPage />);
    expect(
      screen.getByRole("button", { name: /trigger aggregation/i })
    ).toBeInTheDocument();
  });

  it("renders enabled Scrape and Enrichment trigger buttons", () => {
    renderWithQueryClient(<SettingsPage />);
    const scrapeBtn = screen.getByRole("button", { name: /trigger scrape/i });
    const enrichBtn = screen.getByRole("button", { name: /trigger enrichment/i });
    expect(scrapeBtn).not.toBeDisabled();
    expect(enrichBtn).not.toBeDisabled();
  });

  it("renders the System Info section", () => {
    renderWithQueryClient(<SettingsPage />);
    expect(
      screen.getByRole("heading", { name: /system info/i })
    ).toBeInTheDocument();
  });

  it("renders system info key-value rows", () => {
    renderWithQueryClient(<SettingsPage />);
    expect(screen.getByText("Database")).toBeInTheDocument();
    expect(screen.getByText("Supabase Postgres 17")).toBeInTheDocument();
    expect(screen.getByText("Platform")).toBeInTheDocument();
    expect(screen.getByText("Digital Ocean")).toBeInTheDocument();
  });

});

// ────────────────────────────────────────────────────────────────────────────
// Settings — scheduler section
// ────────────────────────────────────────────────────────────────────────────

describe("Settings page — scheduler section", () => {
  it("renders the Scheduler heading", async () => {
    renderWithQueryClient(<SettingsPage />);
    expect(screen.getByRole("heading", { name: /scheduler/i })).toBeInTheDocument();
  });

  it("shows Enabled badge when scheduler is enabled", async () => {
    renderWithQueryClient(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("Enabled")).toBeInTheDocument());
  });

  it("shows schedule row and action buttons for active schedule", async () => {
    overrideQuery(schedulerStatusApiV1SchedulerStatusGetOptions, "schedulerStatus", {
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
    renderWithQueryClient(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("daily_pipeline")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /^trigger$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^pause$/i })).toBeInTheDocument();
  });

  it("shows Resume button for a paused schedule", async () => {
    overrideQuery(schedulerStatusApiV1SchedulerStatusGetOptions, "schedulerStatus", {
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
    renderWithQueryClient(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("daily_pipeline")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /^resume$/i })).toBeInTheDocument();
  });

  it("shows missed run warning when missed_run is true", async () => {
    overrideQuery(schedulerStatusApiV1SchedulerStatusGetOptions, "schedulerStatus", {
      enabled: true,
      schedules: [],
      last_pipeline_finished_at: "2026-02-20T10:00:00Z",
      last_pipeline_success: false,
      missed_run: true,
    });
    renderWithQueryClient(<SettingsPage />);
    await waitFor(() =>
      expect(
        screen.getByText(/no pipeline completed in the last 80 hours/i)
      ).toBeInTheDocument()
    );
  });

  it("shows 'Could not load scheduler status' when API fails", async () => {
    overrideQueryReject(schedulerStatusApiV1SchedulerStatusGetOptions, "schedulerStatus", new Error("network"));
    renderWithQueryClient(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(/error loading scheduler/i)).toBeInTheDocument()
    , { timeout: 3000 });
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Settings — trigger error handling
// ────────────────────────────────────────────────────────────────────────────

describe("Settings page — trigger errors", () => {
  it("shows error banner when Trigger Scrape fails", async () => {
    const rejectFn = vi.fn().mockRejectedValue(new Error("Backend unreachable"));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(triggerScrapeApiV1ScrapeTriggerPostMutation).mockReturnValue({ mutationFn: rejectFn } as any);
    const user = userEvent.setup();
    renderWithQueryClient(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /trigger scrape/i }));
    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: /^confirm$/i }));

    await waitFor(() => {
      expect(rejectFn).toHaveBeenCalled();
    });

    await waitFor(() =>
      expect(screen.getByText(/scrape error/i)).toBeInTheDocument()
    , { timeout: 3000 });
  });

  it("shows error banner when Trigger Enrichment fails", async () => {
    const rejectFn = vi.fn().mockRejectedValue(new Error("Backend unreachable"));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(triggerFullApiV1EnrichTriggerPostMutation).mockReturnValue({ mutationFn: rejectFn } as any);
    const user = userEvent.setup();
    renderWithQueryClient(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /trigger enrichment/i }));
    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: /^confirm$/i }));

    await waitFor(() => {
      expect(rejectFn).toHaveBeenCalled();
    });

    await waitFor(() =>
      expect(screen.getByText(/enrichment error/i)).toBeInTheDocument()
    , { timeout: 3000 });
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Settings — run history with data
// ────────────────────────────────────────────────────────────────────────────

describe("Settings page — run history with data", () => {
  beforeEach(() => {
    overrideQuery(pipelineRunsApiV1PipelineRunsGetOptions, "pipelineRuns", {
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
    renderWithQueryClient(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("T-ROC")).toBeInTheDocument());
  });

  it("renders pass1 succeeded count in enrichment run history", async () => {
    renderWithQueryClient(<SettingsPage />);
    await waitFor(() => {
      const cells = screen.getAllByText("95");
      expect(cells.length).toBeGreaterThan(0);
    });
  });
});
