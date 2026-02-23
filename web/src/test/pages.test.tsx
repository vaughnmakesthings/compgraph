import { render, screen } from "@testing-library/react";
import MarketPage from "../app/market/page";
import HiringPage from "../app/hiring/page";
import SettingsPage from "../app/settings/page";
import type { DailyVelocity, CoverageGap, PostingListResponse } from "../lib/types";

vi.mock("../lib/api-client", () => ({
  api: {
    getVelocity: vi.fn(),
    getCoverageGaps: vi.fn(),
    listPostings: vi.fn(),
    health: vi.fn(),
    triggerAggregation: vi.fn(),
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
      company_id: "troc",
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
  vi.mocked(api.health).mockResolvedValue({ status: "ok" });
  vi.mocked(api.triggerAggregation).mockResolvedValue({ status: "started" });
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
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("First Seen")).toBeInTheDocument();
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

  it("renders disabled Scrape and Enrichment trigger buttons with coming soon tooltip", () => {
    render(<SettingsPage />);
    const scrapeBtn = screen.getByRole("button", { name: /trigger scrape/i });
    const enrichBtn = screen.getByRole("button", { name: /trigger enrichment/i });
    expect(scrapeBtn).toBeDisabled();
    expect(enrichBtn).toBeDisabled();
    expect(scrapeBtn).toHaveAttribute("title", "Coming soon");
    expect(enrichBtn).toHaveAttribute("title", "Coming soon");
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
});
