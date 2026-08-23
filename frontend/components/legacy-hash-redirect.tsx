"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

const legacyRoutes: Record<string, string> = {
  "#control-tower": "/control-tower",
  "#opportunity": "/opportunity",
  "#regional-analytics": "/regional-analytics",
  "#regulasilens": "/regulations",
};

export function LegacyHashRedirect() {
  const router = useRouter();

  useEffect(() => {
    const destination = legacyRoutes[window.location.hash];
    if (destination) router.replace(destination);
  }, [router]);

  return null;
}
