import { useEffect, useId, useState } from "react";
import type { GraphNode, IntentContinuityGraph } from "@contracts/projections";
import { StatusBadge, statusTone } from "./StatusBadge";

const nodeLabels: Readonly<Record<GraphNode["nodeType"], string>> = {
  intent: "Business intent", promise: "Customer promise", component: "Design component",
  baseline: "Runtime binding", "runtime-snapshot": "Configuration snapshot",
  finding: "Finding", evaluation: "Promise evaluation", correction: "Correction", evidence: "Source evidence",
};
const slots: Readonly<Record<GraphNode["nodeType"], readonly [number, number]>> = {
  intent: [30, 30], promise: [310, 30], component: [590, 30],
  evaluation: [310, 210], "runtime-snapshot": [30, 210], baseline: [30, 390],
  evidence: [590, 210], finding: [310, 390], correction: [590, 390],
};
function lines(label: string): string[] {
  const result: string[] = [];
  let current = "";
  for (const word of label.split(" ")) {
    if ((current + " " + word).length > 28 && current) { result.push(current); current = word; }
    else current = current ? `${current} ${word}` : word;
  }
  if (current) result.push(current);
  return result.length > 3 ? [...result.slice(0, 2), (result[2] ?? "") + "…"] : result;
}

export function ContinuityGraph({ graph, onInspect }: {
  graph: IntentContinuityGraph;
  onInspect(recordId?: string): void;
}) {
  const [view, setView] = useState<"map" | "list">(() => window.matchMedia("(max-width: 48rem)").matches ? "list" : "map");
  const markerId = useId().replaceAll(":", "");
  useEffect(() => {
    const media = window.matchMedia("(max-width: 48rem)");
    const narrow = () => { if (media.matches) setView("list"); };
    media.addEventListener("change", narrow);
    return () => media.removeEventListener("change", narrow);
  }, []);
  const positions = new Map<string, { x: number; y: number }>();
  const used = new Set<string>();
  for (const node of graph.nodes) {
    const initial = node.source.kind === "gap" && node.nodeType === "evaluation" ? [590, 390] : slots[node.nodeType];
    const x = initial[0] ?? 30;
    let y = initial[1] ?? 30;
    while (used.has(`${x}:${y}`)) y += 180;
    used.add(`${x}:${y}`);
    positions.set(node.nodeId, { x, y });
  }
  const height = Math.max(510, ...Array.from(positions.values(), (point) => point.y + 120));
  const nodes = new Map(graph.nodes.map((node) => [node.nodeId, node]));
  const edges = new Map(graph.edges.map((edge) => [edge.edgeId, edge]));

  return <section className="continuity-card" aria-labelledby="continuity-title">
    <div className="section-heading">
      <div><p className="eyebrow">INTENT CONTINUITY</p><h2 id="continuity-title">Follow the evidence.</h2>
        <p className="muted">Only supplied relationships. A broken line names the gap in the promise.</p></div>
      <div className="view-switch" role="group" aria-label="Continuity view">
        <button aria-pressed={view === "map"} onClick={() => setView("map")}>Map</button>
        <button aria-pressed={view === "list"} onClick={() => setView("list")}>Ordered list</button>
      </div>
    </div>
    {graph.nodes.length === 0 ? <p className="empty-inline">No continuity data is supplied for this snapshot.</p>
      : view === "map" ? <div className="graph-visual">
        <svg viewBox={`0 0 860 ${height}`} role="img" aria-labelledby={`${markerId}-title`} aria-describedby={`${markerId}-description`}>
          <title id={`${markerId}-title`}>Supplied intent continuity map</title>
          <desc id={`${markerId}-description`}>Relationships are rendered exactly as supplied. Use Ordered list for full labels, status text and source inspection.</desc>
          <defs>{["supported", "broken", "pending", "gap"].map((status) =>
            <marker key={status} id={`${markerId}-${status}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" className={`arrow-${status}`} />
            </marker>)}</defs>
          {graph.edges.map((edge) => {
            const from = positions.get(edge.fromNodeId);
            const to = positions.get(edge.toNodeId);
            if (!from || !to) return null;
            const sameRow = from.y === to.y;
            const start = sameRow ? { x: from.x + (to.x > from.x ? 220 : 0), y: from.y + 47 }
              : { x: from.x + 110, y: from.y + (to.y > from.y ? 94 : 0) };
            const end = sameRow ? { x: to.x + (to.x > from.x ? 0 : 220), y: to.y + 47 }
              : { x: to.x + 110, y: to.y + (to.y > from.y ? 0 : 94) };
            const curved = sameRow && Math.abs(to.x - from.x) > 300;
            const vertical = start.x === end.x;
            const d = curved
              ? `M ${start.x} ${start.y} C ${start.x} ${start.y + 135}, ${end.x} ${end.y + 135}, ${end.x} ${end.y}`
              : `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
            return <g key={edge.edgeId} data-edge-id={edge.edgeId} data-edge-status={edge.status}>
              <path d={d} className={`graph-edge edge-${edge.status}`} markerEnd={`url(#${markerId}-${edge.status})`} />
              <text x={(start.x + end.x) / 2 + (vertical ? 9 : 0)}
                y={(start.y + end.y) / 2 + (curved ? 135 * 0.75 : 0) - 9}
                textAnchor={vertical ? "start" : "middle"} className={`edge-caption caption-${edge.status}`}>
                {edge.status}
              </text>
            </g>;
          })}
          {graph.nodes.map((node) => {
            const point = positions.get(node.nodeId);
            if (!point) return null;
            return <g key={node.nodeId} transform={`translate(${point.x},${point.y})`} data-node-id={node.nodeId}>
              <title>{node.label}</title>
              <rect width="220" height="94" rx="8" className={node.source.kind === "gap" ? "graph-node graph-gap" : "graph-node"} />
              <text x="16" y="24" className="node-type">{nodeLabels[node.nodeType]}</text>
              {lines(node.label).map((line, index) => <text key={index} x="16" y={44 + index * 17} className="node-label">{line}</text>)}
            </g>;
          })}
        </svg>
        <p className="graph-caption">Solid: supplied relationship · dashed red: broken · dashed amber: pending or gap.
          <button className="text-button" onClick={() => setView("list")}>Read the exact path →</button></p>
      </div> : <ol className="continuity-list" aria-label="Supplied continuity ordered list">
        {graph.listEntries.map((entry) => {
          const node = nodes.get(entry.nodeId);
          if (!node) return null;
          return <li key={entry.nodeId} data-node-id={entry.nodeId}>
            <div className="list-node-title"><span><span className="small-label">{nodeLabels[node.nodeType]}</span><strong>{node.label}</strong></span>
              {node.source.kind === "artifact" && <button className="text-button"
                onClick={() => node.source.kind === "artifact" && onInspect(node.source.reference.artifact.artifactId)}>
                Inspect source<span className="sr-only"> for {node.label}</span> ↗
              </button>}</div>
            <ul aria-label={`Connections for ${node.label}`}>
              {entry.relatedEdgeIds.map((edgeId) => {
                const edge = edges.get(edgeId);
                if (!edge) return null;
                return <li key={edgeId} data-related-edge-id={edgeId}>
                  <StatusBadge label={edge.status} tone={statusTone(edge.status)} />
                  <span>{nodes.get(edge.fromNodeId)?.label} <span aria-hidden="true">→</span><span className="sr-only"> to </span> {nodes.get(edge.toNodeId)?.label}</span>
                </li>;
              })}
            </ul>
          </li>;
        })}
      </ol>}
  </section>;
}
