import { render, screen } from "@testing-library/react";
import Home from "../app/page";

describe("Home page", () => {
  it("renders the CompGraph heading", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: /compgraph/i })).toBeInTheDocument();
  });

  it("renders the platform description", () => {
    render(<Home />);
    expect(screen.getByText(/competitive intelligence platform/i)).toBeInTheDocument();
  });
});
