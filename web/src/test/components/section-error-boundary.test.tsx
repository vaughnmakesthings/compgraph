import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SectionErrorBoundary } from "@/components/ui/section-error-boundary";

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Render failure");
  }
  return <p>Content loaded</p>;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("SectionErrorBoundary", () => {
  it("renders children when no error occurs", () => {
    render(
      <SectionErrorBoundary>
        <p>Working content</p>
      </SectionErrorBoundary>
    );

    expect(screen.getByText("Working content")).toBeInTheDocument();
  });

  it("shows default fallback when child throws", () => {
    render(
      <SectionErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </SectionErrorBoundary>
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("This section encountered an error")).toBeInTheDocument();
    expect(screen.getByText("Render failure")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("shows named fallback when name prop is provided", () => {
    render(
      <SectionErrorBoundary name="Velocity Chart">
        <ThrowingChild shouldThrow={true} />
      </SectionErrorBoundary>
    );

    expect(screen.getByText("Failed to load Velocity Chart")).toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    render(
      <SectionErrorBoundary fallback={<div>Custom error state</div>}>
        <ThrowingChild shouldThrow={true} />
      </SectionErrorBoundary>
    );

    expect(screen.getByText("Custom error state")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("recovers from error when retry is clicked", async () => {
    const user = userEvent.setup();
    let shouldThrow = true;

    function ToggleChild() {
      if (shouldThrow) {
        throw new Error("Temporary failure");
      }
      return <p>Recovered content</p>;
    }

    const { rerender } = render(
      <SectionErrorBoundary>
        <ToggleChild />
      </SectionErrorBoundary>
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();

    shouldThrow = false;
    await user.click(screen.getByRole("button", { name: /retry/i }));

    rerender(
      <SectionErrorBoundary>
        <ToggleChild />
      </SectionErrorBoundary>
    );

    expect(screen.getByText("Recovered content")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("logs error to console", () => {
    render(
      <SectionErrorBoundary name="KPI metrics">
        <ThrowingChild shouldThrow={true} />
      </SectionErrorBoundary>
    );

    expect(console.error).toHaveBeenCalled();
  });

  it("does not affect sibling boundaries", () => {
    render(
      <div>
        <SectionErrorBoundary name="Section A">
          <ThrowingChild shouldThrow={true} />
        </SectionErrorBoundary>
        <SectionErrorBoundary name="Section B">
          <ThrowingChild shouldThrow={false} />
        </SectionErrorBoundary>
      </div>
    );

    expect(screen.getByText("Failed to load Section A")).toBeInTheDocument();
    expect(screen.getByText("Content loaded")).toBeInTheDocument();
  });
});
