import type { Metadata } from "next";

import { ControlTower } from "@/components/control-tower";

export const metadata: Metadata = {
  title: "Control Tower · NusaIntel",
  description: "Periksa keterbaruan, kualitas, dan kendala pada data NusaIntel.",
};

export default function ControlTowerPage() {
  return <main className="module-page module-page-dark"><ControlTower /></main>;
}
