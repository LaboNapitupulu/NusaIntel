import type { Metadata } from "next";

import { OpportunityEngine } from "@/components/opportunity-engine";

export const metadata: Metadata = {
  title: "Peluang Regional · NusaIntel",
  description: "Bandingkan provinsi berdasarkan indikator dan prioritas pilihan Anda.",
};

export default function OpportunityPage() {
  return <main className="module-page"><OpportunityEngine /></main>;
}
