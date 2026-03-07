import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { useCompanies } from "@/lib/hooks/use-companies";
import { listCompaniesApiV1CompaniesGetOptions } from "@/api-client/@tanstack/react-query.gen";

vi.mock("@/api-client/@tanstack/react-query.gen", async () => {
  const { apiClientRqMock } = await import("./mocks/api-client-rq");
  return apiClientRqMock();
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

const mockCompanies = [
  { id: "c1", name: "Acosta", slug: "acosta", ats_platform: "jobsync" },
  { id: "c2", name: "Advantage", slug: "advantage", ats_platform: "icims" },
];

describe("useCompanies", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns loading state initially", () => {
    vi.mocked(listCompaniesApiV1CompaniesGetOptions).mockReturnValue({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      queryKey: ["companies"] as any,
      queryFn: vi.fn().mockReturnValue(new Promise(() => {})),
    });

    const { result } = renderHook(() => useCompanies(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("returns company data after query resolves", async () => {
    vi.mocked(listCompaniesApiV1CompaniesGetOptions).mockReturnValue({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      queryKey: ["companies"] as any,
      queryFn: vi.fn().mockResolvedValue(mockCompanies),
    });

    const { result } = renderHook(() => useCompanies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockCompanies);
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data![0].name).toBe("Acosta");
  });

  it("calls listCompaniesApiV1CompaniesGetOptions", () => {
    vi.mocked(listCompaniesApiV1CompaniesGetOptions).mockReturnValue({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      queryKey: ["companies"] as any,
      queryFn: vi.fn().mockResolvedValue([]),
    });

    renderHook(() => useCompanies(), { wrapper: createWrapper() });

    expect(listCompaniesApiV1CompaniesGetOptions).toHaveBeenCalled();
  });

  it("returns empty array when API returns no data", async () => {
    vi.mocked(listCompaniesApiV1CompaniesGetOptions).mockReturnValue({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      queryKey: ["companies"] as any,
      queryFn: vi.fn().mockResolvedValue([]),
    });

    const { result } = renderHook(() => useCompanies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
  });
});
