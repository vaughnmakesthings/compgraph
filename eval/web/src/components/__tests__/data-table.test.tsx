import { describe, it, expect } from "vitest";
import { axe } from "vitest-axe";
import { render, screen } from "@/__tests__/helpers/render";
import { DataTable, type Column } from "@/components/data-table";

interface TestRow {
  name: string;
  score: number;
  [key: string]: unknown;
}

const columns: Column<TestRow>[] = [
  { key: "name", label: "Name" },
  { key: "score", label: "Score", align: "right", mono: true },
];

const data: TestRow[] = [
  { name: "Alice", score: 95 },
  { name: "Bob", score: 82 },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(<DataTable columns={columns} data={data} ariaLabel="Test table" />);
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Score")).toBeInTheDocument();
  });

  it("renders data rows", () => {
    render(<DataTable columns={columns} data={data} ariaLabel="Test table" />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("82")).toBeInTheDocument();
  });

  it("applies right alignment to header and cells", () => {
    render(<DataTable columns={columns} data={data} ariaLabel="Test table" />);
    const scoreHeader = screen.getByText("Score");
    expect(scoreHeader.className).toContain("text-right");
  });

  it("applies mono class to numeric cells", () => {
    render(<DataTable columns={columns} data={data} ariaLabel="Test table" />);
    const scoreCell = screen.getByText("95");
    expect(scoreCell.className).toContain("font-mono");
    expect(scoreCell.className).toContain("tabular-nums");
  });

  it("supports custom render function", () => {
    const customColumns: Column<TestRow>[] = [
      { key: "name", label: "Name", render: (row) => <strong>{row.name}</strong> },
    ];
    render(<DataTable columns={customColumns} data={data} ariaLabel="Test table" />);
    const bold = screen.getByText("Alice");
    expect(bold.tagName).toBe("STRONG");
  });

  it("sets aria-label on the table", () => {
    render(<DataTable columns={columns} data={data} ariaLabel="Test table" />);
    expect(screen.getByRole("table", { name: "Test table" })).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <DataTable columns={columns} data={data} ariaLabel="Test table" />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
