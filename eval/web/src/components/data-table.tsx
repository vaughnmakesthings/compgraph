import { useState, useMemo } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  label: string;
  align?: "left" | "right" | "center";
  width?: string;
  mono?: boolean;
  sortable?: boolean;
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  ariaLabel: string;
  rowKey?: (row: T, index: number) => React.Key;
}

export function DataTable<T extends object>({
  columns,
  data,
  ariaLabel,
  rowKey,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey];
      const bVal = (b as Record<string, unknown>)[sortKey];
      const aStr = String(aVal ?? "");
      const bStr = String(bVal ?? "");
      const aNum = parseFloat(aStr.replace(/[^0-9.-]/g, ""));
      const bNum = parseFloat(bStr.replace(/[^0-9.-]/g, ""));
      const cmp =
        isNaN(aNum) || isNaN(bNum)
          ? aStr.localeCompare(bStr)
          : aNum - bNum;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full" aria-label={ariaLabel}>
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn(
                  "px-2 pb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/50",
                  col.align === "right" && "text-right",
                  col.align === "center" && "text-center",
                  col.align !== "right" && col.align !== "center" && "text-left",
                  col.width,
                )}
              >
                {col.sortable ? (
                  <button
                    type="button"
                    onClick={() => handleSort(col.key)}
                    className={cn(
                      "flex items-center gap-0.5 hover:text-foreground transition-colors duration-150",
                      col.align === "right" && "justify-end w-full",
                      col.align === "center" && "justify-center w-full",
                    )}
                  >
                    {col.label}
                    {sortKey === col.key ? (
                      sortDir === "asc" ? (
                        <ChevronUp className="size-3" />
                      ) : (
                        <ChevronDown className="size-3" />
                      )
                    ) : (
                      <ChevronsUpDown className="size-3 opacity-40" />
                    )}
                  </button>
                ) : (
                  col.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, i) => (
            <tr
              key={rowKey ? rowKey(row, i) : i}
              className="border-b border-border/50 transition-colors duration-100 last:border-0 hover:bg-muted/30"
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(
                    "px-2 py-2.5 text-[13px]",
                    col.align === "right" && "text-right",
                    col.align === "center" && "text-center",
                    col.mono && "font-mono tabular-nums",
                    col.width,
                  )}
                >
                  {col.render
                    ? col.render(row)
                    : ((row as Record<string, unknown>)[col.key] as React.ReactNode)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
