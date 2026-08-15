import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./styles.css";

export const metadata: Metadata = {
  title: "NusaIntel",
  description: "Evidence-first regional intelligence for Indonesia.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="id" data-scroll-behavior="smooth">
      <body>{children}</body>
    </html>
  );
}
