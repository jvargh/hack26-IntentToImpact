import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ArchitectureCanvas } from "./ArchitectureCanvas";
import type { ArchitectureOption } from "../contracts";

const option: ArchitectureOption = {
  id: "interaction-fixture", name: "Interaction-only fixture", rationale: "Canvas test, not model proof",
  tradeoffs: ["Fixture"], costNotes: "Not priced",
  components: [
    { id: "client", kind: "client", label: "Customer", service: "Client", responsibility: "Submit", requirementIds: ["r1"] },
    { id: "api", kind: "appservice", label: "API", service: "AppService", responsibility: "Process", requirementIds: ["r1"] },
  ],
  connections: [{ id: "request", source: "client", target: "api", label: "Request" }],
};

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
    return this.classList.contains("st-graph-viewport") ? new DOMRect(100, 50, 800, 600) : new DOMRect();
  });
});

function mount() {
  const view = render(<><input aria-label="Outside prompt" /><button>Outside control</button>
    <ArchitectureCanvas option={option} selectedId={null} highlightedIds={null} onSelect={vi.fn()} /></>);
  const canvas = screen.getByRole("region", { name: "Interactive architecture canvas" });
  return { ...view, canvas };
}

const percent = () => Number(screen.getByLabelText("Canvas zoom").textContent?.replace("%", ""));
function transform() {
  const plane = document.querySelector<HTMLElement>(".st-graph-plane")!;
  const match = /translate\(([-\d.]+)px, ([-\d.]+)px\) scale\(([-\d.]+)\)/.exec(plane.style.transform)!;
  return { x: Number(match[1]), y: Number(match[2]), zoom: Number(match[3]) };
}

describe("scoped canvas zoom interactions", () => {
  it("keeps manual placement on Fit and restores automatic placement only on Re-layout", () => {
    mount();
    const node = screen.getByRole("button", { name: "Inspect API" });
    const original = node.style.left;
    fireEvent.keyDown(node, { key: "ArrowRight", shiftKey: true });
    const moved = node.style.left;
    expect(moved).not.toBe(original);
    fireEvent.click(screen.getByRole("button", { name: "Fit" }));
    expect(node.style.left).toBe(moved);
    fireEvent.click(screen.getByRole("button", { name: "Re-layout" }));
    expect(node.style.left).toBe(original);
  });

  it("switches direction and exposes label control without changing connections", () => {
    mount();
    const customer = screen.getByRole("button", { name: "Inspect Customer" });
    const api = screen.getByRole("button", { name: "Inspect API" });
    expect(Number.parseFloat(api.style.left)).toBeGreaterThan(Number.parseFloat(customer.style.left));
    fireEvent.change(screen.getByRole("combobox", { name: "Flow direction" }), { target: { value: "TB" } });
    expect(api.style.left).toBe(customer.style.left);
    expect(Number.parseFloat(api.style.top)).toBeGreaterThan(Number.parseFloat(customer.style.top));
    expect(document.querySelectorAll("[data-edge-id]")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Labels" }));
    expect(document.querySelector("[data-edge-id]")).toHaveClass("show-label");
    fireEvent.click(screen.getByRole("button", { name: "List view" }));
    expect(screen.getByRole("button", { name: "Re-layout" })).toBeDisabled();
    expect(screen.getByRole("combobox", { name: "Flow direction" })).toBeDisabled();
  });

  it.each([
    { key: "=", ctrlKey: true }, { key: "+", ctrlKey: true, shiftKey: true },
    { key: "Add", code: "NumpadAdd", ctrlKey: true }, { key: "=", metaKey: true },
  ])("zooms in with the keyboard shortcut %j", (shortcut) => {
    const { canvas } = mount();
    canvas.focus();
    const before = percent();
    expect(fireEvent.keyDown(canvas, shortcut)).toBe(false);
    expect(percent()).toBeGreaterThan(before);
  });

  it.each([
    { key: "-", ctrlKey: true }, { key: "_", ctrlKey: true, shiftKey: true },
    { key: "Subtract", code: "NumpadSubtract", ctrlKey: true }, { key: "-", metaKey: true },
  ])("zooms out with the keyboard shortcut %j", (shortcut) => {
    const { canvas } = mount();
    canvas.focus();
    const before = percent();
    expect(fireEvent.keyDown(canvas, shortcut)).toBe(false);
    expect(percent()).toBeLessThan(before);
  });

  it("handles hover shortcuts but preserves browser shortcuts outside and in editable fields", () => {
    const { canvas } = mount();
    fireEvent.pointerEnter(canvas);
    const before = percent();
    expect(fireEvent.keyDown(document.body, { key: "=", ctrlKey: true })).toBe(false);
    expect(percent()).toBeGreaterThan(before);
    const after = percent();
    const input = screen.getByRole("textbox", { name: "Outside prompt" });
    input.focus();
    expect(fireEvent.keyDown(input, { key: "=", ctrlKey: true })).toBe(true);
    expect(percent()).toBe(after);
    fireEvent.pointerLeave(canvas);
    const outside = screen.getByRole("button", { name: "Outside control" });
    outside.focus();
    expect(fireEvent.keyDown(outside, { key: "-", ctrlKey: true })).toBe(true);
    expect(percent()).toBe(after);
  });

  it("zooms Ctrl-wheel around the pointer while normal wheel remains unhandled", () => {
    const { canvas } = mount();
    const before = transform();
    expect(fireEvent.wheel(canvas, { deltaY: -100, clientX: 300, clientY: 200 })).toBe(true);
    expect(transform()).toEqual(before);
    expect(fireEvent.wheel(canvas, { deltaY: -100, clientX: 300, clientY: 200, ctrlKey: true })).toBe(false);
    const after = transform();
    expect(after.zoom).toBeGreaterThan(before.zoom);
    expect((200 - after.x) / after.zoom).toBeCloseTo((200 - before.x) / before.zoom, 7);
    expect((150 - after.y) / after.zoom).toBeCloseTo((150 - before.y) / before.zoom, 7);
    expect(fireEvent.wheel(canvas, { deltaY: 100, clientX: 300, clientY: 200, ctrlKey: true })).toBe(false);
    expect(transform().zoom).toBeCloseTo(before.zoom, 7);
  });

  it("keeps keyboard, wheel and buttons inside the existing zoom limits", () => {
    const { canvas } = mount();
    canvas.focus();
    for (let i = 0; i < 30; i++) fireEvent.keyDown(canvas, { key: "=", ctrlKey: true });
    expect(percent()).toBe(180);
    expect(screen.getByRole("button", { name: "Zoom in" })).toBeDisabled();
    for (let i = 0; i < 30; i++) fireEvent.wheel(canvas, { deltaY: 100, ctrlKey: true });
    expect(percent()).toBe(25);
    expect(screen.getByRole("button", { name: "Zoom out" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(percent()).toBeGreaterThan(25);
  });

  it("fits with Ctrl+0 and leaves list mode and unmodified keys alone", () => {
    const { canvas } = mount();
    canvas.focus();
    fireEvent.keyDown(canvas, { key: "+", ctrlKey: true });
    expect(fireEvent.keyDown(canvas, { key: "0", ctrlKey: true })).toBe(false);
    const fitted = percent();
    expect(fireEvent.keyDown(canvas, { key: "+" })).toBe(true);
    expect(percent()).toBe(fitted);
    fireEvent.click(screen.getByRole("button", { name: "List view" }));
    expect(fireEvent.keyDown(canvas, { key: "+", ctrlKey: true })).toBe(true);
    expect(fireEvent.wheel(canvas, { deltaY: -100, ctrlKey: true })).toBe(true);
    expect(percent()).toBe(fitted);
  });

  it("removes native shortcut and wheel listeners on unmount", () => {
    const { canvas, unmount } = mount();
    fireEvent.pointerEnter(canvas);
    unmount();
    expect(fireEvent.keyDown(document.body, { key: "=", ctrlKey: true })).toBe(true);
    expect(fireEvent.wheel(canvas, { deltaY: -100, ctrlKey: true })).toBe(true);
  });
});
