import { WorkspaceSkeleton } from "@/components/workspace-ui";

export default function ControlTowerLoading() {
  return (
    <main className="module-page" id="main-content">
      <div className="control-tower">
        <WorkspaceSkeleton label="Memuat Pusat Kualitas Data" />
      </div>
    </main>
  );
}
