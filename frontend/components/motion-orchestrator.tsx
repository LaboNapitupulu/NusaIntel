"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

export function MotionOrchestrator() {
  const pathname = usePathname();

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.routeMotion = "entering";
    const frame = requestAnimationFrame(() => {
      root.dataset.routeMotion = "settled";
    });
    return () => cancelAnimationFrame(frame);
  }, [pathname]);

  useEffect(() => {
    const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!finePointer.matches || reducedMotion.matches) return;

    let frame = 0;
    let pointerX = 0;
    let pointerY = 0;
    const updateScene = () => {
      document.documentElement.style.setProperty("--pointer-x", pointerX.toFixed(3));
      document.documentElement.style.setProperty("--pointer-y", pointerY.toFixed(3));
      frame = 0;
    };
    const onPointerMove = (event: PointerEvent) => {
      pointerX = (event.clientX / window.innerWidth - 0.5) * 2;
      pointerY = (event.clientY / window.innerHeight - 0.5) * 2;
      if (!frame) frame = requestAnimationFrame(updateScene);

      const surface = (event.target as Element | null)?.closest<HTMLElement>("[data-tilt]");
      if (!surface) return;
      const bounds = surface.getBoundingClientRect();
      const localX = (event.clientX - bounds.left) / bounds.width - 0.5;
      const localY = (event.clientY - bounds.top) / bounds.height - 0.5;
      surface.style.setProperty("--tilt-x", `${(-localY * 7).toFixed(2)}deg`);
      surface.style.setProperty("--tilt-y", `${(localX * 8).toFixed(2)}deg`);
      surface.style.setProperty("--glow-x", `${((localX + 0.5) * 100).toFixed(1)}%`);
      surface.style.setProperty("--glow-y", `${((localY + 0.5) * 100).toFixed(1)}%`);
    };
    const resetSurface = (event: PointerEvent) => {
      const surface = (event.target as Element | null)?.closest<HTMLElement>("[data-tilt]");
      if (!surface || (event.relatedTarget instanceof Node && surface.contains(event.relatedTarget))) return;
      surface.style.removeProperty("--tilt-x");
      surface.style.removeProperty("--tilt-y");
      surface.style.removeProperty("--glow-x");
      surface.style.removeProperty("--glow-y");
    };

    document.addEventListener("pointermove", onPointerMove, { passive: true });
    document.addEventListener("pointerout", resetSurface, { passive: true });
    return () => {
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerout", resetSurface);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return null;
}
