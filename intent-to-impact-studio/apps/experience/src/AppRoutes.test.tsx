import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("./studio/StudioApp", () => ({
  StudioApp: () => <h1>Live architecture studio</h1>,
}));
vi.mock("./LegacyPreview", () => ({
  LegacyPreview: () => <h1>Historical component viewer</h1>,
}));

afterEach(() => window.history.replaceState({}, "", "/"));

describe("product entry route", () => {
  it("opens the business-first front door by default", () => {
    window.history.replaceState({}, "", "/");
    render(<App />);
    expect(screen.getByRole("heading", { name: "Live architecture studio" })).toBeVisible();
    expect(screen.queryByText("Historical component viewer")).not.toBeInTheDocument();
  });

  it("does not reuse an old scene link as the product's front door", () => {
    window.history.replaceState({}, "", "/?scene=FX-09");
    render(<App />);
    expect(screen.getByRole("heading", { name: "Live architecture studio" })).toBeVisible();
  });

  it.each(["/draft", "/draft/", "/draft?scene=FX-09"])("opens the live studio for retired draft bookmark %s", (url) => {
    window.history.replaceState({}, "", url);
    render(<App />);
    expect(screen.getByRole("heading", { name: "Live architecture studio" })).toBeVisible();
    expect(screen.queryByText("Opening local draft tools...")).not.toBeInTheDocument();
    expect(screen.queryByText("Business-first workbench")).not.toBeInTheDocument();
  });

  it.each(["/?view=legacy-risk&scene=FX-09", "/legacy-risk/?scene=FX-09"])(
    "retains explicit legacy route %s separately", async (url) => {
      window.history.replaceState({}, "", url);
      render(<App />);
      expect(await screen.findByRole("heading", { name: "Historical component viewer" })).toBeVisible();
    },
  );
});
