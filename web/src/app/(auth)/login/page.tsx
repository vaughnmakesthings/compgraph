import type { Metadata } from "next";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = {
  title: "Sign in — CompGraph",
};

export default function LoginPage() {
  return (
    <>
      {/* Left panel — brand */}
      <div
        style={{
          width: "40%",
          minHeight: "100vh",
          backgroundColor: "var(--color-sidebar, #2D3142)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
            fontSize: "28px",
            fontWeight: 700,
            color: "#FFFFFF",
            letterSpacing: "-0.02em",
          }}
        >
          CompGraph
        </span>
      </div>

      {/* Right panel — form */}
      <div
        style={{
          flex: 1,
          minHeight: "100vh",
          backgroundColor: "var(--color-background, #F4F4F0)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 24px",
        }}
      >
        <div style={{ width: "100%", maxWidth: "380px" }}>
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
                margin: "0 0 20px",
                lineHeight: 1.2,
              }}
            >
              Sign in
            </h1>

            <LoginForm />
          </div>
        </div>
      </div>
    </>
  );
}
