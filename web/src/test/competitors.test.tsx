import { screen, waitFor, fireEvent } from "@testing-library/react";
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

// ── Mock Tremor charts (jsdom has no layout engine) ────────────────────────────

import "./mocks/resize-observer";

vi.mock("@tremor/react", async () => {
  const { tremorMockSimple } = await import("./mocks/tremor");
  return tremorMockSimple();
});

// ── Mock api-client react-query options ──────────────────────────────────────

vi.mock("@/api-client/@tanstack/react-query.gen", async () => {
  const { apiClientRqMock } = await import("./mocks/api-client-rq");
  return apiClientRqMock();
});

// ── Imports (after mocks) ─────────────────────────────────────────────────────

import CompetitorsPage from "@/app/(app)/competitors/page";
import CompetitorDossierPage from "@/app/(app)/competitors/[slug]/page";
import { renderWithQueryClient } from "./test-utils";
import { getVelocityApiV1AggregationVelocityGetOptions } from "@/api-client/@tanstack/react-query.gen";

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getVelocityApiV1AggregationVelocityGetOptions).mockReturnValue({
    queryKey: ["velocity"],
    queryFn: vi.fn().mockResolvedValue(mockVelocity),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  } as any);
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("Competitors list page", () => {
  it("renders the Competitors heading", () => {
    renderWithQueryClient(<CompetitorsPage />);
    expect(
      screen.getByRole("heading", { name: /competitors/i }),
    ).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    renderWithQueryClient(<CompetitorsPage />);
    expect(
      screen.getByText(/field marketing agencies in our competitive set/i),
    ).toBeInTheDocument();
  });

  it("renders 5 company cards", () => {
    renderWithQueryClient(<CompetitorsPage />);
    expect(screen.getByText("2020 Companies")).toBeInTheDocument();
    expect(screen.getByText("BDS Connected Solutions")).toBeInTheDocument();
    expect(screen.getByText("MarketSource")).toBeInTheDocument();
    expect(screen.getByText("OSL Retail Services")).toBeInTheDocument();
    expect(screen.getByText("T-ROC")).toBeInTheDocument();
  });

  it("renders ATS platform badges for each company", () => {
    renderWithQueryClient(<CompetitorsPage />);
    const workdayBadges = screen.getAllByText("Workday");
    const icimsBadges = screen.getAllByText("iCIMS");
    // 2020 Companies + T-ROC = 2 Workday; BDS + MarketSource + OSL = 3 iCIMS
    expect(workdayBadges).toHaveLength(2);
    expect(icimsBadges).toHaveLength(3);
  });

  it("shows active posting counts after velocity data loads", async () => {
    renderWithQueryClient(<CompetitorsPage />);
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
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getAllByText("T-ROC").length).toBeGreaterThanOrEqual(1);
  });

  it("renders the ATS badge", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Workday")).toBeInTheDocument();
  });

  it("renders KPI cards", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Active Postings")).toBeInTheDocument();
    expect(screen.getByText("New This Week")).toBeInTheDocument();
    expect(screen.getByText("Avg Pay Min")).toBeInTheDocument();
    expect(screen.getByText("Top Role")).toBeInTheDocument();
  });

  it("renders KPI values from mock data", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
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
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText(/company not found/i)).toBeInTheDocument();
  });

  it("renders tab navigation", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Executive Summary")).toBeInTheDocument();
    expect(screen.getByText("Brand Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Hiring")).toBeInTheDocument();
    expect(screen.getByText("Employee Insights")).toBeInTheDocument();
  });

  it("renders the Key Finding callout on the summary tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Key Finding")).toBeInTheDocument();
    expect(screen.getByText(/doubling down on Samsung/i)).toBeInTheDocument();
  });

  it("renders the Company Overview narrative section on the summary tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Company Overview")).toBeInTheDocument();
    expect(screen.getByText(/premier retail services company/i)).toBeInTheDocument();
  });

  it("renders known clients and channels on the summary tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Known Clients & Channels")).toBeInTheDocument();
    expect(screen.getByText("Samsung")).toBeInTheDocument();
  });

  it("renders the posting metrics row on the summary tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Total Roles Found")).toBeInTheDocument();
    expect(screen.getByText("Roles Closed")).toBeInTheDocument();
    expect(screen.getByText("Currently Open")).toBeInTheDocument();
  });

  it("renders the Hiring by Role section on the summary tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Hiring by Role")).toBeInTheDocument();
    expect(screen.getAllByText("Brand Ambassador").length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Latest Roles table on the summary tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getByText("Latest Roles")).toBeInTheDocument();
    expect(
      screen.getAllByText("Field Marketing Representative – Samsung").length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Orlando, FL")).toBeInTheDocument();
  });

  it("renders the Pay Benchmarks section title on the hiring tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Hiring"));
    expect(screen.getByText("Pay Benchmarks by Role")).toBeInTheDocument();
  });

  it("renders the Job Postings table on the hiring tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Hiring"));
    expect(screen.getByText("Job Postings")).toBeInTheDocument();
  });

  it("renders the Geographic Focus callout on the brands tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Brand Intelligence"));
    expect(screen.getByText("Geographic Focus")).toBeInTheDocument();
    expect(screen.getByText(/Southeast corridor dominance/i)).toBeInTheDocument();
  });

  it("renders the Brand Intelligence section on the brands tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Brand Intelligence"));
    // "Brand Intelligence" appears as both tab label and section heading
    expect(screen.getAllByText("Brand Intelligence").length).toBeGreaterThanOrEqual(2);
  });

  it("renders the Data Note caution callout on the brands tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Brand Intelligence"));
    expect(screen.getByText("Data Note")).toBeInTheDocument();
    expect(screen.getByText(/re-fills of the same position/i)).toBeInTheDocument();
  });

  it("renders distinct content for the 'bds' slug", () => {
    mockSlug.current = "bds";
    renderWithQueryClient(<CompetitorDossierPage />);
    expect(screen.getAllByText("BDS Connected Solutions").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/in-store demo presence/i)).toBeInTheDocument();
  });

  it("renders Glassdoor overall rating on the employees tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Employee Insights"));
    // T-ROC overall rating is 3.9
    expect(screen.getAllByText("3.9").length).toBeGreaterThanOrEqual(1);
  });

  it("renders sentiment percentages on the employees tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Employee Insights"));
    // T-ROC: 72% recommend, 68% outlook, 79% CEO, 50% interview
    expect(screen.getByText("72%")).toBeInTheDocument();
    expect(screen.getByText(/Brett Beveridge/i)).toBeInTheDocument();
  });

  it("renders review cards on the employees tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Employee Insights"));
    expect(screen.getByText("Low Pay, High Standards")).toBeInTheDocument();
    expect(screen.getByText("Great place to work and grow")).toBeInTheDocument();
  });

  it("renders category ratings on the employees tab", () => {
    renderWithQueryClient(<CompetitorDossierPage />);
    fireEvent.click(screen.getByText("Employee Insights"));
    expect(screen.getByText("Ratings by Category")).toBeInTheDocument();
    expect(screen.getByText("Diversity & inclusion")).toBeInTheDocument();
  });
});
