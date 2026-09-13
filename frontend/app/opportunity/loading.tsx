import { WorkspaceSkeleton } from "@/components/workspace-ui";

export default function OpportunityLoading() {
  return (
    <div className="module-page" id="main-content">
      <div className="opportunity-shell">
        <WorkspaceSkeleton label="Memuat Peluang Regional" />
      </div>
    </div>
  );
}
