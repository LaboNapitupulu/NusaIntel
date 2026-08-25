import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { GettingStartedGuide } from "./getting-started-guide";

afterEach(() => {
  window.localStorage.removeItem("nusa-intel-onboarding-complete");
});

describe("GettingStartedGuide", () => {
  it("can be dismissed and remembers the choice locally", async () => {
    const view = render(<GettingStartedGuide />);

    expect(await screen.findByText(/Tiga langkah untuk membaca hasil/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Lewati panduan" }));
    expect(screen.queryByText(/Tiga langkah untuk membaca hasil/)).not.toBeInTheDocument();
    expect(window.localStorage.getItem("nusa-intel-onboarding-complete")).toBe("true");

    view.unmount();
    render(<GettingStartedGuide />);
    await waitFor(() =>
      expect(screen.queryByText(/Tiga langkah untuk membaca hasil/)).not.toBeInTheDocument(),
    );
  });
});
