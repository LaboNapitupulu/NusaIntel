"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { writePreference } from "./preferences";

const navigation = [
  { href: "/control-tower", label: "Kualitas data" },
  { href: "/opportunity", label: "Perbandingan" },
  { href: "/regional-analytics", label: "Analisis wilayah" },
  { href: "/regulations", label: "RegulasiLens" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [night, setNight] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    let active = true;
    queueMicrotask(() => { if (active) setNight(document.documentElement.dataset.theme === "night"); });
    return () => { active = false; };
  }, []);

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === "night" ? "day" : "night";
    document.documentElement.dataset.theme = next;
    writePreference("nusa-intel-theme", next);
    setNight(next === "night");
  }

  return (
    <header className="site-header" onKeyDown={(event) => {
      if (event.key === "Escape" && menuOpen) { setMenuOpen(false); menuButton.current?.focus(); }
    }}>
      <div className="site-header-inner">
        <Link className="site-brand" href="/" aria-label="NusaIntel beranda" onClick={() => setMenuOpen(false)}>NusaIntel</Link>
        <button ref={menuButton} className="site-menu-button" type="button" aria-expanded={menuOpen} aria-controls="site-navigation" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? "Tutup menu" : "Menu"}
        </button>
        <nav className="site-nav" id="site-navigation" aria-label="Navigasi utama" data-open={menuOpen}>
          {navigation.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`) || (item.href === "/regional-analytics" && pathname.startsWith("/regions/"));
            return <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} onClick={() => setMenuOpen(false)}>{item.label}</Link>;
          })}
          <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label="Tema gelap" aria-pressed={night}>
            <span aria-hidden="true">◐</span><span>{night ? "Gelap" : "Terang"}</span>
          </button>
        </nav>
      </div>
    </header>
  );
}
