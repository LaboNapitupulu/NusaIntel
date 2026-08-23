import type { Metadata } from "next";
import type { ReactNode } from "react";

import { SiteHeader } from "@/components/site-header";
import { MotionOrchestrator } from "@/components/motion-orchestrator";

import "./styles.css";

export const metadata: Metadata = {
  title: "NusaIntel",
  description: "Data publik Indonesia yang lebih mudah dipahami dan dibandingkan.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="id" data-scroll-behavior="smooth">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: "try{document.documentElement.dataset.theme=localStorage.getItem('nusa-intel-theme')||'day'}catch(e){}",
          }}
        />
      </head>
      <body>
        <MotionOrchestrator />
        <SiteHeader />
        {children}
        <footer className="site-footer">
          <span>NusaIntel © 2026</span>
          <span>Data publik yang mudah dipahami.</span>
        </footer>
      </body>
    </html>
  );
}
