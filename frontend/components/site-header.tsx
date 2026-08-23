"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

type Theme = "day" | "night";

type ViewTransitionDocument = Document & {
  startViewTransition?: (callback: () => void) => { finished: Promise<void> };
};

const navigation = [
  { href: "/control-tower", label: "Kualitas Data" },
  { href: "/opportunity", label: "Peluang" },
  { href: "/regional-analytics", label: "Analisis Wilayah" },
  { href: "/regulations", label: "RegulasiLens" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  function toggleTheme() {
    const root = document.documentElement;
    const next: Theme = root.dataset.theme === "night" ? "day" : "night";
    const applyTheme = () => {
      root.dataset.theme = next;
      window.localStorage.setItem("nusa-intel-theme", next);
    };
    const transitionDocument = document as ViewTransitionDocument;

    root.classList.add("theme-transitioning");
    if (transitionDocument.startViewTransition) {
      const transition = transitionDocument.startViewTransition(applyTheme);
      void transition.finished.finally(() => root.classList.remove("theme-transitioning"));
      return;
    }

    applyTheme();
    window.setTimeout(() => root.classList.remove("theme-transitioning"), 480);
  }

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Link className="brand site-brand" href="/" aria-label="NusaIntel beranda">
          <span className="brand-cube" aria-hidden="true">
            <span className="brand-cube-face brand-cube-front">NI</span>
            <span className="brand-cube-face brand-cube-side" />
            <span className="brand-cube-face brand-cube-top" />
          </span>
          <span>NusaIntel</span>
        </Link>

        <button
          className="site-menu-button"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="site-navigation"
          onClick={() => setMenuOpen((current) => !current)}
        >
          <span aria-hidden="true" />
          <span aria-hidden="true" />
          <span className="sr-only">Buka navigasi</span>
        </button>

        <nav
          className="site-nav"
          id="site-navigation"
          aria-label="Navigasi utama"
          data-open={menuOpen}
        >
          {navigation.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </Link>
            );
          })}
          <button
            className="theme-toggle"
            type="button"
            onClick={toggleTheme}
            aria-label="Ganti tema tampilan"
            title="Ganti tema tampilan"
          >
            <span className="theme-toggle-icon" aria-hidden="true">◐</span>
            <span className="theme-toggle-label" aria-hidden="true" />
          </button>
          <span className="phase-label">NusaIntel</span>
        </nav>
      </div>
    </header>
  );
}
