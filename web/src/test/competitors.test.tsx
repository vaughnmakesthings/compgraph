import { render, screen, waitFor } from "@testing-library/react";
import type {
  DailyVelocity,
  PayBenchmark,
  BrandTimeline,
  PostingListResponse,
} from "@/lib/types";

// ── Hoist mock data so it's available inside vi.mock factories ────────────────

const mockVelocity = vi.hoisted<DailyVelocity[]>(() => [
  {
    date: "2026-02-22",
    company_id: "uuid-advantage",
    company_name: "Advantage Solutions",
    new_postings: 5,
    closed_postings: 1,
    active_postings: 120,
  },
  {
    date: "2026-02-22",
    company_id: "uuid-acosta",
    company_name: "Acosta Group",
    new_postings: 3,
    closed_postings: 0,
    active_postings: 85,
  },
  {
    date: "2026-02-22",
    company_id: "uuid-bds",
    company_name: "BDS Connected Solutions",
    new_postings: 2,
    closed_postings: 0,
    active_postings: 42,
  },
  {
    date: "2026-02-22",
    company_id: "uuid-marketsource",
    company_name: "MarketSource",
    new_postings: 4,
    closed_postings: 2,
    active_postings: 67,
  },
  {
    date: "2026-02-22",
    company_id: "uuid-troc",
    company_name: "T-ROC",
    new_postings: 1,
    closed_postings: 0,
    active_postings: 31,
  },
]);

const mockPayBenchmarks = vi.hoisted<PayBenchmark[]>(() => [
  {
    company_id: "uuid-advantage",
    role_archetype: "Field Rep",
    pay_min_avg: 18.5,
    pay_max_avg: 24.0,
    sample_size: 40,
  },
]);

const mockBrandTimeline = vi.hoisted<BrandTimeline[]>(() => [
  {
    brand_id: "brand-1",
    brand_name: "Samsung",
    date: "2026-02-22",
    posting_count: 30,
    company_id: "uuid-advantage",
  },
]);

const mockPostingsResponse = vi.hoisted<PostingListResponse>(() => ({
  items: [
    {
      id: "posting-1",
      company_id: "uuid-advantage",
      title: "Field Marketing Representative",
      location: "Atlanta, GA",
      first_seen_at: "2026-01-15T00:00:00Z",
      last_seen_at: "2026-02-22T00:00:00Z",
      is_active: true,
      role_archetype: "Field Rep",
      pay_min: 18,
      pay_max: 24,
      employment_type: "Full-time",
    },
  ],
  total: 1,
}));

// ── Controllable slug for dossier tests ───────────────────────────────────────

const mockSlug = vi.hoisted(() => ({ current: "advantage" }));

// ── Mock next/navigation ──────────────────────────────────────────────────────

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/competitors",
  useParams: () => ({ slug: mockSlug.current }),
}));

// ── Mock recharts (jsdom has no layout engine) ────────────────────────────────

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 800, height: 400 }}>{children}</div>
    ),
    BarChart: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="bar-chart">{children}</div>
    ),
    Bar: ({ name }: { name: string }) => <div>{name}</div>,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
  };
});

// ── Mock api-client ───────────────────────────────────────────────────────────

vi.mock("@/lib/api-client", () => ({
  api: {
    getVelocity: vi.fn().mockResolvedValue(mockVelocity),
    getPayBenchmarks: vi.fn().mockResolvedValue(mockPayBenchmarks),
    getBrandTimeline: vi.fn().mockResolvedValue(mockBrandTimeline),
    listPostings: vi.fn().mockResolvedValue(mockPostingsResponse),
  },
}));

// ── Imports (after mocks) ─────────────────────────────────────────────────────

import CompetitorsPage from "@/app/competitors/page";
import CompetitorDossierPage from "@/app/competitors/[slug]/page";

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("Competitors list page", () => {
  it("renders the Competitors heading", () => {
    render(<CompetitorsPage />);
    expect(
      screen.getByRole("heading", { name: /competitors/i }),
    ).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    render(<CompetitorsPage />);
    expect(
      screen.getByText(/field marketing agencies in our competitive set/i),
    ).toBeInTheDocument();
  });

  it("renders 5 company cards", () => {
    render(<CompetitorsPage />);
    expect(screen.getByText("Advantage Solutions")).toBeInTheDocument();
    expect(screen.getByText("Acosta Group")).toBeInTheDocument();
    expect(screen.getByText("BDS Connected Solutions")).toBeInTheDocument();
    expect(screen.getByText("MarketSource")).toBeInTheDocument();
    expect(screen.getByText("T-ROC")).toBeInTheDocument();
  });

  it("renders ATS platform badges for each company", () => {
    render(<CompetitorsPage />);
    const workdayBadges = screen.getAllByText("Workday");
    const icimsBadges = screen.getAllByText("iCIMS");
    expect(workdayBadges).toHaveLength(3);
    expect(icimsBadges).toHaveLength(2);
  });

  it("shows active posting counts after velocity data loads", async () => {
    render(<CompetitorsPage />);
    await waitFor(() => {
      expect(screen.getByText("120")).toBeInTheDocument();
    });
  });
});

describe("Competitor dossier page", () => {
  beforeEach(() => {
    mockSlug.current = "advantage";
  });

  it("renders the company name for the 'advantage' slug", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Advantage Solutions")).toBeInTheDocument();
  });

  it("renders the ATS badge", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Workday")).toBeInTheDocument();
  });

  it("renders KPI cards after data loads", async () => {
    render(<CompetitorDossierPage />);
    await waitFor(() => {
      expect(screen.getByText("Active Postings")).toBeInTheDocument();
      expect(screen.getByText("New This Week")).toBeInTheDocument();
      expect(screen.getByText("Avg Pay Min")).toBeInTheDocument();
      expect(screen.getByText("Top Role")).toBeInTheDocument();
    });
  });

  it("renders 'Company not found' for an unknown slug", () => {
    mockSlug.current = "unknown-slug";
    render(<CompetitorDossierPage />);
    expect(screen.getByText(/company not found/i)).toBeInTheDocument();
  });

  it("renders the Pay Benchmarks section title", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Pay Benchmarks by Role")).toBeInTheDocument();
  });

  it("renders the Job Postings section title", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Job Postings")).toBeInTheDocument();
  });

  it("renders posting data in the table after load", async () => {
    render(<CompetitorDossierPage />);
    await waitFor(() => {
      expect(
        screen.getByText("Field Marketing Representative"),
      ).toBeInTheDocument();
    });
  });

  it("renders error message when API fails", async () => {
    const { api } = await import("@/lib/api-client");
    vi.mocked(api.getVelocity).mockRejectedValueOnce(new Error("Network error"));
    render(<CompetitorDossierPage />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });
});
