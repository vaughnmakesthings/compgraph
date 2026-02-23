"use client";

export function Header() {
  return (
    <header
      className="flex h-14 shrink-0 items-center justify-between border-b px-6"
      style={{
        backgroundColor: "var(--color-surface)",
        borderColor: "var(--color-border)",
      }}
    >
      <span
        className="text-lg font-semibold tracking-tight"
        style={{
          fontFamily: "var(--font-display)",
          color: "var(--color-foreground)",
        }}
      >
        CompGraph
      </span>

      <div className="flex items-center gap-2">
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: "var(--color-success)" }}
          aria-hidden="true"
        />
        <span
          className="text-xs"
          style={{ color: "var(--color-muted-foreground)" }}
        >
          API connected
        </span>
      </div>
    </header>
  );
}
