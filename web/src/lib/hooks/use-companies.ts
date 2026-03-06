"use client";

import { useQuery } from "@tanstack/react-query";
import { listCompaniesApiV1CompaniesGetOptions } from "@/api-client/@tanstack/react-query.gen";
import type { Company } from "@/lib/types";

export function useCompanies() {
  return useQuery({
    ...listCompaniesApiV1CompaniesGetOptions(),
    select: (data) => data as unknown as Company[],
    staleTime: 5 * 60 * 1000,
  });
}
