import Link from "next/link";

export default function NotFound() {
  return (
    <main className="route-state">
      <p className="kicker">404 / Not found</p>
      <h1>Halaman tidak ditemukan.</h1>
      <p>Alamat ini tidak menunjuk ke halaman NusaIntel yang tersedia.</p>
      <Link href="/">Kembali ke beranda</Link>
    </main>
  );
}
