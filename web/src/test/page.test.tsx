import { render, screen } from "@testing-library/react";
import DashboardPage from "../app/(app)/page";
import { api } from "@/lib/api-client";

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
    BarChart: () => <div data-testid="bar-chart" />,
    AreaChart: () => <div data-testid="area-chart" />,
    DonutChart: () => <div data-testid="donut-chart" />,
  };
});

const mockedApi = vi.mocked(api);

beforeEach(() => {
  mockedApi.getPipelineStatus.mockReturnValue(new Promise(() => {}));
  mockedApi.getVelocity.mockReturnValue(new Promise(() => {}));
});

describe("Home page", () => {
  it("renders the Pipeline Health heading", () => {
    render(<DashboardPage />);
    expect(
      screen.getByRole("heading", { name: /pipeline health/i })
    ).toBeInTheDocument();
  });

  it("renders the page subtitle", () => {
    render(<DashboardPage />);
    expect(
      screen.getByText(/hiring activity across tracked competitors/i)
    ).toBeInTheDocument();
  });
});
