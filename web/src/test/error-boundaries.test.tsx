import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@sentry/nextjs", () => ({
  captureException: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

const mockError = Object.assign(new Error("Test error message"), { digest: "abc123" });
const mockReset = vi.fn();

describe("(app) error.tsx", () => {
  it("renders error message and retry button", async () => {
    const { default: AppError } = await import("@/app/(app)/error");
    render(<AppError error={mockError} reset={mockReset} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Test error message")).toBeInTheDocument();
    expect(screen.getByText("Error ID: abc123")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("calls reset when retry is clicked", async () => {
    const { default: AppError } = await import("@/app/(app)/error");
    render(<AppError error={mockError} reset={mockReset} />);

    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(mockReset).toHaveBeenCalledOnce();
  });

  it("reports to Sentry on mount", async () => {
    const Sentry = await import("@sentry/nextjs");
    const { default: AppError } = await import("@/app/(app)/error");
    render(<AppError error={mockError} reset={mockReset} />);

    expect(Sentry.captureException).toHaveBeenCalledWith(mockError);
  });
});

describe("(app) not-found.tsx", () => {
  it("renders 404 with link back to dashboard", async () => {
    const { default: AppNotFound } = await import("@/app/(app)/not-found");
    render(<AppNotFound />);

    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByText("Page not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to dashboard/i })).toHaveAttribute("href", "/");
  });
});

describe("(app) loading.tsx", () => {
  it("renders loading status with aria attributes", async () => {
    const { default: AppLoading } = await import("@/app/(app)/loading");
    render(<AppLoading />);

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveAttribute("aria-label", "Loading page content");
  });
});

describe("(app)/eval error.tsx", () => {
  it("renders evaluation-specific error heading", async () => {
    const { default: EvalError } = await import("@/app/(app)/eval/error");
    render(<EvalError error={mockError} reset={mockReset} />);

    expect(screen.getByText("Evaluation error")).toBeInTheDocument();
    expect(screen.getByText("Test error message")).toBeInTheDocument();
  });
});

describe("(app)/eval loading.tsx", () => {
  it("renders loading status for evaluation data", async () => {
    const { default: EvalLoading } = await import("@/app/(app)/eval/loading");
    render(<EvalLoading />);

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "Loading evaluation data");
  });
});

describe("(auth) error.tsx", () => {
  it("renders authentication error with retry", async () => {
    const { default: AuthError } = await import("@/app/(auth)/error");
    render(<AuthError error={mockError} reset={mockReset} />);

    expect(screen.getByText("Authentication error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });
});

describe("(auth) not-found.tsx", () => {
  it("renders 404 with link to login", async () => {
    const { default: AuthNotFound } = await import("@/app/(auth)/not-found");
    render(<AuthNotFound />);

    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /go to login/i })).toHaveAttribute("href", "/login");
  });
});

describe("(auth) loading.tsx", () => {
  it("renders loading status for authentication", async () => {
    const { default: AuthLoading } = await import("@/app/(auth)/loading");
    render(<AuthLoading />);

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-label", "Loading authentication");
  });
});

describe("root not-found.tsx", () => {
  it("renders 404 with link to dashboard", async () => {
    const { default: RootNotFound } = await import("@/app/not-found");
    render(<RootNotFound />);

    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByText("Page not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to dashboard/i })).toHaveAttribute("href", "/");
  });
});
