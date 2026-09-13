import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Inter, DM_Serif_Display } from "next/font/google";

import { SiteHeader } from "@/components/site-header";
import { MotionOrchestrator } from "@/components/motion-orchestrator";

import "./styles.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  weight: ["300", "400", "500", "600", "700"],
});

const dmSerifDisplay = DM_Serif_Display({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
  weight: ["400"],
  style: ["normal", "italic"],
});

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f3f0e8" },
    { media: "(prefers-color-scheme: dark)", color: "#0d2929" },
  ],
};

export const metadata: Metadata = {
  title: {
    default: "NusaIntel — Data Publik Indonesia",
    template: "%s · NusaIntel",
  },
  description:
    "Platform wawasan data publik Indonesia. Bandingkan 38 provinsi, periksa kualitas data, dan pahami regulasi dengan bukti dari sumber resmi.",
  keywords: ["data publik", "Indonesia", "analisis wilayah", "provinsi", "regulasi", "open data"],
  authors: [{ name: "Tim NusaIntel" }],
  creator: "NusaIntel",
  metadataBase: new URL("https://nusa-intel.vercel.app"),
  openGraph: {
    type: "website",
    locale: "id_ID",
    siteName: "NusaIntel",
    title: "NusaIntel — Data Publik Indonesia",
    description: "Dari data publik menjadi keputusan yang bisa dibuktikan.",
  },
  twitter: {
    card: "summary_large_image",
    title: "NusaIntel — Data Publik Indonesia",
    description: "Dari data publik menjadi keputusan yang bisa dibuktikan.",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="id"
      data-scroll-behavior="smooth"
      className={`${inter.variable} ${dmSerifDisplay.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{document.documentElement.dataset.theme=localStorage.getItem('nusa-intel-theme')||'day'}catch(e){}",
          }}
        />
      </head>
      <body>
        <MotionOrchestrator />
        <SiteHeader />
        <a href="#main-content" className="skip-link">
          Lewati ke konten utama
        </a>
        {children}
        <footer className="site-footer">
          <span>NusaIntel © 2026</span>
          <span>Data publik yang mudah dipahami.</span>
          <a
            href="https://github.com/LaboNapitupulu/NusaIntel/issues/new?labels=feedback&title=Feedback%3A%20"
            target="_blank"
            rel="noreferrer"
          >
            Berikan masukan ↗
          </a>
        </footer>
      </body>
    </html>
  );
}
