"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const STORAGE_KEY = "nusa-intel-onboarding-complete";

const steps = [
  {
    number: "01",
    title: "Periksa kesiapan data",
    description: "Mulai dari status kualitas agar Anda tahu data mana yang layak digunakan.",
  },
  {
    number: "02",
    title: "Pilih prioritas",
    description: "Gunakan preset atau atur indikator dan bobot sesuai pertanyaan Anda.",
  },
  {
    number: "03",
    title: "Periksa alasan dan sumber",
    description: "Baca kontribusi, keterbatasan, serta sumber resmi sebelum menyimpulkan.",
  },
];

export function GettingStartedGuide() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setVisible(window.localStorage.getItem(STORAGE_KEY) !== "true");
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  function dismiss() {
    window.localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <section className="getting-started" aria-labelledby="getting-started-title" data-reveal>
      <div className="getting-started-heading">
        <div>
          <p className="kicker">Panduan singkat</p>
          <h2 id="getting-started-title">Tiga langkah untuk membaca hasil dengan percaya diri.</h2>
        </div>
        <button type="button" className="secondary-button" onClick={dismiss}>
          Lewati panduan
        </button>
      </div>
      <ol>
        {steps.map((step) => (
          <li key={step.number}>
            <span>{step.number}</span>
            <strong>{step.title}</strong>
            <p>{step.description}</p>
          </li>
        ))}
      </ol>
      <div className="getting-started-actions">
        <Link href="/control-tower" onClick={dismiss}>Mulai periksa data</Link>
        <Link href="/opportunity" onClick={dismiss}>Coba preset skenario</Link>
      </div>
    </section>
  );
}
