"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/data/badge";
import { api } from "@/lib/api-client";
import { formatRoleArchetype } from "@/lib/utils";
import type { PostingListItem } from "@/lib/types";

const PAGE_SIZE = 50;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatPayRange(min: number | null, max: number | null): string {
  if (min === null && max === null) return "—";
  const fmt = (n: number) =>
    n.toLocaleString("en-US", { minimumFractionDigits: n % 1 !== 0 ? 2 : 0, maximumFractionDigits: 2 });
  if (min !== null && max !== null) return `$${fmt(min)}–$${fmt(max)}`;
  if (min !== null) return `$${fmt(min)}+`;
  return `up to $${fmt(max!)}`;
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

  const [search, setSearch] = useState("");
  const [companyFilter, setCompanyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [roleFilter, setRoleFilter] = useState("");

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
        const result = await api.listPostings({ limit: PAGE_SIZE, offset });
        if (!cancelled) {
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
  }, [offset]);

  const uniqueRoles = useMemo(() => {
    const roles = new Set<string>();
    for (const item of items) {
      if (item.role_archetype) roles.add(item.role_archetype);
    }
    return [...roles].sort();
  }, [items]);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      if (search && !(item.title ?? "").toLowerCase().includes(search.toLowerCase())) {
        return false;
      }
      if (companyFilter && item.company_id !== companyFilter) {
        return false;
      }
      if (statusFilter === "active" && !item.is_active) return false;
      if (statusFilter === "inactive" && item.is_active) return false;
      if (roleFilter && item.role_archetype !== roleFilter) return false;
      return true;
    });
  }, [items, search, companyFilter, statusFilter, roleFilter]);

  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + PAGE_SIZE, total);

  const inputStyle: React.CSSProperties = {
    border: "1px solid #BFC0C0",
    borderRadius: "var(--radius-md, 6px)",
    padding: "6px 12px",
    fontSize: "13px",
    backgroundColor: "#FFFFFF",
    color: "#2D3142",
    fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
    outline: "none",
  };

  return (
    <div>
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display, 'Sora Variable', sans-serif)", color: "#2D3142" }}
        >
          Job Feed
        </h1>
        <p
          className="mt-1 text-sm"
          style={{ fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)", color: "#4F5D75" }}
        >
          All tracked postings across competitors
        </p>
      </div>

      {error && (
        <div
          className="mb-4 rounded-lg border px-4 py-3 text-sm"
          style={{
            backgroundColor: "#8C2C231A",
            borderColor: "#8C2C2333",
            color: "#8C2C23",
            fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          }}
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="flex flex-row gap-3 mb-4 flex-wrap">
        <input
          type="search"
          placeholder="Search postings..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={inputStyle}
          aria-label="Search postings"
        />

        <select
          value={companyFilter}
          onChange={(e) => setCompanyFilter(e.target.value)}
          style={inputStyle}
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
          style={inputStyle}
          aria-label="Filter by status"
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Closed</option>
        </select>

        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          style={inputStyle}
          aria-label="Filter by role"
        >
          <option value="">All Roles</option>
          {uniqueRoles.map((role) => (
            <option key={role} value={role}>
              {formatRoleArchetype(role)}
            </option>
          ))}
        </select>
      </div>

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
            ) : filtered.length === 0 ? (
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
              filtered.map((item) => (
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
                      {formatPayRange(item.pay_min, item.pay_max)}
                    </span>
                  </td>
                  {/* Status + date merged in one column (#182) */}
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      <Badge variant={item.is_active ? "success" : "error"}>
                        {item.is_active ? "Active" : "Closed"}
                      </Badge>
                      <span
                        style={{
                          fontSize: "11px",
                          color: "#8A8F98",
                          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                        }}
                      >
                        {item.is_active
                          ? `Since: ${formatDate(item.first_seen_at)}`
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
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
            disabled={offset === 0}
            style={{
              border: "1px solid #BFC0C0",
              borderRadius: "var(--radius-md, 6px)",
              padding: "4px 12px",
              fontSize: "13px",
              backgroundColor: "#FFFFFF",
              color: offset === 0 ? "#BFC0C0" : "#2D3142",
              cursor: offset === 0 ? "not-allowed" : "pointer",
              opacity: offset === 0 ? 0.5 : 1,
            }}
          >
            Prev
          </button>
          <button
            type="button"
            onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
            disabled={offset + PAGE_SIZE >= total}
            style={{
              border: "1px solid #BFC0C0",
              borderRadius: "var(--radius-md, 6px)",
              padding: "4px 12px",
              fontSize: "13px",
              backgroundColor: "#FFFFFF",
              color: offset + PAGE_SIZE >= total ? "#BFC0C0" : "#2D3142",
              cursor: offset + PAGE_SIZE >= total ? "not-allowed" : "pointer",
              opacity: offset + PAGE_SIZE >= total ? 0.5 : 1,
            }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
