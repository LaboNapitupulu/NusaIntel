import type { Metadata } from "next";

import { RegionalAnalytics } from "@/components/regional-analytics";

export const metadata: Metadata = {
  title: "Regional Analytics · NusaIntel",
  description: "Analisis kemiripan, cluster, dan profil indikator antarprovinsi.",
};

export default function RegionalAnalyticsPage() {
  return <main className="module-page module-page-dark"><RegionalAnalytics /></main>;
}
