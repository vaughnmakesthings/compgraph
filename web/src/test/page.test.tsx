import { render, screen } from "@testing-library/react";
import DashboardPage from "../app/page";
import { api } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  api: {
    getPipelineStatus: vi.fn(),
    getVelocity: vi.fn(),
  },
}));

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
    Bar: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
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
