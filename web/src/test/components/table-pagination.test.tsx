import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TablePagination } from "@/components/data/table-pagination";

function renderPagination(page: number, totalPages: number) {
  const handlers = {
    onFirst: vi.fn(),
    onPrev: vi.fn(),
    onNext: vi.fn(),
    onLast: vi.fn(),
  };
  render(
    <TablePagination page={page} totalPages={totalPages} {...handlers} />
  );
  return handlers;
}

describe("TablePagination", () => {
  it("displays page info text", () => {
    renderPagination(3, 10);
    expect(screen.getByText("Page 3 of 10")).toBeInTheDocument();
  });

  it("renders all four navigation buttons", () => {
    renderPagination(2, 5);
    expect(screen.getByRole("button", { name: "First page" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Last page" })).toBeInTheDocument();
  });

  it("disables First and Previous on page 1", () => {
    renderPagination(1, 5);
    expect(screen.getByRole("button", { name: "First page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
  });

  it("enables Next and Last when not on last page", () => {
    renderPagination(1, 5);
    expect(screen.getByRole("button", { name: "Next page" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Last page" })).toBeEnabled();
  });

  it("disables Next and Last on last page", () => {
    renderPagination(5, 5);
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Last page" })).toBeDisabled();
  });

  it("enables all buttons on a middle page", () => {
    renderPagination(3, 5);
    expect(screen.getByRole("button", { name: "First page" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next page" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Last page" })).toBeEnabled();
  });

  it("disables all buttons when there is only one page", () => {
    renderPagination(1, 1);
    expect(screen.getByRole("button", { name: "First page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Last page" })).toBeDisabled();
  });

  it("fires click handlers on enabled buttons", async () => {
    const user = userEvent.setup();
    const handlers = renderPagination(3, 5);

    await user.click(screen.getByRole("button", { name: "First page" }));
    expect(handlers.onFirst).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Previous page" }));
    expect(handlers.onPrev).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(handlers.onNext).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Last page" }));
    expect(handlers.onLast).toHaveBeenCalledTimes(1);
  });
});
