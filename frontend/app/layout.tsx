import type { Metadata } from "next";
import type { ReactNode } from "react";

import { SiteHeader } from "@/components/site-header";

import "./styles.css";

export const metadata: Metadata = {
  title: "NusaIntel",
  description: "Evidence-first regional intelligence for Indonesia.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="id" data-scroll-behavior="smooth">
      <body>
        <SiteHeader />
        {children}
        <footer className="site-footer">
          <span>NusaIntel © 2026</span>
          <span>Data publik. Metodologi terbuka.</span>
        </footer>
      </body>
    </html>
  );
}
