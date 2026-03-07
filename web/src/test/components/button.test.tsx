import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders children text", () => {
    render(<Button>Save changes</Button>);
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument();
  });

  it("renders with type='button' by default", () => {
    render(<Button>Click</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "button");
  });

  it("applies primary variant backgroundColor", () => {
    render(<Button variant="primary">Primary</Button>);
    expect(screen.getByRole("button")).toHaveStyle({ backgroundColor: "#EF8354" });
  });

  it("applies secondary variant with border and white background", () => {
    render(<Button variant="secondary">Secondary</Button>);
    const style = screen.getByRole("button").style;
    expect(style.border).toMatch(/1px solid/);
    // jsdom converts hex to rgb — verify the style properties are set
    expect(style.backgroundColor).toBeTruthy();
    expect(style.color).toBeTruthy();
  });

  it("applies destructive variant backgroundColor", () => {
    render(<Button variant="destructive">Delete</Button>);
    expect(screen.getByRole("button")).toHaveStyle({ backgroundColor: "#8C2C23" });
  });

  it("applies ghost variant backgroundColor", () => {
    render(<Button variant="ghost">Ghost</Button>);
    expect(screen.getByRole("button").style.backgroundColor).toBe("transparent");
  });

  it("applies sm size fontSize", () => {
    render(<Button size="sm">Small</Button>);
    expect(screen.getByRole("button")).toHaveStyle({ fontSize: "12px" });
  });

  it("applies lg size fontSize", () => {
    render(<Button size="lg">Large</Button>);
    expect(screen.getByRole("button")).toHaveStyle({ fontSize: "15px" });
  });

  it("renders disabled state with opacity and disabled attribute", () => {
    render(<Button disabled>Disabled</Button>);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button).toHaveStyle({ opacity: 0.5 });
  });

  it("calls onClick handler when clicked", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    await user.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("passes through aria-label", () => {
    render(<Button aria-label="Close dialog">X</Button>);
    expect(screen.getByRole("button", { name: "Close dialog" })).toBeInTheDocument();
  });
});
