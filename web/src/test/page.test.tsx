import { screen } from "@testing-library/react";
import DashboardPage from "../app/(app)/page";
import { renderWithQueryClient } from "./test-utils";

vi.mock("@/lib/api-client", () => ({
  api: {
    getPipelineStatus: vi.fn(),
    getVelocity: vi.fn(),
  },
}));

vi.mock("@/api-client/@tanstack/react-query.gen", async () => {
  const { apiClientRqMock } = await import("./mocks/api-client-rq");
  return apiClientRqMock();
});

import "./mocks/resize-observer";

vi.mock("@tremor/react", async () => {
  const { tremorMockSimple } = await import("./mocks/tremor");
  return tremorMockSimple();
});

describe("Home page", () => {
  it("renders the Pipeline Health heading", () => {
    renderWithQueryClient(<DashboardPage />);
    expect(
      screen.getByRole("heading", { name: /pipeline health/i })
    ).toBeInTheDocument();
  });

  it("renders the page subtitle", () => {
    renderWithQueryClient(<DashboardPage />);
    expect(
      screen.getByText(/hiring activity across tracked competitors/i)
    ).toBeInTheDocument();
  });
});
