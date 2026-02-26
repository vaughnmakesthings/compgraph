"use client";

import { useState, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { AllCommunityModule, ModuleRegistry, type ColDef, type ICellRendererParams } from "ag-grid-community";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import type { Variant } from "./comparison-panel";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

// ---------------------------------------------------------------------------
// Canonical table data — identical for all variants
// ---------------------------------------------------------------------------

interface Posting {
  id: number;
  company: string;
  title: string;
  location: string;
  payMin: number;
  payMax: number;
  status: "active" | "stale" | "closed";
  postedDate: string;
}

const TABLE_DATA: Posting[] = [
  { id: 1, company: "T-ROC", title: "Brand Ambassador", location: "Miami, FL", payMin: 16, payMax: 22, status: "active", postedDate: "2026-02-20" },
  { id: 2, company: "BDS", title: "Retail Merchandiser", location: "Dallas, TX", payMin: 14, payMax: 18, status: "active", postedDate: "2026-02-18" },
  { id: 3, company: "MarketSource", title: "Sales Specialist", location: "Chicago, IL", payMin: 18, payMax: 25, status: "stale", postedDate: "2026-02-10" },
  { id: 4, company: "T-ROC", title: "Field Marketing Rep", location: "Atlanta, GA", payMin: 15, payMax: 20, status: "active", postedDate: "2026-02-22" },
  { id: 5, company: "OSL", title: "Wireless Sales Rep", location: "Toronto, ON", payMin: 17, payMax: 23, status: "closed", postedDate: "2026-01-28" },
  { id: 6, company: "2020 Companies", title: "Demo Specialist", location: "Seattle, WA", payMin: 16, payMax: 21, status: "active", postedDate: "2026-02-24" },
  { id: 7, company: "BDS", title: "Account Manager", location: "New York, NY", payMin: 22, payMax: 30, status: "active", postedDate: "2026-02-21" },
  { id: 8, company: "MarketSource", title: "Tech Consultant", location: "San Jose, CA", payMin: 20, payMax: 28, status: "stale", postedDate: "2026-02-05" },
  { id: 9, company: "T-ROC", title: "Event Coordinator", location: "Orlando, FL", payMin: 15, payMax: 19, status: "active", postedDate: "2026-02-23" },
  { id: 10, company: "OSL", title: "Store Lead", location: "Vancouver, BC", payMin: 19, payMax: 26, status: "active", postedDate: "2026-02-19" },
];

const STATUS_COLORS: Record<Posting["status"], { bg: string; text: string }> = {
  active: { bg: "#E6F5F3", text: "#1B998B" },
  stale: { bg: "#FFF3E0", text: "#DCB256" },
  closed: { bg: "#FDECEA", text: "#8C2C23" },
};

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const tableContainerStyle: React.CSSProperties = {
  fontFamily: "var(--font-body)",
  fontSize: 13,
  border: "1px solid #E8E8E4",
  borderRadius: 6,
  overflow: "hidden",
};

function StatusBadge({ status }: { status: Posting["status"] }) {
  const { bg, text } = STATUS_COLORS[status];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        backgroundColor: bg,
        color: text,
        textTransform: "capitalize",
      }}
    >
      {status}
    </span>
  );
}

function PayRange({ min, max }: { min: number; max: number }) {
  return (
    <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
      ${min}–${max}/hr
    </span>
  );
}

// ---------------------------------------------------------------------------
// Variant 1: Native HTML table
// ---------------------------------------------------------------------------

function NativeTable() {
  const [sortCol, setSortCol] = useState<keyof Posting>("postedDate");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    return [...TABLE_DATA].sort((a, b) => {
      const av = a[sortCol];
      const bv = b[sortCol];
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [sortCol, sortDir]);

  const handleSort = (col: keyof Posting) => {
    if (col === sortCol) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortCol(col); setSortDir("asc"); }
  };

  const thStyle: React.CSSProperties = {
    padding: "8px 12px",
    textAlign: "left",
    fontWeight: 600,
    fontSize: 11,
    color: "#4F5D75",
    borderBottom: "2px solid #E8E8E4",
    cursor: "pointer",
    userSelect: "none",
    whiteSpace: "nowrap",
  };

  const tdStyle: React.CSSProperties = {
    padding: "6px 12px",
    borderBottom: "1px solid #E8E8E4",
    color: "#2D3142",
  };

  const arrow = (col: keyof Posting) => (sortCol === col ? (sortDir === "asc" ? " ↑" : " ↓") : "");

  return (
    <div style={{ ...tableContainerStyle, maxHeight: 320, overflowY: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-body)", fontSize: 13 }}>
        <thead style={{ backgroundColor: "#FAFAF7", position: "sticky", top: 0 }}>
          <tr>
            <th style={thStyle} onClick={() => handleSort("company")}>Company{arrow("company")}</th>
            <th style={thStyle} onClick={() => handleSort("title")}>Title{arrow("title")}</th>
            <th style={thStyle} onClick={() => handleSort("location")}>Location{arrow("location")}</th>
            <th style={thStyle} onClick={() => handleSort("payMin")}>Pay{arrow("payMin")}</th>
            <th style={thStyle} onClick={() => handleSort("status")}>Status{arrow("status")}</th>
            <th style={thStyle} onClick={() => handleSort("postedDate")}>Posted{arrow("postedDate")}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr key={row.id} style={{ transition: "background-color 100ms" }} onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#FAFAF7")} onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "")}>
              <td style={{ ...tdStyle, fontWeight: 500 }}>{row.company}</td>
              <td style={tdStyle}>{row.title}</td>
              <td style={tdStyle}>{row.location}</td>
              <td style={tdStyle}><PayRange min={row.payMin} max={row.payMax} /></td>
              <td style={tdStyle}><StatusBadge status={row.status} /></td>
              <td style={{ ...tdStyle, fontFamily: "var(--font-mono)", fontSize: 12 }}>{row.postedDate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 2: AG Grid
// ---------------------------------------------------------------------------

function AGGridTable() {
  const colDefs = useMemo<ColDef<Posting>[]>(() => [
    { field: "company", headerName: "Company", flex: 1, minWidth: 100 },
    { field: "title", headerName: "Title", flex: 1.5, minWidth: 140 },
    { field: "location", headerName: "Location", flex: 1, minWidth: 110 },
    {
      headerName: "Pay",
      flex: 0.8,
      minWidth: 100,
      valueGetter: (p) => p.data ? `$${p.data.payMin}–$${p.data.payMax}/hr` : "",
      comparator: (_, __, a, b) => (a.data?.payMin ?? 0) - (b.data?.payMin ?? 0),
    },
    {
      field: "status",
      headerName: "Status",
      flex: 0.6,
      minWidth: 80,
      cellRenderer: (p: ICellRendererParams<Posting>) => {
        if (!p.data) return null;
        return <StatusBadge status={p.data.status} />;
      },
    },
    { field: "postedDate", headerName: "Posted", flex: 0.8, minWidth: 100, sort: "desc" },
  ], []);

  return (
    <div style={{ height: 320, fontFamily: "var(--font-body)" }}>
      <AgGridReact<Posting>
        rowData={TABLE_DATA}
        columnDefs={colDefs}
        defaultColDef={{ sortable: true, resizable: true }}
        animateRows
        suppressCellFocus
        headerHeight={36}
        rowHeight={34}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant 3: TanStack Table
// ---------------------------------------------------------------------------

function TanStackTable() {
  const [sorting, setSorting] = useState<SortingState>([{ id: "postedDate", desc: true }]);
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<Posting>[]>(() => [
    { accessorKey: "company", header: "Company", cell: (info) => <span style={{ fontWeight: 500 }}>{info.getValue<string>()}</span> },
    { accessorKey: "title", header: "Title" },
    { accessorKey: "location", header: "Location" },
    {
      id: "pay",
      header: "Pay",
      accessorFn: (row) => row.payMin,
      cell: (info) => <PayRange min={info.row.original.payMin} max={info.row.original.payMax} />,
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: (info) => <StatusBadge status={info.getValue<Posting["status"]>()} />,
    },
    {
      accessorKey: "postedDate",
      header: "Posted",
      cell: (info) => <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{info.getValue<string>()}</span>,
    },
  ], []);

  const table = useReactTable({
    data: TABLE_DATA,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  });

  const thStyle: React.CSSProperties = {
    padding: "8px 12px",
    textAlign: "left",
    fontWeight: 600,
    fontSize: 11,
    color: "#4F5D75",
    borderBottom: "2px solid #E8E8E4",
    cursor: "pointer",
    userSelect: "none",
    whiteSpace: "nowrap",
  };

  const tdStyle: React.CSSProperties = {
    padding: "6px 12px",
    borderBottom: "1px solid #E8E8E4",
    color: "#2D3142",
  };

  return (
    <div>
      <input
        value={globalFilter}
        onChange={(e) => setGlobalFilter(e.target.value)}
        placeholder="Search all columns…"
        style={{
          width: "100%",
          padding: "6px 10px",
          marginBottom: 8,
          border: "1px solid #BFC0C0",
          borderRadius: 4,
          fontFamily: "var(--font-body)",
          fontSize: 12,
          color: "#2D3142",
          outline: "none",
        }}
      />
      <div style={{ ...tableContainerStyle, maxHeight: 290, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-body)", fontSize: 13 }}>
          <thead style={{ backgroundColor: "#FAFAF7", position: "sticky", top: 0 }}>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id} style={thStyle} onClick={h.column.getToggleSortingHandler()}>
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {{ asc: " ↑", desc: " ↓" }[h.column.getIsSorted() as string] ?? ""}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} style={{ transition: "background-color 100ms" }} onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#FAFAF7")} onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "")}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} style={tdStyle}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variant definitions
// ---------------------------------------------------------------------------

export const tableVariants: Variant[] = [
  {
    id: "native-table",
    name: "Native HTML",
    library: "vanilla <table>",
    render: () => <NativeTable />,
    scorecard: {
      bundleKb: "0",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 0,
      notes:
        "Zero dependency. Full design token control. Sorting/filtering/pagination must be manually implemented. Best for simple, static tables under 100 rows.",
    },
  },
  {
    id: "ag-grid-table",
    name: "AG Grid",
    library: "ag-grid-react",
    render: () => <AGGridTable />,
    scorecard: {
      bundleKb: "~300",
      tokenCompliance: "partial",
      a11y: "built-in",
      propsNeeded: 7,
      notes:
        "Enterprise-grade grid engine. Built-in sorting, filtering, column resize, virtualization for 100K+ rows. Largest bundle but most features. Free community edition covers most needs. Custom theming via CSS variables.",
    },
  },
  {
    id: "tanstack-table",
    name: "TanStack Table",
    library: "@tanstack/react-table",
    render: () => <TanStackTable />,
    scorecard: {
      bundleKb: "~15",
      tokenCompliance: "full",
      a11y: "manual",
      propsNeeded: 10,
      notes:
        "Headless — no UI, just table logic (sorting, filtering, pagination, grouping). You bring your own markup and styles. Smallest bundle for the feature set. Global search built-in. Ideal when full design token control matters.",
    },
  },
];
