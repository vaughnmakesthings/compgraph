interface LoadingCardProps {
  message?: string;
}

export function LoadingCard({ message = "Loading\u2026" }: LoadingCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-10 text-center shadow-sm">
      <p className="animate-pulse text-[13px] text-muted-foreground">{message}</p>
    </div>
  );
}
