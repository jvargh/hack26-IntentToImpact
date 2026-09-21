import { describe, expect, it } from "vitest";
import type { ArchitectureOption, Component } from "../contracts";
import { fitGraph, layoutGraph, movedRoute, NODE_HEIGHT, NODE_WIDTH } from "./graphLayout";

function topology(nodes: [string, Component["kind"]][], edges: [string, string][]): ArchitectureOption {
  return { id: "layout-fixture", name: "Layout fixture", rationale: "Geometry only", tradeoffs: ["Not model evidence"], costNotes: "Not priced",
    components: nodes.map(([id, kind]) => ({ id, kind, label: id, service: kind, responsibility: id, requirementIds: ["r1"] })),
    connections: edges.map(([source, target], index) => ({ id: `e-${String(index).padStart(2, "0")}`, source, target, label: `${source} to ${target}` })),
  };
}

// Same connectivity as the reported 11-component callback design; synthetic labels.
const reported = topology([
  ["client", "client"], ["public-api", "appservice"], ["ops-ui", "appservice"], ["sb", "servicebus"],
  ["store", "storage"], ["worker", "functions"], ["adapter", "functions"], ["kv", "keyvault"],
  ["erp", "external"], ["pay", "external"], ["wh", "external"],
], [
  ["client", "public-api"], ["public-api", "store"], ["public-api", "sb"], ["public-api", "kv"],
  ["ops-ui", "store"], ["ops-ui", "sb"], ["ops-ui", "kv"], ["sb", "worker"], ["worker", "store"],
  ["worker", "kv"], ["worker", "erp"], ["worker", "wh"], ["pay", "public-api"], ["wh", "public-api"],
  ["pay", "adapter"], ["wh", "adapter"], ["adapter", "sb"],
]);

describe("automatic topology layout", () => {
  it("separates deep chains instead of capping all later components in one column", () => {
    const nodes: [string, Component["kind"]][] = Array.from({ length: 8 }, (_, index) => [`node-${index}`, "functions"]);
    const chain = topology(nodes, nodes.slice(1).map(([id], index) => [`node-${index}`, id]));
    const scene = layoutGraph(chain, "LR");
    expect(new Set(Object.values(scene.positions).map((point) => point.x)).size).toBe(8);
    for (const edge of chain.connections) expect(scene.positions[edge.target]!.x).toBeGreaterThan(scene.positions[edge.source]!.x + NODE_WIDTH);
  });

  it.each(["LR", "TB"] as const)("lays out every reported node and feedback edge without block overlap (%s)", (direction) => {
    const original = structuredClone(reported);
    const scene = layoutGraph(reported, direction);
    expect(Object.keys(scene.positions)).toHaveLength(11);
    expect(Object.keys(scene.routes)).toHaveLength(17);
    const positions = Object.values(scene.positions);
    for (const [index, point] of positions.entries()) {
      expect(point.x).toBeGreaterThanOrEqual(0); expect(point.y).toBeGreaterThanOrEqual(0);
      expect(point.x + NODE_WIDTH).toBeLessThanOrEqual(scene.width);
      expect(point.y + NODE_HEIGHT).toBeLessThanOrEqual(scene.height);
      for (const other of positions.slice(index + 1)) {
        expect(point.x + NODE_WIDTH <= other.x || other.x + NODE_WIDTH <= point.x
          || point.y + NODE_HEIGHT <= other.y || other.y + NODE_HEIGHT <= point.y).toBe(true);
      }
    }
    if (direction === "LR") {
      expect(scene.width).toBeLessThanOrEqual(1500);
      expect(scene.height).toBeLessThanOrEqual(800);
      const columns = positions.map((point) => positions.filter((other) => other.x === point.x).length);
      expect(Math.max(...columns)).toBeLessThanOrEqual(4);
    }
    for (const route of Object.values(scene.routes)) expect(route.points.every((point) => Number.isFinite(point.x) && Number.isFinite(point.y))).toBe(true);
    expect(reported).toEqual(original);
  });

  it("is deterministic regardless of model array ordering", () => {
    expect(layoutGraph({ ...reported, components: [...reported.components].reverse(), connections: [...reported.connections].reverse() }, "LR"))
      .toEqual(layoutGraph(reported, "LR"));
  });

  it("preserves separate parallel, reverse and self-loop connections", () => {
    const scene = layoutGraph(topology([["a", "functions"], ["b", "storage"], ["isolated", "client"]],
      [["a", "b"], ["a", "b"], ["b", "a"], ["a", "a"]]), "LR");
    expect(Object.keys(scene.positions)).toHaveLength(3);
    expect(Object.keys(scene.routes)).toHaveLength(4);
    expect(scene.routes["e-00"]?.points).not.toEqual(scene.routes["e-01"]?.points);
    expect(scene.routes["e-03"]?.points.length).toBeGreaterThan(2);
  });

  it("fits negative manual positions without altering them", () => {
    const positions = { first: { x: -180, y: -90 }, second: { x: 500, y: 250 } };
    const original = structuredClone(positions);
    const camera = fitGraph(positions, {}, { width: 1200, height: 800 });
    for (const point of Object.values(positions)) {
      expect(point.x * camera.zoom + camera.offset.x).toBeGreaterThanOrEqual(0);
      expect(point.y * camera.zoom + camera.offset.y).toBeGreaterThanOrEqual(0);
      expect((point.x + NODE_WIDTH) * camera.zoom + camera.offset.x).toBeLessThanOrEqual(1200);
      expect((point.y + NODE_HEIGHT) * camera.zoom + camera.offset.y).toBeLessThanOrEqual(800);
    }
    expect(positions).toEqual(original);
  });

  it("updates moved edge endpoints and translates self-loops without changing saved routes", () => {
    const route = { points: [{ x: 214, y: 50 }, { x: 260, y: 50 }, { x: 300, y: 50 }], label: { x: 260, y: 50 } };
    const original = structuredClone(route);
    const moved = movedRoute(route, { x: -30, y: 0 }, { x: 330, y: 0 }, { x: 0, y: 0 }, { x: 300, y: 0 }, false);
    expect(moved.points[0]).toEqual({ x: 184, y: 50 });
    expect(moved.points[2]).toEqual({ x: 330, y: 50 });
    expect(movedRoute(route, { x: 40, y: 20 }, { x: 40, y: 20 }, { x: 0, y: 0 }, { x: 0, y: 0 }, true).label).toEqual({ x: 300, y: 70 });
    expect(route).toEqual(original);
  });

  it("reports unknown endpoints rather than inventing extra nodes", () => {
    expect(() => layoutGraph(topology([["a", "functions"]], [["a", "missing"]]), "LR")).toThrow("missing component");
  });
});
