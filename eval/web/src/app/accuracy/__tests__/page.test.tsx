import { describe, it, expect, vi } from "vitest";
import { axe } from "vitest-axe";
import { render, screen, waitFor } from "@/__tests__/helpers/render";
import userEvent from "@testing-library/user-event";

// --- Hoisted mocks (referenced inside vi.mock factory) ---
const { mockCreateFieldReview, mockDeleteFieldReview } = vi.hoisted(() => ({
  mockCreateFieldReview: vi.fn().mockResolvedValue({ id: 1 }),
  mockDeleteFieldReview: vi.fn().mockResolvedValue(undefined),
}));

// --- Mock next/navigation (required by Sidebar) ---
vi.mock("next/navigation", () => ({
  usePathname: () => "/accuracy",
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

// --- Mock next/link (required by Sidebar) ---
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// --- Mock next-themes (required by Header > ThemeToggle) ---
vi.mock("next-themes", () => ({
  useTheme: () => ({
    setTheme: vi.fn(),
    resolvedTheme: "light",
    theme: "light",
  }),
}));

// --- Mock api-client ---
vi.mock("@/lib/api-client", () => ({
  getRuns: vi.fn().mockResolvedValue([
    {
      id: 1,
      created_at: "2026-02-18T00:00:00",
      pass_number: 1,
      model: "haiku-3.5",
      prompt_version: "pass1_v1",
      corpus_size: 50,
      total_input_tokens: 1000,
      total_output_tokens: 500,
      total_cost_usd: 0.191,
      total_duration_ms: 236000,
    },
  ]),
  getRunResults: vi.fn().mockResolvedValue([
    {
      id: 101,
      run_id: 1,
      posting_id: "posting-1",
      raw_response: null,
      parsed_result: JSON.stringify({ role_archetype: "manager" }),
      parse_success: true,
      input_tokens: 100,
      output_tokens: 50,
      cost_usd: 0.001,
      latency_ms: 500,
    },
  ]),
  getCorpus: vi.fn().mockResolvedValue([
    {
      id: "posting-1",
      company_slug: "acme",
      title: "Senior Manager",
      location: "Remote",
      full_text: "We are hiring a Senior Manager...",
      reference_pass1: JSON.stringify({ role_archetype: "manager" }),
      reference_pass2: null,
    },
  ]),
  getRunFieldReviews: vi.fn().mockResolvedValue({}),
  createFieldReview: mockCreateFieldReview,
  deleteFieldReview: mockDeleteFieldReview,
}));

import AccuracyPage from "@/app/accuracy/page";

// Helper: select a run so the main UI loads, then blur the select so
// keyboard shortcuts are not intercepted by the select element.
async function selectRun() {
  const select = await screen.findByLabelText("Select Run") as HTMLSelectElement;
  await userEvent.selectOptions(select, "1");
  // Wait for field rows to appear
  await waitFor(() => {
    expect(screen.getByText("role_archetype")).toBeInTheDocument();
  });
  // Blur the select so keyboard events are not swallowed by it
  select.blur();
}

describe("AccuracyPage", () => {
  it('renders page heading "Accuracy Review"', () => {
    render(<AccuracyPage />);
    expect(
      screen.getByRole("heading", { name: "Accuracy Review" }),
    ).toBeInTheDocument();
  });

  it("shows run selector after loading", async () => {
    render(<AccuracyPage />);
    const select = await screen.findByLabelText("Select Run");
    expect(select).toBeInTheDocument();
    expect(select.tagName).toBe("SELECT");
  });

  it("shows empty state when no run selected", async () => {
    render(<AccuracyPage />);
    const emptyMsg = await screen.findByText(/select a run to begin reviewing/i);
    expect(emptyMsg).toBeInTheDocument();
  });

  it("passes axe accessibility audit", async () => {
    const { container } = render(<AccuracyPage />);
    await waitFor(() => {
      expect(screen.getByLabelText("Select Run")).toBeInTheDocument();
    });
    const results = await axe(container, {
      rules: { "heading-order": { enabled: false } },
    });
    expect(results).toHaveNoViolations();
  });

  describe("keyboard interactions", () => {
    it("pressing C on focused field calls createFieldReview with is_correct=1", async () => {
      render(<AccuracyPage />);
      await selectRun();

      mockCreateFieldReview.mockClear();
      await userEvent.keyboard("c");

      await waitFor(() => {
        expect(mockCreateFieldReview).toHaveBeenCalledWith(
          expect.objectContaining({
            result_id: 101,
            field_name: "role_archetype",
            is_correct: 1,
            correct_value: null,
          }),
        );
      });
    });

    it("pressing B calls createFieldReview with is_correct=0, correct_value=null", async () => {
      render(<AccuracyPage />);
      await selectRun();

      mockCreateFieldReview.mockClear();
      await userEvent.keyboard("b");

      await waitFor(() => {
        expect(mockCreateFieldReview).toHaveBeenCalledWith(
          expect.objectContaining({
            result_id: 101,
            field_name: "role_archetype",
            is_correct: 0,
            correct_value: null,
          }),
        );
      });
    });

    it("pressing ArrowDown moves field focus to next field", async () => {
      render(<AccuracyPage />);
      await selectRun();

      await userEvent.keyboard("{ArrowDown}");

      await waitFor(() => {
        const roleLevel = screen.getByText("role_level");
        expect(roleLevel.closest("[class*='border-l-primary']")).toBeTruthy();
      });
    });

    it("pressing R opens replace mode with an input field", async () => {
      render(<AccuracyPage />);
      await selectRun();

      await userEvent.keyboard("r");

      await waitFor(() => {
        const inputs = document.querySelectorAll('input[type="text"]');
        expect(inputs.length).toBeGreaterThan(0);
      });
    });

    it("pressing R then typing then Enter saves with correct_value", async () => {
      render(<AccuracyPage />);
      await selectRun();

      mockCreateFieldReview.mockClear();

      // Press R to enter replace mode
      await userEvent.keyboard("r");

      // Wait for the replace input to appear
      const replaceInput = await waitFor(() => {
        const el = document.querySelector(
          'input[type="text"]',
        ) as HTMLInputElement;
        expect(el).toBeInTheDocument();
        return el;
      });

      // Clear any accidental character from the keydown/focus timing, then type
      await userEvent.clear(replaceInput);
      await userEvent.type(replaceInput, "director");
      await userEvent.keyboard("{Enter}");

      await waitFor(() => {
        expect(mockCreateFieldReview).toHaveBeenCalledWith(
          expect.objectContaining({
            result_id: 101,
            field_name: "role_archetype",
            is_correct: 0,
            correct_value: "director",
          }),
        );
      });
    });
  });
});
