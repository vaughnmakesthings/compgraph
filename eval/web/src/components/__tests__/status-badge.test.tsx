import { describe, it, expect } from "vitest";
import { axe } from "vitest-axe";
import { render, screen } from "@/__tests__/helpers/render";
import { StatusBadge } from "@/components/status-badge";

describe("StatusBadge", () => {
  it("renders label text for completed status", () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders label text for running status", () => {
    render(<StatusBadge status="running" />);
    expect(screen.getByText("Running")).toBeInTheDocument();
  });

  it("renders label text for failed status", () => {
    render(<StatusBadge status="failed" />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("renders human-readable label for cant-assess", () => {
    render(<StatusBadge status="cant-assess" />);
    expect(screen.getByText("Can't Assess")).toBeInTheDocument();
  });

  it("renders human-readable label for blank", () => {
    render(<StatusBadge status="blank" />);
    expect(screen.getByText("Wrong (blank)")).toBeInTheDocument();
  });

  it("renders human-readable label for replaced", () => {
    render(<StatusBadge status="replaced" />);
    expect(screen.getByText("Wrong (replaced)")).toBeInTheDocument();
  });

  it("applies sm size class when size=sm", () => {
    render(<StatusBadge status="correct" size="sm" />);
    const label = screen.getByText("Correct");
    expect(label.className).toContain("text-[11px]");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<StatusBadge status="completed" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
