import type { Metadata } from "next";

import { RegulationLens } from "@/components/regulation-lens";

export const metadata: Metadata = {
  title: "RegulasiLens · NusaIntel",
  description: "Pahami dan bandingkan regulasi Indonesia melalui kutipan dokumen resmi.",
};

export default function RegulationsPage() {
  return <main className="module-page module-page-dark"><RegulationLens /></main>;
}
