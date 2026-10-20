import Link from "next/link";
import { GettingStartedGuide } from "@/components/getting-started-guide";
import { SystemStatus } from "@/components/system-status";

const products = [
  { title: "Kualitas data", description: "Periksa keterbaruan, hasil pemeriksaan, dan kendala pada sumber data.", href: "/control-tower", detail: "Katalog dan pemeriksaan" },
  { title: "Perbandingan wilayah", description: "Susun bobot indikator, bandingkan provinsi, dan uji perubahan peringkat.", href: "/opportunity", detail: "Skenario dan peringkat" },
  { title: "Analisis wilayah", description: "Lihat sebaran nilai dan cari provinsi dengan profil indikator yang serupa.", href: "/regional-analytics", detail: "Peta dan kelompok wilayah" },
  { title: "RegulasiLens", description: "Cari jawaban dari koleksi regulasi, baca kutipan, dan bandingkan versi dokumen.", href: "/regulations", detail: "Pertanyaan dan dokumen" },
];

export default function Home() {
  return (
    <main className="home-page" id="main-content">
      <section className="landing-hero" aria-labelledby="home-title">
        <div className="landing-copy">
          <p className="kicker">Data publik Indonesia</p>
          <h1 id="home-title">Pahami wilayah.<br />Periksa sumbernya.</h1>
          <p className="lede">Telusuri kualitas data, bandingkan kondisi provinsi, dan baca regulasi beserta kutipan sumbernya.</p>
        </div>
        <SystemStatus />
      </section>
      <section className="module-launchpad" aria-labelledby="modules-title">
        <div className="launchpad-heading"><h2 id="modules-title">Apa yang ingin Anda periksa?</h2><p>Pilih ruang kerja untuk memulai.</p></div>
        <div className="module-card-grid">
          {products.map((product) => (
            <Link className="module-card" href={product.href} key={product.href}>
              <span className="module-card-content"><strong>{product.title}</strong><span>{product.description}</span></span>
              <span className="module-card-footer">{product.detail}</span>
            </Link>
          ))}
        </div>
      </section>
      <GettingStartedGuide />
    </main>
  );
}
