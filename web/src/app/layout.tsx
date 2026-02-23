import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/layout";

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
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
