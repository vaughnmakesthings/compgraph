interface ErrorBoxProps {
  message: string;
}

export function ErrorBox({ message }: ErrorBoxProps) {
  return (
    <div className="rounded-lg border border-error/30 bg-error-muted px-4 py-3 text-[13px] text-status-wrong">
      {message}
    </div>
  );
}
