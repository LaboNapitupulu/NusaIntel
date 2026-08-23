import type { Metadata } from "next";

import { OpportunityEngine } from "@/components/opportunity-engine";

export const metadata: Metadata = {
  title: "Opportunity Engine · NusaIntel",
  description: "Bandingkan peluang regional melalui skenario yang transparan dan dapat diaudit.",
};

export default function OpportunityPage() {
  return <main className="module-page"><OpportunityEngine /></main>;
}
