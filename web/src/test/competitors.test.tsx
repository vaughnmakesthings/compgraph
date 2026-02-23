import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import type { DailyVelocity } from "@/lib/types";

// ── Hoist mock data so it's available inside vi.mock factories ────────────────

const mockVelocity = vi.hoisted<DailyVelocity[]>(() => [
  {
    date: "2026-02-22",
    company_id: "uuid-2020",
    company_name: "2020 Companies",
    company_slug: "2020",
    new_postings: 5,
    closed_postings: 1,
    active_postings: 120,
  },
  {
    date: "2026-02-22",
    company_id: "uuid-bds",
    company_name: "BDS Connected Solutions",
    company_slug: "bds",
    new_postings: 2,
    closed_postings: 0,
    active_postings: 42,
  },
  {
    date: "2026-02-22",
    company_id: "uuid-marketsource",
    company_name: "MarketSource",
    company_slug: "marketsource",
    new_postings: 4,
    closed_postings: 2,
    active_postings: 67,
  },
  {
    date: "2026-02-22",
    company_id: "uuid-osl",
    company_name: "OSL Retail Services",
    company_slug: "osl",
    new_postings: 2,
    closed_postings: 1,
    active_postings: 55,
  },
  {
    date: "2026-02-22",
    company_id: "uuid-troc",
    company_name: "T-ROC",
    company_slug: "troc",
    new_postings: 1,
    closed_postings: 0,
    active_postings: 31,
  },
]);

// ── Controllable slug for dossier tests ───────────────────────────────────────

const mockSlug = vi.hoisted(() => ({ current: "troc" }));

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

// ── Mock api-client (used by CompetitorsPage list) ────────────────────────────

vi.mock("@/lib/api-client", () => ({
  api: {
    getVelocity: vi.fn().mockResolvedValue(mockVelocity),
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
    expect(screen.getByText("2020 Companies")).toBeInTheDocument();
    expect(screen.getByText("BDS Connected Solutions")).toBeInTheDocument();
    expect(screen.getByText("MarketSource")).toBeInTheDocument();
    expect(screen.getByText("OSL Retail Services")).toBeInTheDocument();
    expect(screen.getByText("T-ROC")).toBeInTheDocument();
  });

  it("renders ATS platform badges for each company", () => {
    render(<CompetitorsPage />);
    const workdayBadges = screen.getAllByText("Workday");
    const icimsBadges = screen.getAllByText("iCIMS");
    // 2020 Companies + T-ROC = 2 Workday; BDS + MarketSource + OSL = 3 iCIMS
    expect(workdayBadges).toHaveLength(2);
    expect(icimsBadges).toHaveLength(3);
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
    mockSlug.current = "troc";
  });

  it("renders the company name for the 'troc' slug", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("T-ROC")).toBeInTheDocument();
  });

  it("renders the ATS badge", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Workday")).toBeInTheDocument();
  });

  it("renders KPI cards", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Active Postings")).toBeInTheDocument();
    expect(screen.getByText("New This Week")).toBeInTheDocument();
    expect(screen.getByText("Avg Pay Min")).toBeInTheDocument();
    expect(screen.getByText("Top Role")).toBeInTheDocument();
  });

  it("renders KPI values from mock data", () => {
    render(<CompetitorDossierPage />);
    // $48,000 is unique to the avg pay KPI
    expect(screen.getByText("$48,000")).toBeInTheDocument();
    // 89 appears in both top KPI (Active Postings) and metrics row (Currently Open)
    expect(screen.getAllByText("89").length).toBeGreaterThanOrEqual(1);
    // 12 and FMR each appear in both KPI row and role distribution list
    expect(screen.getAllByText("12").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("FMR").length).toBeGreaterThanOrEqual(1);
  });

  it("renders 'Company not found' for an unknown slug", () => {
    mockSlug.current = "unknown-slug";
    render(<CompetitorDossierPage />);
    expect(screen.getByText(/company not found/i)).toBeInTheDocument();
  });

  it("renders tab navigation", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Executive Summary")).toBeInTheDocument();
    expect(screen.getByText("Brand Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Hiring")).toBeInTheDocument();
  });

  it("renders the Key Finding callout on the summary tab", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Key Finding")).toBeInTheDocument();
    expect(screen.getByText(/doubling down on Samsung/i)).toBeInTheDocument();
  });

  it("renders the Company Overview narrative section on the summary tab", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Company Overview")).toBeInTheDocument();
    expect(screen.getByText(/premier retail services company/i)).toBeInTheDocument();
  });

  it("renders known clients and channels on the summary tab", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Known Clients & Channels")).toBeInTheDocument();
    expect(screen.getByText("Samsung")).toBeInTheDocument();
  });

  it("renders the posting metrics row on the summary tab", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Total Roles Found")).toBeInTheDocument();
    expect(screen.getByText("Roles Closed")).toBeInTheDocument();
    expect(screen.getByText("Currently Open")).toBeInTheDocument();
  });

  it("renders the Hiring by Role section on the summary tab", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Hiring by Role")).toBeInTheDocument();
    expect(screen.getAllByText("Brand Ambassador").length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Latest Roles table on the summary tab", () => {
    render(<CompetitorDossierPage />);
    expect(screen.getByText("Latest Roles")).toBeInTheDocument();
    expect(
      screen.getAllByText("Field Marketing Representative – Samsung").length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Orlando, FL")).toBeInTheDocument();
  });

  it("renders the Pay Benchmarks section title on the hiring tab", () => {
    render(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Hiring"));
    expect(screen.getByText("Pay Benchmarks by Role")).toBeInTheDocument();
  });

  it("renders the Job Postings table on the hiring tab", () => {
    render(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Hiring"));
    expect(screen.getByText("Job Postings")).toBeInTheDocument();
  });

  it("renders the Geographic Focus callout on the brands tab", () => {
    render(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Brand Intelligence"));
    expect(screen.getByText("Geographic Focus")).toBeInTheDocument();
    expect(screen.getByText(/Southeast corridor dominance/i)).toBeInTheDocument();
  });

  it("renders the Brand Intelligence section on the brands tab", () => {
    render(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Brand Intelligence"));
    // "Brand Intelligence" appears as both tab label and section heading
    expect(screen.getAllByText("Brand Intelligence").length).toBeGreaterThanOrEqual(2);
  });

  it("renders the Data Note caution callout on the brands tab", () => {
    render(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Brand Intelligence"));
    expect(screen.getByText("Data Note")).toBeInTheDocument();
    expect(screen.getByText(/re-fills of the same position/i)).toBeInTheDocument();
  });

  it("renders distinct content for the 'bds' slug", () => {
    mockSlug.current = "bds";
    render(<CompetitorDossierPage />);
    expect(screen.getByText("BDS Connected Solutions")).toBeInTheDocument();
    expect(screen.getByText(/in-store demo presence/i)).toBeInTheDocument();
  });
});
