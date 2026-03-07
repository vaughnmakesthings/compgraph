import { render, screen } from "@testing-library/react";

import "../mocks/resize-observer";

vi.mock("@tremor/react", async () => {
  const { tremorMockWithCategories } = await import("../mocks/tremor");
  return tremorMockWithCategories();
});

import { BarChart } from "@/components/charts/bar-chart";
import { AreaChart } from "@/components/charts/area-chart";
import { DonutChart } from "@/components/charts/donut-chart";

const barAreaData = [
  { month: "Jan", postings_count: 120, enriched_count: 95 },
  { month: "Feb", postings_count: 200, enriched_count: 180 },
];

const bars = [
  { dataKey: "postings_count", name: "Postings" },
  { dataKey: "enriched_count", name: "Enriched" },
];

const areas = [
  { dataKey: "postings_count", name: "Postings" },
  { dataKey: "enriched_count", name: "Enriched" },
];

const donutData = [
  { name: "Active", value: 300 },
  { name: "Expired", value: 120 },
  { name: "Pending", value: 45 },
];

describe("BarChart", () => {
  it("renders bar-chart container", () => {
    render(<BarChart data={barAreaData} bars={bars} xDataKey="month" />);

    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("maps bar names to categories", () => {
    render(<BarChart data={barAreaData} bars={bars} xDataKey="month" />);

    expect(screen.getByTestId("bar-Postings")).toBeInTheDocument();
    expect(screen.getByTestId("bar-Enriched")).toBeInTheDocument();
  });

  it("remaps data from dataKey to name", () => {
    render(<BarChart data={barAreaData} bars={bars} xDataKey="month" />);

    const chartData = JSON.parse(
      screen.getByTestId("chart-data").textContent!,
    );

    expect(chartData).toHaveLength(2);
    expect(chartData[0]).toEqual({
      month: "Jan",
      Postings: 120,
      Enriched: 95,
    });
    expect(chartData[1]).toEqual({
      month: "Feb",
      Postings: 200,
      Enriched: 180,
    });
  });

  it("container has default height of 300", () => {
    const { container } = render(
      <BarChart data={barAreaData} bars={bars} xDataKey="month" />,
    );

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.style.height).toBe("300px");
  });
});

describe("AreaChart", () => {
  it("renders area-chart container", () => {
    render(<AreaChart data={barAreaData} areas={areas} xDataKey="month" />);

    expect(screen.getByTestId("area-chart")).toBeInTheDocument();
  });

  it("maps area names to categories", () => {
    render(<AreaChart data={barAreaData} areas={areas} xDataKey="month" />);

    expect(screen.getByTestId("area-Postings")).toBeInTheDocument();
    expect(screen.getByTestId("area-Enriched")).toBeInTheDocument();
  });

  it("remaps data from dataKey to name", () => {
    render(<AreaChart data={barAreaData} areas={areas} xDataKey="month" />);

    const chartData = JSON.parse(
      screen.getByTestId("chart-data").textContent!,
    );

    expect(chartData).toHaveLength(2);
    expect(chartData[0]).toEqual({
      month: "Jan",
      Postings: 120,
      Enriched: 95,
    });
    expect(chartData[1]).toEqual({
      month: "Feb",
      Postings: 200,
      Enriched: 180,
    });
  });
});

describe("DonutChart", () => {
  it("renders donut-chart container", () => {
    render(<DonutChart data={donutData} />);

    expect(screen.getByTestId("donut-chart")).toBeInTheDocument();
  });

  it("passes data through unchanged", () => {
    render(<DonutChart data={donutData} />);

    const chartData = JSON.parse(
      screen.getByTestId("chart-data").textContent!,
    );

    expect(chartData).toEqual([
      { name: "Active", value: 300 },
      { name: "Expired", value: 120 },
      { name: "Pending", value: 45 },
    ]);
  });

  it("container has default height of 280", () => {
    const { container } = render(<DonutChart data={donutData} />);

    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.style.height).toBe("280px");
  });
});
