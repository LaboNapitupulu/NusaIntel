import { RegionalDetail } from "@/components/regional-detail";

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
