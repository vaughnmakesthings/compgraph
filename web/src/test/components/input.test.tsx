import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { Input } from "@/components/ui/input";

describe("Input", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a basic input without label", () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
  });

  it("renders with a label and links it via htmlFor", () => {
    render(<Input label="Email address" />);
    const label = screen.getByText("Email address");
    expect(label).toBeInTheDocument();
    expect(label.tagName).toBe("LABEL");
    expect(label).toHaveAttribute("for", "email-address");
  });

  it("uses provided id over auto-generated id", () => {
    render(<Input label="Name" id="custom-id" />);
    const input = screen.getByLabelText("Name");
    expect(input).toHaveAttribute("id", "custom-id");
  });

  it("displays error message when error prop is set", () => {
    render(<Input label="Password" error="Password is required" />);
    expect(screen.getByText("Password is required")).toBeInTheDocument();
  });

  it("displays hint when no error is present", () => {
    render(<Input label="Name" hint="Enter your full name" />);
    expect(screen.getByText("Enter your full name")).toBeInTheDocument();
  });

  it("shows error instead of hint when both are provided", () => {
    render(
      <Input label="Name" hint="Enter your full name" error="Name is required" />,
    );
    expect(screen.getByText("Name is required")).toBeInTheDocument();
    expect(screen.queryByText("Enter your full name")).not.toBeInTheDocument();
  });

  it("renders rightElement inside the input container", () => {
    render(
      <Input
        label="Password"
        rightElement={<button type="button">Toggle</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Toggle" })).toBeInTheDocument();
  });

  it("accepts user input", async () => {
    const user = userEvent.setup();
    render(<Input label="Email" placeholder="you@example.com" />);
    const input = screen.getByLabelText("Email");
    await user.type(input, "test@test.com");
    expect(input).toHaveValue("test@test.com");
  });

  it("forwards native input props like type and required", () => {
    render(<Input label="Email" type="email" required />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("type", "email");
    expect(input).toBeRequired();
  });

  it("calls onFocus and onBlur handlers", async () => {
    const onFocus = vi.fn();
    const onBlur = vi.fn();
    const user = userEvent.setup();
    render(<Input label="Name" onFocus={onFocus} onBlur={onBlur} />);
    const input = screen.getByLabelText("Name");
    await user.click(input);
    expect(onFocus).toHaveBeenCalledTimes(1);
    await user.tab();
    expect(onBlur).toHaveBeenCalledTimes(1);
  });
});
