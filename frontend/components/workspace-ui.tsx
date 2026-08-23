import type { ReactNode } from "react";

export interface WorkspaceTab<T extends string> {
  id: T;
  label: string;
  count?: number;
}

export function WorkspaceTabs<T extends string>({
  label,
  tabs,
  active,
  onChange,
}: {
  label: string;
  tabs: WorkspaceTab<T>[];
  active: T;
  onChange: (tab: T) => void;
}) {
  return (
    <div className="workspace-tabs" role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <button
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          tabIndex={active === tab.id ? 0 : -1}
          key={tab.id}
          onClick={() => onChange(tab.id)}
        >
          <span>{tab.label}</span>
          {typeof tab.count === "number" && <strong>{tab.count}</strong>}
        </button>
      ))}
    </div>
  );
}

export function WorkspaceToast({
  message,
  tone = "info",
  onDismiss,
}: {
  message: string | null;
  tone?: "info" | "success" | "error";
  onDismiss: () => void;
}) {
  if (!message) return null;
  return (
    <div className="workspace-toast" data-tone={tone} role="status">
      <span>{message}</span>
      <button type="button" onClick={onDismiss} aria-label="Tutup notifikasi">×</button>
    </div>
  );
}

export function WorkspaceSkeleton({ label = "Memuat workspace" }: { label?: string }) {
  return (
    <div className="workspace-skeleton" role="status" aria-label={label}>
      <span />
      <span />
      <span />
      <small>{label}…</small>
    </div>
  );
}

export function EmptyState({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="workspace-empty">
      <span>{eyebrow}</span>
      <strong>{title}</strong>
      <p>{description}</p>
      {action}
    </div>
  );
}
