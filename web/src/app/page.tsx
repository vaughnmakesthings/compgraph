export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      <h1
        style={{ fontFamily: "var(--font-display)" }}
        className="text-2xl font-semibold tracking-tight"
      >
        CompGraph
      </h1>
      <p className="mt-2 text-sm" style={{ color: "var(--color-muted-foreground)" }}>
        Competitive intelligence platform
      </p>
    </main>
  );
}
