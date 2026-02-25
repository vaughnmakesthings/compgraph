import type { Metadata } from "next";
import Link from "next/link";
import { LockClosedIcon } from "@heroicons/react/24/solid";

export const metadata: Metadata = {
  title: "Access Restricted — CompGraph",
};

export default function UnauthorizedPage() {
  return (
    <>
      {/* Minimal header — wordmark only, no nav */}
      <header
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: "56px",
          display: "flex",
          alignItems: "center",
          padding: "0 24px",
          backgroundColor: "var(--color-surface, #FFFFFF)",
          borderBottom: "1px solid var(--color-border, #BFC0C0)",
          zIndex: 10,
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
            fontSize: "18px",
            fontWeight: 700,
            color: "var(--color-foreground, #2D3142)",
            letterSpacing: "-0.02em",
          }}
        >
          CompGraph
        </span>
      </header>

      {/* Full-page centered content */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "96px 24px 48px", // top padding accounts for fixed header
          backgroundColor: "var(--color-background, #F4F4F0)",
          minHeight: "100vh",
        }}
      >
        <div
          style={{
            textAlign: "center",
            maxWidth: "420px",
            width: "100%",
          }}
        >
          {/* Lock icon */}
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "50%",
              backgroundColor: "var(--color-muted, #E8E8E4)",
              border: "1px solid var(--color-border, #BFC0C0)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 24px",
            }}
          >
            <LockClosedIcon
              style={{
                width: 24,
                height: 24,
                color: "var(--color-muted-foreground, #4F5D75)",
              }}
            />
          </div>

          {/* 403 badge */}
          <div
            style={{
              display: "inline-block",
              backgroundColor: "var(--color-surface, #FFFFFF)",
              border: "1px solid var(--color-border, #BFC0C0)",
              borderRadius: "var(--radius-lg, 8px)",
              boxShadow: "var(--shadow-sm, 0 1px 2px 0 rgb(0 0 0 / 0.05))",
              padding: "12px 32px",
              marginBottom: "24px",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-mono, 'JetBrains Mono Variable', monospace)",
                fontSize: "48px",
                fontWeight: 700,
                color: "var(--color-foreground, #2D3142)",
                lineHeight: 1,
              }}
            >
              403
            </div>
            <div
              style={{
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "11px",
                color: "var(--color-muted-foreground, #4F5D75)",
                textTransform: "uppercase",
                letterSpacing: "0.07em",
                marginTop: "6px",
              }}
            >
              Access Restricted
            </div>
          </div>

          {/* Heading */}
          <h1
            style={{
              fontFamily: "var(--font-display, 'Sora Variable', sans-serif)",
              fontSize: "20px",
              fontWeight: 600,
              color: "var(--color-foreground, #2D3142)",
              lineHeight: 1.3,
              margin: "0 0 12px",
            }}
          >
            You don&apos;t have permission to view this page
          </h1>

          {/* Description */}
          <p
            style={{
              fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
              fontSize: "14px",
              color: "var(--color-muted-foreground, #4F5D75)",
              lineHeight: 1.65,
              margin: "0 0 28px",
            }}
          >
            This is a private, invite-only platform.
          </p>

          {/* Actions */}
          <div
            style={{
              display: "flex",
              gap: "12px",
              justifyContent: "center",
              flexWrap: "wrap",
            }}
          >
            <Link
              href="/login"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "10px 22px",
                backgroundColor: "var(--color-primary, #EF8354)",
                color: "#FFFFFF",
                borderRadius: "var(--radius-md, 6px)",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "14px",
                fontWeight: 500,
                textDecoration: "none",
                transition: "opacity 150ms",
              }}
            >
              ← Back to Login
            </Link>

            <a
              href="mailto:admin@compgraph.io"
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "10px 22px",
                backgroundColor: "transparent",
                color: "var(--color-muted-foreground, #4F5D75)",
                border: "1px solid var(--color-border, #BFC0C0)",
                borderRadius: "var(--radius-md, 6px)",
                fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
                fontSize: "14px",
                fontWeight: 400,
                textDecoration: "none",
                transition: "background-color 150ms",
              }}
            >
              Contact Admin
            </a>
          </div>
        </div>
      </div>
    </>
  );
}
