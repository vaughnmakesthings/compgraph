import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CompGraph",
  description: "Competitive intelligence for field marketing agencies",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
