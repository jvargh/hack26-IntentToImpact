import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LegacyPreview as App } from "./LegacyPreview";
import { createFixtureTransport, defaultInputs, HISTORICAL_NOTICE, FixtureError } from "./data/fixtureTransport";
import type { FixtureTransport, NavigationResult } from "./data/fixtureTransport";
import { setNarrowLayout } from "./test/setup";

async function ready(id = "FX-09", transport?: FixtureTransport) {
  render(<App initialSceneId={id} transport={transport} />);
  await waitFor(() => expect(screen.getByLabelText("Review scene")).toBeEnabled());
  await screen.findByRole("heading", { level: 1 });
}

describe("historical early review preview", () => {
  it("discloses historical V2, current NSP direction, fixture mode and pending human review", async () => {
    await ready();
    expect(screen.getByText(HISTORICAL_NOTICE)).toBeVisible();
    expect(screen.getByText(/LOCAL-09 requires NSP Enforced with zero external access rules/)).toBeVisible();
    expect(screen.getByText("fixture / ux-mock")).toBeVisible();
    expect(screen.getByText(/GATE-UX01 pending/)).toBeVisible();
    expect(screen.getByText("Demo Identity · local-demo")).toBeVisible();
    expect(document.querySelectorAll('button[data-primary="true"]')).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /switch.*live|approve|materialize/i })).not.toBeInTheDocument();
  });

  it("navigates all seven snapshots using the scene selector", async () => {
    const user = userEvent.setup();
    const transport = createFixtureTransport();
    await ready("FX-01", transport);
    for (const choice of transport.choices) {
      await user.selectOptions(screen.getByLabelText("Review scene"), choice.id);
      const expected = await transport.loadScene(choice.id);
      await screen.findByRole("heading", { level: 1, name: expected.response.operationsRisk.headline });
      await waitFor(() => expect(screen.getByLabelText("Review scene")).toBeEnabled());
      expect(document.querySelectorAll('button[data-primary="true"]')).toHaveLength(1);
    }
  });

  it("passes the exact action ID and supports keyboard activation", async () => {
    const user = userEvent.setup();
    const base = createFixtureTransport();
    const navigate = vi.fn(base.navigate);
    await ready("FX-09", { ...base, navigate });
    const action = screen.getByRole("button", { name: /Review correction example/ });
    action.focus();
    await user.keyboard("{Enter}");
    await screen.findByRole("heading", { level: 1, name: /Correction prepared/ });
    expect(navigate).toHaveBeenCalledWith(expect.objectContaining({ id: "FX-09" }), "review-correction-example");
  });

  it("disables issued actions and selection while opening a snapshot", async () => {
    const user = userEvent.setup();
    const base = createFixtureTransport();
    const next = await base.loadScene("FX-10");
    let release: ((result: NavigationResult) => void) | undefined;
    const navigate = vi.fn(() => new Promise<NavigationResult>((resolve) => { release = resolve; }));
    await ready("FX-09", { ...base, navigate });
    const action = screen.getByRole("button", { name: /Review correction example/ });
    await user.click(action);
    expect(action).toBeDisabled();
    expect(screen.getByLabelText("Review scene")).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("no workflow is running");
    release?.({ kind: "scene", scene: next });
    await screen.findByRole("heading", { level: 1, name: /Correction prepared/ });
  });

  it("keeps pending visibly pending, not restored", async () => {
    await ready("FX-11");
    expect(screen.getByText("Verification pending", { selector: ".status-badge" })).toBeVisible();
    expect(screen.queryByText("Fixture verification only")).not.toBeInTheDocument();
    expect(screen.getByText(/Prepared or materialized files are not runtime verification/)).toBeVisible();
  });

  it("displays unknown, stale and unavailable counts without inventing a success count", async () => {
    const user = userEvent.setup();
    await ready("FX-09:stale-evidence");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("stale");
    expect(screen.getByText("Assurance unknown")).toBeVisible();
    await user.click(screen.getByText("All eight promise states"));
    expect(screen.getByText("Coverage counts are not assessed.")).toBeVisible();
    expect(screen.getByText("stale", { selector: ".status-badge" })).toBeVisible();
    expect(screen.queryByText(/8 \/ 8|7 \/ 8/)).not.toBeInTheDocument();
  });

  it("renders supplied map edges and the equivalent supplied ordered list", async () => {
    const user = userEvent.setup();
    const expected = (await createFixtureTransport().loadScene("FX-09")).response.continuityGraph;
    await ready();
    const map = screen.getByRole("img", { name: "Supplied intent continuity map" });
    for (const edge of expected.edges) {
      expect(map.querySelector(`[data-edge-id="${edge.edgeId}"]`)).toHaveAttribute("data-edge-status", edge.status);
    }
    await user.click(screen.getByRole("button", { name: "Ordered list" }));
    const list = screen.getByRole("list", { name: "Supplied continuity ordered list" });
    expect(list.querySelectorAll(":scope > li")).toHaveLength(expected.listEntries.length);
    for (const entry of expected.listEntries) {
      const node = list.querySelector(`[data-node-id="${entry.nodeId}"]`);
      expect(node?.querySelectorAll("[data-related-edge-id]")).toHaveLength(entry.relatedEdgeIds.length);
      for (const edgeId of entry.relatedEdgeIds) expect(node?.querySelector(`[data-related-edge-id="${edgeId}"]`)).not.toBeNull();
    }
  });

  it("starts narrow layouts in the semantic list and retains accessible controls", async () => {
    setNarrowLayout(true);
    await ready();
    expect(screen.getByRole("list", { name: "Supplied continuity ordered list" })).toBeVisible();
    expect(screen.queryByRole("img", { name: "Supplied intent continuity map" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Map" })).toBeEnabled();
    const css = readFileSync(resolve(process.cwd(), "src", "styles.css"), "utf8");
    expect(css).toContain("@media (max-width: 48rem)");
    expect(css).toContain("grid-template-columns: minmax(0, 1fr)");
    expect(css).toContain("prefers-reduced-motion: reduce");
    expect(css).toContain("--iti-focus-ring-width");
    expect(css).toContain("overflow-wrap: anywhere");
  });

  it("opens evidence before hashes, traps focus, closes with Escape and restores focus", async () => {
    const user = userEvent.setup();
    await ready();
    const opener = screen.getByRole("button", { name: /^Inspect evidence/ });
    await user.click(opener);
    const dialog = screen.getByRole("dialog", { name: "Inspect the evidence." });
    const close = within(dialog).getByRole("button", { name: "Close evidence" });
    expect(close).toHaveFocus();
    expect(within(dialog).getAllByText("Observed time").length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText(/ineligible for live proof/).length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText(/synthetic/).length).toBeGreaterThan(0);
    expect(within(dialog).getByText(/V2 public-endpoint examples are not current NSP proof/)).toBeVisible();
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(within(dialog).getByRole("button", { name: "Return to snapshot" })).toHaveFocus();
    await user.tab();
    expect(close).toHaveFocus();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(opener).toHaveFocus());
    await user.click(opener);
    await user.click(screen.getByRole("button", { name: "Close evidence" }));
    await waitFor(() => expect(opener).toHaveFocus());
  });

  it("shows missing evidence honestly inside the drawer", async () => {
    const user = userEvent.setup();
    await ready("FX-11:missing-evidence");
    await user.click(screen.getByRole("button", { name: /^Inspect evidence/ }));
    expect(screen.getByRole("heading", { name: "No configuration evidence loaded" })).toBeVisible();
    expect(screen.getByText(/Missing is not verified/)).toBeVisible();
  });

  it("fails visibly for an unknown scene instead of substituting success", async () => {
    await ready("FX-99");
    expect(screen.getByRole("alert")).toHaveTextContent("Unknown scene: FX-99");
    expect(screen.getByText(/No live API was contacted/)).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Follow the evidence." })).not.toBeInTheDocument();
  });

  it("fails visibly for an unknown action result", async () => {
    const user = userEvent.setup();
    const base = createFixtureTransport();
    await ready("FX-09", { ...base, navigate: async () => { throw new FixtureError("Unknown action: rejected-test-action"); } });
    await user.click(screen.getByRole("button", { name: /Review correction example/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unknown action");
    expect(screen.queryByText("Correction prepared", { selector: ".status-badge" })).not.toBeInTheDocument();
  });

  it("renders a real empty-catalog state without requesting data", async () => {
    const base = createFixtureTransport();
    const loadScene = vi.fn(base.loadScene);
    render(<App transport={{ ...base, choices: [], loadScene }} />);
    expect(screen.getByRole("heading", { name: "No authored snapshots." })).toBeVisible();
    expect(screen.getByLabelText("Review scene")).toBeDisabled();
    expect(loadScene).not.toHaveBeenCalled();
    expect(screen.getByText(HISTORICAL_NOTICE)).toBeVisible();
  });

  it("renders a safe error for missing fixture data", async () => {
    const inputs = structuredClone(defaultInputs);
    inputs.files = {};
    await ready("FX-09", createFixtureTransport(inputs));
    expect(screen.getByRole("alert")).toHaveTextContent("Missing fixture data");
    expect(screen.getByText(HISTORICAL_NOTICE)).toBeVisible();
  });
});
