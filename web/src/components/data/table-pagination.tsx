"use client";

interface TablePaginationProps {
  page: number;
  totalPages: number;
  onFirst: () => void;
  onPrev: () => void;
  onNext: () => void;
  onLast: () => void;
}

export function TablePagination({
  page,
  totalPages,
  onFirst,
  onPrev,
  onNext,
  onLast,
}: TablePaginationProps) {
  const btn =
    "inline-flex items-center justify-center w-8 h-8 rounded border text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const enabled =
    "border-[#BFC0C0] bg-white text-[#2D3142] hover:bg-[#E8E8E4] cursor-pointer";
  const disabled = "border-[#BFC0C0] bg-white text-[#BFC0C0] cursor-not-allowed";

  return (
    <div className="flex items-center justify-between gap-4">
      <span
        style={{
          fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
          fontSize: "13px",
          color: "#4F5D75",
        }}
      >
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-1">
        <button
          type="button"
          onClick={onFirst}
          disabled={page <= 1}
          className={`${btn} ${page <= 1 ? disabled : enabled}`}
          aria-label="First page"
        >
          <span aria-hidden>⏮</span>
        </button>
        <button
          type="button"
          onClick={onPrev}
          disabled={page <= 1}
          className={`${btn} ${page <= 1 ? disabled : enabled}`}
          aria-label="Previous page"
        >
          <span aria-hidden>◀</span>
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={page >= totalPages}
          className={`${btn} ${page >= totalPages ? disabled : enabled}`}
          aria-label="Next page"
        >
          <span aria-hidden>▶</span>
        </button>
        <button
          type="button"
          onClick={onLast}
          disabled={page >= totalPages}
          className={`${btn} ${page >= totalPages ? disabled : enabled}`}
          aria-label="Last page"
        >
          <span aria-hidden>⏭</span>
        </button>
      </div>
    </div>
  );
}
