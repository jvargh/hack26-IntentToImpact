import { Graph, layout } from "@dagrejs/dagre";
import type { EdgeLabel, GraphLabel, NodeLabel, Point } from "@dagrejs/dagre";
import type { ArchitectureOption } from "../contracts";

export type { Point };
export type FlowDirection = "LR" | "TB";
export const NODE_WIDTH = 214;
export const NODE_HEIGHT = 100;
export type EdgeRoute = { points: Point[]; label: Point };
export type GraphLayout = { positions: Record<string, Point>; routes: Record<string, EdgeRoute>; width: number; height: number };

function finite(value: number | undefined): number {
  if (value === undefined || !Number.isFinite(value)) throw new Error("The layout engine returned an invalid coordinate.");
  return value;
}

export function layoutGraph(option: ArchitectureOption, direction: FlowDirection): GraphLayout {
  const graph = new Graph<GraphLabel, NodeLabel, EdgeLabel>({ multigraph: true });
  graph.setGraph({ rankdir: direction, ranksep: 70, nodesep: 44, edgesep: 18,
    marginx: 24, marginy: 24, acyclicer: "greedy", ranker: "network-simplex" });
  const components = new Map(option.components.map((node) => [node.id, node]));
  if (components.size !== option.components.length || new Set(option.connections.map((edge) => edge.id)).size !== option.connections.length) {
    throw new Error("The topology contains duplicate component or connection IDs.");
  }
  const byId = (a: { id: string }, b: { id: string }) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  for (const node of [...option.components].sort(byId)) graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  for (const edge of [...option.connections].sort(byId)) {
    if (!components.has(edge.source) || !components.has(edge.target)) throw new Error("A topology connection references a missing component.");
    graph.setEdge(edge.source, edge.target, { weight: components.get(edge.source)?.kind === "external" ? 1 : 3 }, edge.id);
  }
  layout(graph);
  const positions = Object.fromEntries(option.components.map((node) => {
    const placed = graph.node(node.id);
    return [node.id, { x: finite(placed.x) - NODE_WIDTH / 2, y: finite(placed.y) - NODE_HEIGHT / 2 }];
  }));
  const routes = Object.fromEntries(option.connections.map((edge) => {
    const routed = graph.edge({ v: edge.source, w: edge.target, name: edge.id });
    if (!routed.points || routed.points.length < 2) throw new Error("The layout engine did not route every connection.");
    const points = routed.points.map((point) => ({ x: finite(point.x), y: finite(point.y) }));
    const middle = points[Math.floor(points.length / 2)];
    if (!middle) throw new Error("The connection route has no label position.");
    return [edge.id, { points, label: { ...middle } }];
  }));
  return { positions, routes, width: finite(graph.graph().width), height: finite(graph.graph().height) };
}

function boundary(position: Point, toward: Point): Point {
  const center = { x: position.x + NODE_WIDTH / 2, y: position.y + NODE_HEIGHT / 2 };
  const dx = toward.x - center.x; const dy = toward.y - center.y;
  if (dx === 0 && dy === 0) return { x: center.x + NODE_WIDTH / 2, y: center.y };
  const scale = 1 / Math.max(Math.abs(dx) / (NODE_WIDTH / 2), Math.abs(dy) / (NODE_HEIGHT / 2));
  return { x: center.x + dx * scale, y: center.y + dy * scale };
}

export function movedRoute(route: EdgeRoute, source: Point, target: Point, originalSource: Point, originalTarget: Point, selfLoop: boolean): EdgeRoute {
  const movedSource = source.x !== originalSource.x || source.y !== originalSource.y;
  const movedTarget = target.x !== originalTarget.x || target.y !== originalTarget.y;
  if (!movedSource && !movedTarget) return route;
  if (selfLoop) {
    const shift = (point: Point) => ({ x: point.x + source.x - originalSource.x, y: point.y + source.y - originalSource.y });
    return { points: route.points.map(shift), label: shift(route.label) };
  }
  const points = route.points.map((point) => ({ ...point }));
  const next = points[1]; const previous = points[points.length - 2];
  if (!next || !previous) throw new Error("The connection route is incomplete.");
  if (movedSource) points[0] = boundary(source, next);
  if (movedTarget) points[points.length - 1] = boundary(target, previous);
  return { points, label: route.label };
}

export function fitGraph(positions: Record<string, Point>, routes: Record<string, EdgeRoute>, viewport: { width: number; height: number }) {
  const nodes = Object.values(positions);
  const points = Object.values(routes).flatMap((route) => route.points);
  const left = Math.min(0, ...nodes.map((point) => point.x - 24), ...points.map((point) => point.x - 12));
  const top = Math.min(0, ...nodes.map((point) => point.y - 24), ...points.map((point) => point.y - 12));
  const right = Math.max(1, ...nodes.map((point) => point.x + NODE_WIDTH + 24), ...points.map((point) => point.x + 12));
  const bottom = Math.max(1, ...nodes.map((point) => point.y + NODE_HEIGHT + 24), ...points.map((point) => point.y + 12));
  const zoom = Math.max(0.25, Math.min(1, viewport.width / (right - left), viewport.height / (bottom - top)));
  return { zoom, offset: { x: (viewport.width - (right - left) * zoom) / 2 - left * zoom,
    y: (viewport.height - (bottom - top) * zoom) / 2 - top * zoom } };
}
