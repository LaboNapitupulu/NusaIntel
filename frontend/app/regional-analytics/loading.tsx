import { WorkspaceSkeleton } from "@/components/workspace-ui";

export default function RegionalAnalyticsLoading() {
  return (
    <div className="module-page" id="main-content">
      <div className="analytics-shell">
        <WorkspaceSkeleton label="Memuat Analisis Regional" />
      </div>
    </div>
  );
}
