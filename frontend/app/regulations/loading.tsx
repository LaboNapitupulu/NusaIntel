import { WorkspaceSkeleton } from "@/components/workspace-ui";

export default function RegulationsLoading() {
  return (
    <div className="module-page" id="main-content">
      <div className="regulation-shell">
        <WorkspaceSkeleton label="Memuat RegulasiLens ID" />
      </div>
    </div>
  );
}
