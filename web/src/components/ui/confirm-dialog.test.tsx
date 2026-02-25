import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { ConfirmDialog } from "./confirm-dialog";

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
    title: "Delete All Data",
    description: "This action cannot be undone.",
    onConfirm: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and description when open", () => {
    render(<ConfirmDialog {...defaultProps} />);

    expect(screen.getByText("Delete All Data")).toBeInTheDocument();
    expect(screen.getByText("This action cannot be undone.")).toBeInTheDocument();
  });

  it("does not render content when closed", () => {
    render(<ConfirmDialog {...defaultProps} open={false} />);

    expect(screen.queryByText("Delete All Data")).not.toBeInTheDocument();
  });

  it("renders default confirm and cancel labels", () => {
    render(<ConfirmDialog {...defaultProps} />);

    expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("renders custom confirm and cancel labels", () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        confirmLabel="Yes, delete"
        cancelLabel="No, keep it"
      />,
    );

    expect(screen.getByRole("button", { name: "Yes, delete" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "No, keep it" })).toBeInTheDocument();
  });

  it("calls onConfirm when confirm button is clicked", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onOpenChange(false) when cancel button is clicked", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("does not call onConfirm when cancel is clicked", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(defaultProps.onConfirm).not.toHaveBeenCalled();
  });

  it("calls onOpenChange(false) on Escape key", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.keyboard("{Escape}");

    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("does not call onConfirm on Escape key", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.keyboard("{Escape}");

    expect(defaultProps.onConfirm).not.toHaveBeenCalled();
  });

  it("calls onOpenChange(false) on overlay click", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    const dialog = screen.getByRole("dialog");
    await user.click(dialog);

    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  it("renders danger variant with red confirm button", () => {
    render(<ConfirmDialog {...defaultProps} confirmVariant="danger" />);

    const confirmBtn = screen.getByRole("button", { name: "Confirm" });
    expect(confirmBtn).toHaveStyle({ backgroundColor: "#8C2C23" });
  });

  it("renders default variant with coral confirm button", () => {
    render(<ConfirmDialog {...defaultProps} confirmVariant="default" />);

    const confirmBtn = screen.getByRole("button", { name: "Confirm" });
    expect(confirmBtn).toHaveStyle({ backgroundColor: "#EF8354" });
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

    expect(screen.getByRole("button", { name: "Deleting..." })).toBeInTheDocument();

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

  it("closes dialog after synchronous onConfirm", async () => {
    const user = userEvent.setup();
    render(<ConfirmDialog {...defaultProps} />);

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });
});
