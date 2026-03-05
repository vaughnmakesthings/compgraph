"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/data/badge";
import { getVelocityApiV1AggregationVelocityGetOptions } from "@/api-client/@tanstack/react-query.gen";
import type { DailyVelocity } from "@/lib/types";
import { COMPANIES, type StaticCompany } from "@/lib/constants";

function CompanyCard({
  company,
  activePostings,
  loading,
  onClick,
}: {
  company: StaticCompany;
  activePostings: number | null;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="block w-full text-left"
      aria-label={`View ${company.name} details`}
    >
      <div className="bg-white border border-[#BFC0C0] border-l-[3px] border-l-[#EF8354] rounded-lg p-5 shadow-sm transition-shadow duration-150 ease-in hover:shadow-md cursor-pointer">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2 className="font-semibold font-body text-[15px] text-[#2D3142] leading-[1.3]">
            {company.name}
          </h2>
          <Badge variant="neutral" size="sm">
            {company.ats}
          </Badge>
        </div>
        <div className="flex items-baseline gap-1">
          <span className={`font-mono text-2xl font-semibold leading-none ${loading ? 'text-[#BFC0C0]' : 'text-[#2D3142]'}`}>
            {loading ? "\u2014" : activePostings !== null ? activePostings.toLocaleString() : "\u2014"}
          </span>
          <span className="font-body text-xs text-[#4F5D75]">
            active postings
          </span>
        </div>
      </div>
    </button>
  );
}

export default function CompetitorsPage() {
  const router = useRouter();

  const { data: velocity, isLoading, error } = useQuery({
    ...getVelocityApiV1AggregationVelocityGetOptions(),
    select: (data) => data as unknown as DailyVelocity[],
  });

  const activeByCompanySlug = useMemo(() => {
    const latestDate: Record<string, string> = {};
    const latestCount: Record<string, number> = {};
    if (!velocity) return latestCount;

    for (const row of velocity) {
      if (!row.company_slug || !row.date) continue;
      const slug = row.company_slug;
      if (!(slug in latestDate) || row.date > latestDate[slug]) {
        latestDate[slug] = row.date;
        latestCount[slug] = row.active_postings ?? 0;
      }
    }
    return latestCount;
  }, [velocity]);

  function resolveActivePostings(company: StaticCompany): number | null {
    const count = activeByCompanySlug[company.slug];
    return count !== undefined ? count : null;
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight font-display">
          Competitors
        </h1>
        <p className="mt-1 text-sm font-body text-muted-foreground">
          Field marketing agencies in our competitive set
        </p>
      </div>

      {error && (
        <div
          className="mb-6 rounded-lg border-l-[3px] border-l-[#8C2C23] px-4 py-3 text-sm bg-[#8C2C231A] text-[#8C2C23] font-body"
          role="alert"
        >
          {error instanceof Error ? error.message : "Failed to load competitor data. Please try again."}
        </div>
      )}

      <div className="grid gap-4 grid-cols-[repeat(auto-fill,minmax(280px,1fr))]">
        {COMPANIES.map((company) => (
          <CompanyCard
            key={company.slug}
            company={company}
            activePostings={resolveActivePostings(company)}
            loading={isLoading}
            onClick={() => router.push(`/competitors/${company.slug}`)}
          />
        ))}
      </div>
    </div>
  );
}
