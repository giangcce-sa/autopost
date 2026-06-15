import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-MOS · Spa Marketing OS",
  description: "AI Marketing Operating System cho Spa",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <nav className="nav">
          <span className="brand">🤖 AI-MOS</span>
          <Link href="/">Tổng quan</Link>
          <Link href="/content">Nội dung</Link>
          <Link href="/leads">Lead</Link>
          <Link href="/ads">Ads</Link>
          <Link href="/goals">Mục tiêu</Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
