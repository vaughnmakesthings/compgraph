import type { Metadata } from "next";
import { AccountSetupForm } from "@/components/auth/account-setup-form";

export const metadata: Metadata = {
  title: "Set up your account — CompGraph",
};

interface SetupPageProps {
  searchParams: Promise<{ email?: string }>;
}

export default async function SetupPage({ searchParams }: SetupPageProps) {
  const { email = "" } = await searchParams;

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
        backgroundColor: "var(--color-background, #F4F4F0)",
      }}
    >
      <div style={{ width: "100%", maxWidth: "440px" }}>
        {/* Wordmark */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginBottom: "28px",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
              fontSize: "26px",
              fontWeight: 700,
              color: "var(--color-foreground, #2D3142)",
              letterSpacing: "-0.02em",
            }}
          >
            CompGraph
          </span>
        </div>

        {/* Card */}
        <div
          style={{
            backgroundColor: "var(--color-surface, #FFFFFF)",
            border: "1px solid var(--color-border, #BFC0C0)",
            borderRadius: "var(--radius-lg, 8px)",
            boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
            padding: "28px 28px 24px",
          }}
        >
          <h1
            style={{
              fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
              fontSize: "20px",
              fontWeight: 600,
              color: "var(--color-foreground, #2D3142)",
              margin: "0 0 6px",
              lineHeight: 1.2,
            }}
          >
            Set up your account
          </h1>
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "13px",
              color: "var(--color-muted-foreground, #4F5D75)",
              margin: "0 0 20px",
              lineHeight: 1.5,
            }}
          >
            You&apos;ll use your email and password to sign in going forward.
          </p>

          <AccountSetupForm email={email} />
        </div>
      </div>
    </div>
  );
}
