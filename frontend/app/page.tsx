import Link from "next/link";

import { DataScene } from "@/components/data-scene";
import { SystemStatus } from "@/components/system-status";

const products = [
  {
    number: "01",
    eyebrow: "Trust",
    title: "Data Reliability Control Tower",
    description: "Pantau freshness, kontrak, lineage, dan insiden sebelum data dipublikasikan.",
    href: "/control-tower",
    metric: "21 dataset",
    tone: "teal",
  },
  {
    number: "02",
    eyebrow: "Compare",
    title: "Regional Opportunity Engine",
    description: "Bangun ranking provinsi dengan bobot, coverage, dan asumsi yang dapat diaudit.",
    href: "/opportunity",
    metric: "38 provinsi",
    tone: "coral",
  },
  {
    number: "03",
    eyebrow: "Discover",
    title: "Regional Analytics",
    description: "Temukan wilayah serupa, cluster tervalidasi, dan bukti pembentuk profilnya.",
    href: "/regional-analytics",
    metric: "Analisis spasial",
    tone: "gold",
  },
  {
    number: "04",
    eyebrow: "Understand",
    title: "RegulasiLens ID",
    description: "Telusuri regulasi berbasis versi dengan jawaban yang selalu kembali ke sumber.",
    href: "/regulations",
    metric: "3 dokumen resmi",
    tone: "mint",
  },
];

export default function Home() {
  return (
    <main className="home-page">
      <section className="landing-hero" aria-labelledby="home-title">
        <div className="landing-copy">
          <p className="kicker">Evidence-first intelligence for Indonesia</p>
          <h1 id="home-title">Dari data publik menjadi keputusan yang bisa dibuktikan.</h1>
          <p className="lede">
            Empat ruang kerja, satu rantai bukti. Pilih modul yang Anda perlukan tanpa harus
            menelusuri satu halaman yang panjang.
          </p>
          <div className="landing-actions">
            <Link className="landing-primary" href="/control-tower">Mulai dari kualitas data</Link>
            <Link className="landing-secondary" href="/opportunity">Buka opportunity engine</Link>
          </div>
          <SystemStatus />
        </div>
        <DataScene />
      </section>

      <section className="module-launchpad" aria-labelledby="modules-title">
        <div className="launchpad-heading">
          <div>
            <p className="kicker">Workspace</p>
            <h2 id="modules-title">Satu tujuan per halaman.</h2>
          </div>
          <p>
            Navigasi kini mempertahankan konteks setiap alat, sementara halaman beranda berfungsi
            sebagai pintu masuk—bukan tumpukan seluruh dashboard.
          </p>
        </div>

        <div className="module-card-grid">
          {products.map((product) => (
            <Link
              className="module-card"
              data-tone={product.tone}
              data-tilt
              data-reveal
              href={product.href}
              key={product.href}
            >
              <span className="module-number">{product.number}</span>
              <span className="module-card-layer" aria-hidden="true" />
              <span className="module-card-content">
                <span className="card-eyebrow">{product.eyebrow}</span>
                <strong>{product.title}</strong>
                <span>{product.description}</span>
                <span className="module-card-footer">
                  <small>{product.metric}</small>
                  <b aria-hidden="true">↗</b>
                </span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="evidence-strip" aria-label="Alur kerja NusaIntel">
        <span>01 · Observe</span>
        <i aria-hidden="true" />
        <span>02 · Validate</span>
        <i aria-hidden="true" />
        <span>03 · Compare</span>
        <i aria-hidden="true" />
        <span>04 · Decide</span>
      </section>
    </main>
  );
}
