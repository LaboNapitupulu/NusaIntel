import Link from "next/link";

import { DataScene } from "@/components/data-scene";
import { SystemStatus } from "@/components/system-status";

const products = [
  {
    number: "01",
    eyebrow: "Kualitas",
    title: "Pusat Kualitas Data",
    description: "Lihat data mana yang siap digunakan dan mana yang masih perlu diperiksa.",
    href: "/control-tower",
    metric: "21 sumber data",
    tone: "teal",
  },
  {
    number: "02",
    eyebrow: "Bandingkan",
    title: "Peluang Regional",
    description: "Bandingkan provinsi berdasarkan prioritas dan indikator pilihan Anda.",
    href: "/opportunity",
    metric: "38 provinsi",
    tone: "coral",
  },
  {
    number: "03",
    eyebrow: "Temukan",
    title: "Analisis Regional",
    description: "Temukan wilayah dengan kondisi serupa dan pahami faktor pembandingnya.",
    href: "/regional-analytics",
    metric: "Analisis spasial",
    tone: "gold",
  },
  {
    number: "04",
    eyebrow: "Pahami",
    title: "RegulasiLens ID",
    description: "Ajukan pertanyaan tentang regulasi dan periksa kutipan dari dokumen resminya.",
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
          <p className="kicker">Wawasan publik untuk Indonesia</p>
          <h1 id="home-title">Dari data publik menjadi keputusan yang bisa dibuktikan.</h1>
          <p className="lede">
            Pilih kebutuhan Anda, bandingkan informasi, lalu periksa sumbernya dalam alur yang
            ringkas dan mudah dipahami.
          </p>
          <div className="landing-actions">
            <Link className="landing-primary" href="/control-tower">Periksa kualitas data</Link>
            <Link className="landing-secondary" href="/opportunity">Bandingkan wilayah</Link>
          </div>
          <SystemStatus />
        </div>
        <DataScene />
      </section>

      <section className="module-launchpad" aria-labelledby="modules-title">
        <div className="launchpad-heading">
          <div>
            <p className="kicker">Pilih kebutuhan</p>
            <h2 id="modules-title">Mulai dari pertanyaan Anda.</h2>
          </div>
          <p>
            Setiap halaman dibuat untuk satu kebutuhan, sehingga Anda dapat fokus pada hasil yang
            ingin dipahami tanpa menghadapi tampilan yang terlalu padat.
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
        <span>01 · Amati</span>
        <i aria-hidden="true" />
        <span>02 · Periksa</span>
        <i aria-hidden="true" />
        <span>03 · Bandingkan</span>
        <i aria-hidden="true" />
        <span>04 · Putuskan</span>
      </section>
    </main>
  );
}
