import Link from "next/link";

export default function RootNotFound() {
  return (
    <div
      className="flex flex-col items-center justify-center px-4"
      style={{ minHeight: "100vh", backgroundColor: "var(--color-background)" }}
    >
      <p
        className="text-5xl font-bold"
        style={{
          fontFamily: "var(--font-mono)",
          color: "var(--color-silver)",
        }}
      >
        404
      </p>
      <h2
        className="mt-3 text-lg font-semibold"
        style={{
          fontFamily: "var(--font-display)",
          color: "var(--color-jet-black)",
        }}
      >
        Page not found
      </h2>
      <p
        className="mt-1 text-sm"
        style={{
          fontFamily: "var(--font-body)",
          color: "var(--color-blue-slate)",
        }}
      >
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        href="/"
        className="mt-5 rounded px-3 py-1.5 text-sm font-medium transition-opacity hover:opacity-80"
        style={{
          fontFamily: "var(--font-body)",
          backgroundColor: "var(--color-jet-black)",
          color: "#FFFFFF",
          borderRadius: "var(--radius-md)",
        }}
      >
        Back to dashboard
      </Link>
    </div>
  );
}
