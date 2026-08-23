"use client";

import type { KeyboardEvent, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

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
  function moveFocus(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight" && event.key !== "Home" && event.key !== "End") return;
    const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("[role='tab']"));
    const current = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (current < 0) return;
    event.preventDefault();
    const next = event.key === "Home"
      ? 0
      : event.key === "End"
        ? buttons.length - 1
        : (current + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next]?.focus();
    buttons[next]?.click();
  }

  return (
    <div className="workspace-tabs" role="tablist" aria-label={label} onKeyDown={moveFocus}>
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

export function AnimatedNumber({
  value,
  digits = 0,
  suffix = "",
  initialFrom,
}: {
  value: number;
  digits?: number;
  suffix?: string;
  initialFrom?: number;
}) {
  const [display, setDisplay] = useState(initialFrom ?? value);
  const previous = useRef(initialFrom ?? value);

  useEffect(() => {
    const from = previous.current;
    previous.current = value;
    const reducedMotion = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (from === value || reducedMotion) {
      setDisplay(value);
      return;
    }
    const startedAt = performance.now();
    const duration = 680;
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(from + (value - from) * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return (
    <span className="animated-number" aria-label={`${value}${suffix}`}>
      {new Intl.NumberFormat("id-ID", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(display)}{suffix}
    </span>
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
