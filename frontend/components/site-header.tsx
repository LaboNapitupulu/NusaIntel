"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const navigation = [
  { href: "/control-tower", label: "Control Tower" },
  { href: "/opportunity", label: "Opportunity" },
  { href: "/regional-analytics", label: "Regional" },
  { href: "/regulations", label: "RegulasiLens" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  function toggleTheme() {
    const current = document.documentElement.dataset.theme;
    const next = current === "night" ? "day" : "night";
    document.documentElement.dataset.theme = next;
    window.localStorage.setItem("nusa-intel-theme", next);
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
          <button className="theme-toggle" type="button" onClick={toggleTheme}>
            Ganti tema
          </button>
          <span className="phase-label">Release 0.7</span>
        </nav>
      </div>
    </header>
  );
}
