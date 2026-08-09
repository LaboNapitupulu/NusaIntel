import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SystemStatus } from "./system-status";

describe("SystemStatus", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a ready state when the backend and database are healthy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: async () => ({
          status: "healthy",
          dependencies: { database: { status: "ready" } },
        }),
      }),
    );

    render(<SystemStatus />);

    expect(await screen.findByText("Semua sistem siap")).toBeInTheDocument();
  });

  it("offers a retry when the backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network unavailable")));

    render(<SystemStatus />);

    await waitFor(() => expect(screen.getByText("Backend tidak tersedia")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Periksa ulang" })).toBeInTheDocument();
  });
});
