import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

// Mock Tremor Dialog to enable Escape key and overlay click testing in jsdom
vi.mock("@tremor/react", () => ({
  Dialog: ({
    open,
    onClose,
    children,
  }: {
    open: boolean;
    onClose: (val: boolean) => void;
    children: React.ReactNode;
  }) => {
    useEffect(() => {
      if (!open) return;
      const handler = (e: KeyboardEvent) => {
        if (e.key === "Escape") onClose(false);
      };
      document.addEventListener("keydown", handler);
      return () => document.removeEventListener("keydown", handler);
    }, [open, onClose]);

    if (!open) return null;
    return (
      <div
        role="dialog"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose(false);
        }}
      >
        {children}
      </div>
    );
  },
  DialogPanel: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

describe("ConfirmDialog", () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    title: "Confirm Action",
    description: "Are you sure?",
    onConfirm: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders when open={true}", () => {
    render(<ConfirmDialog {...defaultProps} />);
    expect(screen.getByText("Confirm Action")).toBeInTheDocument();
    expect(screen.getByText("Are you sure?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("does not render content when open={false}", () => {
    render(<ConfirmDialog {...defaultProps} open={false} />);
    expect(screen.queryByText("Confirm Action")).not.toBeInTheDocument();
  });

  it("Cancel closes without calling onConfirm", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
    expect(defaultProps.onConfirm).not.toHaveBeenCalled();
  });

  it("Confirm calls onConfirm and closes", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("renders custom confirm and cancel labels", () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        confirmLabel="Confirm & Start"
        cancelLabel="Back"
      />,
    );
    expect(
      screen.getByRole("button", { name: "Confirm & Start" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument();
  });

  it("danger variant applies danger styling to confirm button", () => {
    render(<ConfirmDialog {...defaultProps} confirmVariant="danger" />);
    const confirmBtn = screen.getByRole("button", { name: "Confirm" });
    expect(confirmBtn).toHaveStyle({ backgroundColor: "#8C2C23" });
  });

  it("default variant applies coral styling to confirm button", () => {
    render(<ConfirmDialog {...defaultProps} confirmVariant="default" />);
    const confirmBtn = screen.getByRole("button", { name: "Confirm" });
    expect(confirmBtn).toHaveStyle({ backgroundColor: "#EF8354" });
  });

  it("calls onOpenChange(false) on Escape key", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.keyboard("{Escape}");

    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
    expect(defaultProps.onConfirm).not.toHaveBeenCalled();
  });

  it("calls onOpenChange(false) on overlay click", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    const dialog = screen.getByRole("dialog");
    await user.click(dialog);

    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("shows confirmingLabel during async onConfirm", async () => {
    const user = userEvent.setup();
    let resolveConfirm: () => void;
    const asyncConfirm = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveConfirm = resolve;
        }),
    );

    render(
      <ConfirmDialog
        {...defaultProps}
        onConfirm={asyncConfirm}
        confirmingLabel="Deleting..."
      />,
    );

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(
      screen.getByRole("button", { name: "Deleting..." }),
    ).toBeInTheDocument();

    resolveConfirm!();

    await waitFor(() => {
      expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("disables confirm button during async onConfirm", async () => {
    const user = userEvent.setup();
    let resolveConfirm: () => void;
    const asyncConfirm = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveConfirm = resolve;
        }),
    );

    render(
      <ConfirmDialog
        {...defaultProps}
        onConfirm={asyncConfirm}
        confirmingLabel="Working..."
      />,
    );

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    const confirmBtn = screen.getByRole("button", { name: "Working..." });
    expect(confirmBtn).toBeDisabled();

    resolveConfirm!();

    await waitFor(() => {
      expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
