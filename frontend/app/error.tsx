"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("NusaIntel route error", { digest: error.digest, message: error.message });
  }, [error]);

  return (
    <main className="route-state">
      <p className="kicker">Unexpected route error</p>
      <h1>Halaman tidak dapat ditampilkan.</h1>
      <p>Data Anda tidak berubah. Coba muat ulang bagian ini atau kembali ke halaman utama.</p>
      <div>
        <button type="button" onClick={reset}>Coba lagi</button>
        <Link href="/">Kembali ke beranda</Link>
      </div>
    </main>
  );
}
