"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/data/badge";
import { TablePagination } from "@/components/data/table-pagination";
import { api } from "@/lib/api-client";
import { formatRoleArchetype } from "@/lib/utils";
import type { PostingListItem } from "@/lib/types";

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;

/** Canonical role archetypes from enrichment schema — used for filter dropdown (not derived from current page). */
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
  { value: "first_seen_desc", label: "First Seen ↓" },
  { value: "first_seen_asc", label: "First Seen ↑" },
  { value: "pay_desc", label: "Pay High–Low" },
  { value: "pay_asc", label: "Pay Low–High" },
  { value: "title_asc", label: "Title A–Z" },
];

const CHEVRON_SVG =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%234F5D75' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")";

const controlStyle: React.CSSProperties = {
  border: "1px solid var(--color-border, #BFC0C0)",
  borderRadius: "var(--radius-sm, 4px)",
  padding: "6px 12px",
  fontSize: "13px",
  backgroundColor: "var(--color-surface, #FFFFFF)",
  color: "var(--color-foreground, #2D3142)",
  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
};

const selectStyle: React.CSSProperties = {
  ...controlStyle,
  minWidth: "10rem",
  appearance: "none",
  backgroundImage: CHEVRON_SVG,
  backgroundRepeat: "no-repeat",
  backgroundPosition: "right 10px center",
  paddingRight: "32px",
};

const chipStyle: React.CSSProperties = {
  backgroundColor: "var(--color-muted, #E8E8E4)",
  color: "var(--color-foreground, #2D3142)",
  fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatPayRange(
  min: number | null,
  max: number | null,
  currency?: string | null,
): string {
  if (min === null && max === null) return "—";
  const fmt = (n: number) =>
    n.toLocaleString("en-US", {
      minimumFractionDigits: n % 1 !== 0 ? 2 : 0,
      maximumFractionDigits: 2,
    });
  let s: string;
  if (min !== null && max !== null) s = `$${fmt(min)}–$${fmt(max)}`;
  else if (min !== null) s = `$${fmt(min)}+`;
  else s = `up to $${fmt(max!)}`;
  if (currency && currency !== "USD") s += ` ${currency}`;
  return s;
}

function SkeletonRow() {
  return (
    <tr>
      {Array.from({ length: 6 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div
            style={{ backgroundColor: "#E8E8E4", borderRadius: "4px", height: "14px" }}
            aria-hidden="true"
          />
        </td>
      ))}
    </tr>
  );
}

export default function HiringPage() {
  const [items, setItems] = useState<PostingListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  const [searchInput, setSearchInput] = useState("");
  const [searchDebounced, setSearchDebounced] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [roleFilter, setRoleFilter] = useState("");
  const [sortBy, setSortBy] = useState("first_seen_desc");

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setSearchDebounced(searchInput.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Reset to page 1 and clear any stale error when filters change
  useEffect(() => {
    setOffset(0);
    setError(null);
  }, [companyFilter, statusFilter, roleFilter, sortBy, searchDebounced]);

  // All companies fetched once on mount — not derived from current page (#173)
  const [allCompanies, setAllCompanies] = useState<Array<{ id: string; name: string }>>([]);

  useEffect(() => {
    api.getCompanies()
      .then((cos) => setAllCompanies(cos.map((c) => ({ id: c.id, name: c.name })).sort((a, b) => a.name.localeCompare(b.name))))
      .catch(() => {/* non-fatal: company filter falls back to empty */});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    async function load() {
      try {
        const result = await api.listPostings({
          limit: PAGE_SIZE,
          offset,
          company_id: companyFilter || undefined,
          is_active: statusFilter === "all" ? undefined : statusFilter === "active",
          role_archetype: roleFilter || undefined,
          sort_by: sortBy,
          search: searchDebounced || undefined,
        });
        if (!cancelled) {
          setError(null);
          setItems(result.items);
          setTotal(result.total);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load postings");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [offset, companyFilter, statusFilter, roleFilter, sortBy, searchDebounced]);

  const hasActiveFilters =
    companyFilter !== "" ||
    statusFilter !== "all" ||
    roleFilter !== "" ||
    sortBy !== "first_seen_desc" ||
    searchDebounced !== "";

  const clearAll = useCallback(() => {
    setCompanyFilter("");
    setStatusFilter("all");
    setRoleFilter("");
    setSortBy("first_seen_desc");
    setSearchInput("");
    setSearchDebounced("");
    setOffset(0);
  }, []);

  const removeCompanyChip = () => setCompanyFilter("");
  const removeStatusChip = () => setStatusFilter("all");
  const removeRoleChip = () => setRoleFilter("");
  const removeSortChip = () => setSortBy("first_seen_desc");
  const removeSearchChip = () => {
    setSearchInput("");
    setSearchDebounced("");
  };

  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + PAGE_SIZE, total);

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display, 'Sora Variable', sans-serif)", color: "var(--color-foreground, #2D3142)" }}
        >
          Job Feed
        </h1>
        <p
          className="mt-1 text-sm"
          style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", color: "var(--color-muted-foreground, #4F5D75)" }}
        >
          All tracked postings across competitors
        </p>
      </div>

      {error && (
        <div
          className="mb-4 border px-4 py-3 text-sm"
          style={{
            backgroundColor: "var(--color-error-muted, #8C2C231A)",
            borderColor: "#8C2C2333",
            borderRadius: "var(--radius-lg, 8px)",
            color: "var(--color-error, #8C2C23)",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          }}
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="flex flex-row gap-2 mb-2 flex-wrap items-center">
        <input
          type="search"
          placeholder="Search postings..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          style={controlStyle}
          aria-label="Search postings"
        />

        <select
          value={companyFilter}
          onChange={(e) => setCompanyFilter(e.target.value)}
          style={selectStyle}
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
          onChange={(e) => setStatusFilter(e.target.value as "all" | "active" | "inactive")}
          style={selectStyle}
          aria-label="Filter by status"
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>

        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          style={selectStyle}
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
          onChange={(e) => setSortBy(e.target.value)}
          style={selectStyle}
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
            <span
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm"
              style={chipStyle}
            >
              Company: {allCompanies.find((c) => c.id === companyFilter)?.name ?? companyFilter}
              <button
                type="button"
                onClick={removeCompanyChip}
                aria-label="Remove company filter"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {statusFilter !== "all" && (
            <span
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm"
              style={chipStyle}
            >
              Status: {statusFilter === "active" ? "Active" : "Inactive"}
              <button
                type="button"
                onClick={removeStatusChip}
                aria-label="Remove status filter"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {roleFilter && (
            <span
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm"
              style={chipStyle}
            >
              Role: {formatRoleArchetype(roleFilter)}
              <button
                type="button"
                onClick={removeRoleChip}
                aria-label="Remove role filter"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {searchDebounced && (
            <span
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm"
              style={chipStyle}
            >
              Search: &quot;{searchDebounced}&quot;
              <button
                type="button"
                onClick={removeSearchChip}
                aria-label="Clear search"
                className="ml-1 hover:opacity-70"
              >
                ×
              </button>
            </span>
          )}
          {sortBy !== "first_seen_desc" && (
            <span
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm"
              style={chipStyle}
            >
              Sort: {SORT_OPTIONS.find((o) => o.value === sortBy)?.label ?? sortBy}
              <button
                type="button"
                onClick={removeSortChip}
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
              className="text-sm underline"
              style={{
                color: "#4F5D75",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              }}
            >
              Clear all
            </button>
          )}
        </div>
      )}

      <div
        className="rounded-lg border overflow-hidden"
        style={{ borderColor: "#BFC0C0", backgroundColor: "#FFFFFF" }}
      >
        <table className="w-full text-sm">
          <thead>
            <tr style={{ backgroundColor: "#E8E8E4" }}>
              {["Title", "Company", "Location", "Role", "Pay Range", "Status"].map(
                (col) => (
                  <th
                    key={col}
                    className="text-left px-4 py-2 font-semibold"
                    style={{ color: "#2D3142", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
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
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center text-sm"
                  style={{ color: "#4F5D75", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
                >
                  No postings match your filters
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b last:border-b-0"
                  style={{ borderColor: "#BFC0C0" }}
                >
                  <td
                    className="px-4 py-3 max-w-xs truncate"
                    style={{ color: "#2D3142", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
                    title={item.title ?? ""}
                  >
                    {item.title ?? "—"}
                  </td>
                  <td
                    className="px-4 py-3"
                    style={{ color: "#2D3142", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
                  >
                    {item.company_name ?? item.company_id}
                  </td>
                  <td
                    className="px-4 py-3"
                    style={{ color: "#4F5D75", fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)" }}
                  >
                    {item.location ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    {item.role_archetype ? (
                      <Badge variant="neutral">{formatRoleArchetype(item.role_archetype)}</Badge>
                    ) : (
                      <span style={{ color: "#4F5D75" }}>—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      style={{
                        fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                        fontSize: "12px",
                        color: "#4F5D75",
                      }}
                    >
                      {formatPayRange(item.pay_min, item.pay_max, item.pay_currency)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      <Badge variant={item.is_active ? "success" : "error"}>
                        {item.is_active ? "Active" : "Inactive"}
                      </Badge>
                      <span
                        style={{
                          fontSize: "11px",
                          color: "var(--color-blue-slate, #4F5D75)",
                          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                        }}
                      >
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

      <div
        className="mt-3 flex items-center justify-between"
        style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", fontSize: "13px", color: "#4F5D75" }}
      >
        <span>
          {total === 0 ? "No postings" : `Showing ${start}–${end} of ${total}`}
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
