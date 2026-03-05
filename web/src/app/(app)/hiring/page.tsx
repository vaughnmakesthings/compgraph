"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/data/badge";
import { TablePagination } from "@/components/data/table-pagination";
import {
  listCompaniesApiV1CompaniesGetOptions,
  listPostingsApiV1PostingsGetOptions
} from "@/api-client/@tanstack/react-query.gen";
import type { Company, PostingListResponse, PostingListItem } from "@/lib/types";
import { formatRoleArchetype } from "@/lib/utils";

const PAGE_SIZE = 50;

const ROLE_ARCHETYPES = [
  "field_rep",
  "merchandiser",
  "brand_ambassador",
  "demo_specialist",
  "team_lead",
  "manager",
  "recruiter",
  "corporate",
  "other",
] as const;

const SORT_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "first_seen_desc", label: "First Seen \u2193" },
  { value: "first_seen_asc", label: "First Seen \u2191" },
  { value: "pay_desc", label: "Pay High\u2013Low" },
  { value: "pay_asc", label: "Pay Low\u2013High" },
  { value: "title_asc", label: "Title A\u2013Z" },
];

// TODO: consolidate with lib/utils.ts
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatPayRange(
  min: number | null | undefined,
  max: number | null | undefined,
  currency?: string | null,
): string {
  if (min == null && max == null) return "\u2014";
  const fmt = (n: number) =>
    n.toLocaleString("en-US", {
      minimumFractionDigits: n % 1 !== 0 ? 2 : 0,
      maximumFractionDigits: 2,
    });
  let s: string;
  if (min != null && max != null) s = `$${fmt(min)}\u2013$${fmt(max)}`;
  else if (min != null) s = `$${fmt(min)}+`;
  else if (max != null) s = `up to $${fmt(max)}`;
  else return "\u2014";
  if (currency && currency !== "USD") s += ` ${currency}`;
  return s;
}

function SkeletonRow() {
  return (
    <tr>
      {Array.from({ length: 6 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="bg-[#E8E8E4] rounded h-[14px]" aria-hidden="true" />
        </td>
      ))}
    </tr>
  );
}

export default function HiringPage() {
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [roleFilter, setRoleFilter] = useState("");
  const [sortBy, setSortBy] = useState("first_seen_desc");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Companies list for filter
  const { data: companies } = useQuery({
    ...listCompaniesApiV1CompaniesGetOptions(),
    select: (data) => data as unknown as Company[],
  });

  const allCompanies = useMemo(() => {
    if (!companies) return [];
    return [...companies].sort((a, b) => a.name.localeCompare(b.name));
  }, [companies]);

  // Postings list
  const {
    data: postings,
    isLoading: loading,
    error: queryError
  } = useQuery({
    ...listPostingsApiV1PostingsGetOptions({
      query: {
        limit: PAGE_SIZE,
        offset,
        company_id: companyFilter || undefined,
        is_active: statusFilter === "all" ? undefined : statusFilter === "active",
        role_archetype: roleFilter || undefined,
        sort_by: sortBy,
        search: debouncedSearch || undefined,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any
    }),
    select: (data) => data as unknown as PostingListResponse,
  });

  const items = postings?.items ?? [];
  const total = postings?.total ?? 0;
  const error = queryError instanceof Error ? queryError.message : null;

  const hasActiveFilters =
    companyFilter !== "" ||
    statusFilter !== "all" ||
    roleFilter !== "" ||
    sortBy !== "first_seen_desc" ||
    searchInput !== "";

  const clearAll = useCallback(() => {
    setCompanyFilter("");
    setStatusFilter("all");
    setRoleFilter("");
    setSortBy("first_seen_desc");
    setSearchInput("");
    setOffset(0);
  }, []);

  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + PAGE_SIZE, total);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight font-display text-[#2D3142]">
          Job Feed
        </h1>
        <p className="mt-1 text-sm font-body text-[#4F5D75]">
          All tracked postings across competitors
        </p>
      </div>

      {error && (
        <div className="mb-4 border border-[#8C2C2333] px-4 py-3 text-sm bg-[#8C2C231A] rounded-lg text-[#8C2C23] font-body" role="alert">
          {error}
        </div>
      )}

      <div className="flex flex-row gap-2 mb-2 flex-wrap items-center">
        <input
          type="search"
          placeholder="Search postings..."
          value={searchInput}
          onChange={(e) => {
            setSearchInput(e.target.value);
            setOffset(0);
          }}
          className="border border-[#BFC0C0] rounded px-3 py-1.5 text-[13px] bg-white text-[#2D3142] font-body"
          aria-label="Search postings"
        />

        <select
          value={companyFilter}
          onChange={(e) => {
            setCompanyFilter(e.target.value);
            setOffset(0);
          }}
          className="border border-[#BFC0C0] rounded px-3 py-1.5 text-[13px] bg-white text-[#2D3142] font-body min-w-[10rem] appearance-none pr-8 bg-no-repeat bg-[right_10px_center]"
          style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%234F5D75' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")` }}
          aria-label="Filter by company"
        >
          <option value="">All Companies</option>
          {allCompanies.map(({ id, name }) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as "all" | "active" | "inactive");
            setOffset(0);
          }}
          className="border border-[#BFC0C0] rounded px-3 py-1.5 text-[13px] bg-white text-[#2D3142] font-body min-w-[10rem] appearance-none pr-8 bg-no-repeat bg-[right_10px_center]"
          style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%234F5D75' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")` }}
          aria-label="Filter by status"
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>

        <select
          value={roleFilter}
          onChange={(e) => {
            setRoleFilter(e.target.value);
            setOffset(0);
          }}
          className="border border-[#BFC0C0] rounded px-3 py-1.5 text-[13px] bg-white text-[#2D3142] font-body min-w-[10rem] appearance-none pr-8 bg-no-repeat bg-[right_10px_center]"
          style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%234F5D75' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")` }}
          aria-label="Filter by role"
        >
          <option value="">All Roles</option>
          {ROLE_ARCHETYPES.map((role) => (
            <option key={role} value={role}>
              {formatRoleArchetype(role)}
            </option>
          ))}
        </select>

        <select
          value={sortBy}
          onChange={(e) => {
            setSortBy(e.target.value);
            setOffset(0);
          }}
          className="border border-[#BFC0C0] rounded px-3 py-1.5 text-[13px] bg-white text-[#2D3142] font-body min-w-[10rem] appearance-none pr-8 bg-no-repeat bg-[right_10px_center]"
          style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%234F5D75' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E")` }}
          aria-label="Sort by"
        >
          {SORT_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {hasActiveFilters && (
        <div className="flex flex-row gap-2 mb-4 flex-wrap items-center">
          {companyFilter && (
            <span className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm bg-[#E8E8E4] text-[#2D3142] font-body">
              Company: {allCompanies.find((c) => c.id === companyFilter)?.name ?? companyFilter}
              <button
                type="button"
                onClick={() => { setCompanyFilter(""); setOffset(0); }}
                aria-label="Remove company filter"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {statusFilter !== "all" && (
            <span className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm bg-[#E8E8E4] text-[#2D3142] font-body">
              Status: {statusFilter === "active" ? "Active" : "Inactive"}
              <button
                type="button"
                onClick={() => { setStatusFilter("all"); setOffset(0); }}
                aria-label="Remove status filter"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {roleFilter && (
            <span className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm bg-[#E8E8E4] text-[#2D3142] font-body">
              Role: {formatRoleArchetype(roleFilter)}
              <button
                type="button"
                onClick={() => { setRoleFilter(""); setOffset(0); }}
                aria-label="Remove role filter"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {searchInput && (
            <span className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm bg-[#E8E8E4] text-[#2D3142] font-body">
              Search: &quot;{searchInput}&quot;
              <button
                type="button"
                onClick={() => setSearchInput("")}
                aria-label="Clear search"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {sortBy !== "first_seen_desc" && (
            <span className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm bg-[#E8E8E4] text-[#2D3142] font-body">
              Sort: {SORT_OPTIONS.find((o) => o.value === sortBy)?.label ?? sortBy}
              <button
                type="button"
                onClick={() => setSortBy("first_seen_desc")}
                aria-label="Reset sort"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearAll}
              className="text-sm underline text-[#4F5D75] font-body"
            >
              Clear all
            </button>
          )}
        </div>
      )}

      <div className="rounded-lg border border-[#BFC0C0] overflow-hidden bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#E8E8E4]">
              {["Title", "Company", "Location", "Role", "Pay Range", "Status"].map(
                (col) => (
                  <th
                    key={col}
                    className="text-left px-4 py-2 font-semibold text-[#2D3142] font-body"
                  >
                    {col}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-[#4F5D75] font-body">
                  No postings match your filters
                </td>
              </tr>
            ) : (
              items.map((item: PostingListItem) => (
                <tr
                  key={item.id}
                  className="border-b last:border-b-0 border-[#BFC0C0]"
                >
                  <td
                    className="px-4 py-3 max-w-xs truncate text-[#2D3142] font-body"
                    title={item.title ?? ""}
                  >
                    {item.title ?? "\u2014"}
                  </td>
                  <td className="px-4 py-3 text-[#2D3142] font-body">
                    {item.company_name ?? item.company_id}
                  </td>
                  <td className="px-4 py-3 text-[#4F5D75] font-body">
                    {item.location ?? "\u2014"}
                  </td>
                  <td className="px-4 py-3">
                    {item.role_archetype ? (
                      <Badge variant="neutral">{formatRoleArchetype(item.role_archetype)}</Badge>
                    ) : (
                      <span className="text-[#4F5D75]">\u2014</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-[#4F5D75]">
                      {formatPayRange(item.pay_min, item.pay_max, item.pay_currency)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      <Badge variant={item.is_active ? "success" : "error"}>
                        {item.is_active ? "Active" : "Inactive"}
                      </Badge>
                      <span className="text-[11px] text-[#4F5D75] font-body">
                        {item.is_active
                          ? `Start: ${formatDate(item.first_seen_at)}`
                          : item.last_seen_at
                            ? `Closed: ${formatDate(item.last_seen_at)}`
                            : `Seen: ${formatDate(item.first_seen_at)}`}
                      </span>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center justify-between font-body text-[13px] text-[#4F5D75]">
        <span>
          {total === 0 ? "No postings" : `Showing ${start}\u2013${end} of ${total}`}
        </span>
        <TablePagination
          page={total === 0 ? 1 : Math.floor(offset / PAGE_SIZE) + 1}
          totalPages={total === 0 ? 1 : Math.ceil(total / PAGE_SIZE)}
          onFirst={() => setOffset(0)}
          onPrev={() => setOffset((p) => Math.max(0, p - PAGE_SIZE))}
          onNext={() => setOffset((p) => p + PAGE_SIZE)}
          onLast={() =>
            setOffset((Math.ceil(total / PAGE_SIZE) - 1) * PAGE_SIZE)
          }
        />
      </div>
    </div>
  );
}
