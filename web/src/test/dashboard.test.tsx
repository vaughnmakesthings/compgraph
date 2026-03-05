import { screen, waitFor } from "@testing-library/react";
import DashboardPage from "../app/(app)/page";
import type { DailyVelocity } from "@/lib/types";
import { renderWithQueryClient } from "./test-utils";

vi.mock("@/api-client/@tanstack/react-query.gen", async () => {
  const { apiClientRqMock } = await import("./mocks/api-client-rq");
  return apiClientRqMock();
});

import "./mocks/resize-observer";

vi.mock("@tremor/react", async () => {
  const { tremorMockWithData } = await import("./mocks/tremor");
  return tremorMockWithData();
});

const mockStatus = {
  status: "idle",
  scrape: {
    status: "idle",
    current_run: null,
    last_completed_at: "2026-02-23T10:00:00Z",
  },
  enrich: {
    status: "idle",
    current_run: {
      run_id: "run-1",
      status: "completed",
      started_at: "2026-02-23T09:00:00Z",
      pass1_total: 200,
      pass1_succeeded: 200,
      pass1_skipped: 0,
      pass2_total: 200,
      pass2_succeeded: 180,
      pass2_skipped: 20,
    },
    last_completed_at: "2026-02-23T09:45:00Z",
  },
  scheduler: { enabled: true, next_run_at: "2026-02-23T12:00:00Z" },
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

import {
  pipelineStatusApiV1PipelineStatusGetOptions,
  getVelocityApiV1AggregationVelocityGetOptions,
} from "@/api-client/@tanstack/react-query.gen";

/* eslint-disable @typescript-eslint/no-explicit-any */
function overrideVelocity(data: DailyVelocity[] | Promise<never>) {
  const queryFn = data instanceof Promise ? vi.fn().mockReturnValue(data) : vi.fn().mockResolvedValue(data);
  vi.mocked(getVelocityApiV1AggregationVelocityGetOptions).mockReturnValue({
    queryKey: ["velocity"],
    queryFn,
  } as any);
}

function overrideStatus(data: Record<string, unknown> | Promise<never>) {
  const queryFn = data instanceof Promise ? vi.fn().mockReturnValue(data) : vi.fn().mockResolvedValue(data);
  vi.mocked(pipelineStatusApiV1PipelineStatusGetOptions).mockReturnValue({
    queryKey: ["pipelineStatus"],
    queryFn,
  } as any);
}

function overrideStatusReject(err: Error) {
  vi.mocked(pipelineStatusApiV1PipelineStatusGetOptions).mockReturnValue({
    queryKey: ["pipelineStatus"],
    queryFn: vi.fn().mockRejectedValue(err),
  } as any);
}

function overrideVelocityReject(err: Error) {
  vi.mocked(getVelocityApiV1AggregationVelocityGetOptions).mockReturnValue({
    queryKey: ["velocity"],
    queryFn: vi.fn().mockRejectedValue(err),
  } as any);
}
/* eslint-enable @typescript-eslint/no-explicit-any */

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DashboardPage", () => {
  it('renders "Pipeline Health" heading', () => {
    overrideStatus(mockStatus);
    overrideVelocity(mockVelocity);

    renderWithQueryClient(<DashboardPage />);

    expect(
      screen.getByRole("heading", { name: /pipeline health/i })
    ).toBeInTheDocument();
  });

  it("shows subtitle text", () => {
    overrideStatus(mockStatus);
    overrideVelocity(mockVelocity);

    renderWithQueryClient(<DashboardPage />);

    expect(
      screen.getByText(/hiring activity across tracked competitors/i)
    ).toBeInTheDocument();
  });

  it("shows skeleton loading state initially before data resolves", () => {
    overrideStatus(new Promise(() => {}) as Promise<never>);
    overrideVelocity(new Promise(() => {}) as Promise<never>);

    renderWithQueryClient(<DashboardPage />);

    const skeletons = document.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThan(0);

    expect(screen.queryByText("Active Postings")).not.toBeInTheDocument();
  });

  it("renders KPI cards when data loads", async () => {
    overrideStatus(mockStatus);
    overrideVelocity(mockVelocity);

    renderWithQueryClient(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Active Postings")).toBeInTheDocument();
    });

    expect(screen.getByText("New This Week")).toBeInTheDocument();
    expect(screen.getByText("Enriched")).toBeInTheDocument();
    expect(screen.getByText("Pipeline Status")).toBeInTheDocument();
  });

  it("displays active postings total derived from velocity data", async () => {
    overrideStatus(mockStatus);
    overrideVelocity(mockVelocity);

    renderWithQueryClient(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Active Postings")).toBeInTheDocument();
    });

    expect(screen.getByText("211")).toBeInTheDocument();
  });

  it("displays enrichment coverage percentage", async () => {
    overrideStatus(mockStatus);
    overrideVelocity(mockVelocity);

    renderWithQueryClient(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("90%")).toBeInTheDocument();
    });
  });

  it("renders the pipeline status badge with idle label", async () => {
    overrideStatus(mockStatus);
    overrideVelocity(mockVelocity);

    renderWithQueryClient(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("idle")).toBeInTheDocument();
    });
  });

  it("renders the bar chart section after data loads", async () => {
    overrideStatus(mockStatus);
    overrideVelocity(mockVelocity);

    renderWithQueryClient(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });

    expect(
      screen.getByRole("heading", { name: /daily posting velocity/i })
    ).toBeInTheDocument();
  });

  it("KPI grid has aria-busy during loading and aria-label", () => {
    overrideStatus(new Promise(() => {}) as Promise<never>);
    overrideVelocity(new Promise(() => {}) as Promise<never>);

    renderWithQueryClient(<DashboardPage />);

    const kpiGrid = screen.getByLabelText("KPI metrics");
    expect(kpiGrid).toHaveAttribute("aria-busy", "true");
    expect(kpiGrid).toHaveAttribute("aria-label", "KPI metrics");
  });

  it("shows an error alert when the API call fails", async () => {
    overrideStatusReject(new Error("Network error: /api/pipeline/status"));
    overrideVelocityReject(new Error("Network error: /api/aggregation/velocity"));

    renderWithQueryClient(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });
});
