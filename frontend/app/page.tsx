import { ControlTower } from "@/components/control-tower";
import { OpportunityEngine } from "@/components/opportunity-engine";
import { RegionalAnalytics } from "@/components/regional-analytics";
import { RegulationLens } from "@/components/regulation-lens";
import { SystemStatus } from "@/components/system-status";

const foundations = [
  {
    eyebrow: "01 / Trust",
    title: "Data Reliability Control Tower",
    description: "Pantau freshness, kontrak, lineage, dan insiden sebelum data dipublikasikan.",
  },
  {
    eyebrow: "02 / Compare",
    title: "Regional Opportunity Engine",
    description: "Bandingkan provinsi dengan skor yang transparan, dapat diuji, dan sensitif konteks.",
  },
  {
    eyebrow: "03 / Understand",
    title: "RegulasiLens ID",
    description: "Telusuri regulasi berbasis versi dengan jawaban yang selalu kembali ke sumber.",
  },
];

export default function Home() {
  return (
    <main>
      <section className="hero">
        <nav aria-label="Navigasi utama">
          <a className="brand" href="#top" aria-label="NusaIntel beranda">
            <span className="brand-mark">NI</span>
            <span>NusaIntel</span>
          </a>
          <div className="nav-links">
            <a href="#control-tower">Control Tower</a>
            <a href="#opportunity">Opportunity Engine</a>
            <a href="#regional-analytics">Regional Analytics</a>
            <a href="#regulasilens">RegulasiLens</a>
            <span className="phase-label">Release 0.6 / Phase 9</span>
          </div>
        </nav>

        <div className="hero-grid" id="top">
          <div>
            <p className="kicker">Evidence-first intelligence for Indonesia</p>
            <h1>Keputusan regional dimulai dari data yang dapat dipercaya.</h1>
            <p className="lede">
              NusaIntel menghubungkan kualitas data, analisis peluang daerah, dan penelusuran
              regulasi dalam satu sistem yang transparan.
            </p>
          </div>
          <SystemStatus />
        </div>
      </section>

      <section className="foundation" aria-labelledby="foundation-title">
        <div className="section-heading">
          <p className="kicker">Product foundation</p>
          <h2 id="foundation-title">Tiga lapisan, satu rantai bukti.</h2>
        </div>
        <div className="card-grid">
          {foundations.map((item) => (
            <article className="product-card" key={item.title}>
              <p className="card-eyebrow">{item.eyebrow}</p>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <ControlTower />

      <OpportunityEngine />

      <RegionalAnalytics />

      <RegulationLens />

      <footer>
        <span>NusaIntel © 2026</span>
        <span>Data publik. Metodologi terbuka.</span>
      </footer>
    </main>
  );
}
