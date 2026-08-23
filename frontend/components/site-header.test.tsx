import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SiteHeader } from "./site-header";

vi.mock("next/navigation", () => ({
  usePathname: () => "/opportunity",
}));

beforeEach(() => {
  document.documentElement.dataset.theme = "day";
  document.documentElement.classList.remove("theme-transitioning");
  window.localStorage.clear();
});

describe("SiteHeader theme switcher", () => {
  it("keeps its label visible and persists the selected theme", () => {
    render(<SiteHeader />);

    const toggle = screen.getByRole("button", { name: "Ganti tema tampilan" });
    expect(toggle.querySelector(".theme-toggle-label")).toBeInTheDocument();

    fireEvent.click(toggle);

    expect(document.documentElement.dataset.theme).toBe("night");
    expect(window.localStorage.getItem("nusa-intel-theme")).toBe("night");
    expect(screen.getByRole("button", { name: "Ganti tema tampilan" })).toBeInTheDocument();
  });
});
