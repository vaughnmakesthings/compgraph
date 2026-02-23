import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, { dot: string; label: string }> = {
  running: { dot: "bg-amber-500 animate-pulse", label: "text-amber-700 dark:text-amber-400" },
  completed: { dot: "bg-status-correct", label: "text-status-correct" },
  failed: { dot: "bg-status-wrong", label: "text-status-wrong" },
  correct: { dot: "bg-status-correct", label: "text-status-correct" },
  wrong: { dot: "bg-status-wrong", label: "text-status-wrong" },
  blank: { dot: "bg-warning", label: "text-warning" },
  replaced: { dot: "bg-status-wrong", label: "text-status-wrong" },
  improved: { dot: "bg-status-improved", label: "text-status-improved" },
  "cant-assess": { dot: "bg-muted-foreground/30", label: "text-muted-foreground" },
  pending: { dot: "bg-muted-foreground/30", label: "text-muted-foreground" },
};

const DISPLAY_LABELS: Record<string, string> = {
  "cant-assess": "Can't Assess",
  blank: "Wrong (blank)",
  replaced: "Wrong (replaced)",
};

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "default";
}

export function StatusBadge({ status, size = "default" }: StatusBadgeProps) {
  const styles = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  const label = DISPLAY_LABELS[status] ?? status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <span className="inline-flex items-center gap-1.5" role="status" aria-label={label}>
      <span
        className={cn(
          "rounded-full",
          size === "sm" ? "size-1.5" : "size-2",
          styles.dot,
        )}
      />
      <span
        className={cn(
          "font-medium capitalize",
          size === "sm" ? "text-[11px]" : "text-[12px]",
          styles.label,
        )}
      >
        {label}
      </span>
    </span>
  );
}
