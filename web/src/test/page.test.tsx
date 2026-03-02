import { render, screen } from "@testing-library/react";
import DashboardPage from "../app/(app)/page";
import { api } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  api: {
    getPipelineStatus: vi.fn(),
    getVelocity: vi.fn(),
  },
}));

import "./mocks/resize-observer";

vi.mock("@tremor/react", async () => {
  const { tremorMockSimple } = await import("./mocks/tremor");
  return tremorMockSimple();
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
