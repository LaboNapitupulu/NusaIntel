import type { Metadata } from "next";

import { RegulationLens } from "@/components/regulation-lens";

export const metadata: Metadata = {
  title: "RegulasiLens · NusaIntel",
  description: "Telusuri dan bandingkan regulasi Indonesia dengan bukti yang dapat dibuka.",
};

export default function RegulationsPage() {
  return <main className="module-page module-page-dark"><RegulationLens /></main>;
}
