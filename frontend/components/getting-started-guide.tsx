"use client";

import { useEffect, useState } from "react";
import { readPreference, writePreference } from "./preferences";

const STORAGE_KEY = "nusa-intel-onboarding-complete";

export function GettingStartedGuide() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    let active = true;
    queueMicrotask(() => { if (active) setVisible(readPreference(STORAGE_KEY) !== "true"); });
    return () => { active = false; };
  }, []);
  if (!visible) return null;
  return (
    <aside className="getting-started" aria-labelledby="getting-started-title">
      <div><h2 id="getting-started-title">Sebelum membandingkan data</h2><p>Gunakan periode yang sama, periksa kelengkapan sumber, dan baca batasan hasil. Peringkat wilayah mengikuti indikator serta bobot yang Anda pilih.</p></div>
      <button type="button" className="secondary-button" onClick={() => { writePreference(STORAGE_KEY, "true"); setVisible(false); }}>Tutup panduan</button>
    </aside>
  );
}
