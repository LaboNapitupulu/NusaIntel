import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  it("keeps its label visible and persists the selected theme", async () => {
    render(<SiteHeader />);

    const toggle = screen.getByRole("button", { name: "Tema gelap" });
    expect(toggle).toHaveTextContent("Terang");
    await waitFor(() => expect(toggle).toHaveAttribute("aria-pressed", "false"));

    fireEvent.click(toggle);

    expect(document.documentElement.dataset.theme).toBe("night");
    expect(window.localStorage.getItem("nusa-intel-theme")).toBe("night");
    expect(toggle).toHaveTextContent("Gelap");
    expect(toggle).toHaveAttribute("aria-pressed", "true");
  });
});
