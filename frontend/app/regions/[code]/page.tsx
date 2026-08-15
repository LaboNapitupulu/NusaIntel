import { RegionalDetail } from "@/components/regional-detail";
import type { Metadata } from "next";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ code: string }>;
}): Promise<Metadata> {
  const { code } = await params;
  return {
    title: `Bukti regional ${code} | NusaIntel`,
    description: `Nilai indikator, sumber, periode, dan versi dataset untuk provinsi ${code}.`,
  };
}

export default async function RegionPage({
  params,
  searchParams,
}: {
  params: Promise<{ code: string }>;
  searchParams: Promise<{ year?: string }>;
}) {
  const [{ code }, query] = await Promise.all([params, searchParams]);
  const requestedYear = Number(query.year ?? 2024);
  const year = Number.isInteger(requestedYear) && requestedYear >= 2000 && requestedYear <= 2100
    ? requestedYear
    : 2024;
  return <RegionalDetail code={code} year={year} />;
}
