import type { Metadata } from "next";

import { RegionalAnalytics } from "@/components/regional-analytics";

export const metadata: Metadata = {
  title: "Analisis Wilayah",
  description: "Temukan wilayah dengan kondisi serupa berdasarkan indikator pilihan Anda.",
};

export default function RegionalAnalyticsPage() {
  return <main className="module-page module-page-dark" id="main-content"><RegionalAnalytics /></main>;
}
