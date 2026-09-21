import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { CSSProperties, PointerEvent } from "react";
import type { ArchitectureOption } from "../contracts";
import { fitGraph, layoutGraph, movedRoute, NODE_HEIGHT, NODE_WIDTH } from "./graphLayout";
import type { EdgeRoute, FlowDirection, Point } from "./graphLayout";

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 1.8;
const ZOOM_STEP = 1.2;
const clampZoom = (value: number) => Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, value));
const kindSymbols = { appservice: "▣", functions: "ϟ", storage: "▤", servicebus: "⇄", keyvault: "◇", external: "↗", client: "▱" };

export function ArchitectureCanvas({ option, selectedId, highlightedIds, onSelect, expanded = false, onExpand, simulated = false }: {
  option: ArchitectureOption | null;
  selectedId: string | null;
  highlightedIds: string[] | null;
  onSelect: (id: string) => void;
  expanded?: boolean;
  onExpand?: () => void;
  simulated?: boolean;
}) {
  const markerId = useId().replaceAll(":", "");
  const hintId = useId();
  const [direction, setDirection] = useState<FlowDirection>("LR");
  const [labels, setLabels] = useState(false);
  const arranged = useMemo(() => {
    try { return { graph: option ? layoutGraph(option, direction) : null, error: "" }; }
    catch (failure) { return { graph: null, error: failure instanceof Error ? failure.message : "The topology could not be laid out." }; }
  }, [option, direction]);
  const initial = arranged.graph?.positions ?? {};
  const [positions, setPositions] = useState<Record<string, Point>>({});
  const [{ offset, zoom }, setCamera] = useState({ offset: { x: 0, y: 0 }, zoom: 0.8 });
  const [listMode, setListMode] = useState(false);
  const canvas = useRef<HTMLElement>(null);
  const hovered = useRef(false);
  const viewport = useRef<HTMLDivElement>(null);
  const drag = useRef<{ id: string | null; start: Point; origin: Point } | null>(null);
  const actual = { ...initial, ...positions };
  const routes: Record<string, EdgeRoute> = {};
  for (const edge of option?.connections ?? []) {
    const route = arranged.graph?.routes[edge.id];
    const source = actual[edge.source]; const target = actual[edge.target];
    const originalSource = initial[edge.source]; const originalTarget = initial[edge.target];
    if (route && source && target && originalSource && originalTarget) routes[edge.id] = movedRoute(route, source, target, originalSource, originalTarget, edge.source === edge.target);
  }
  const scene = useRef({ positions: actual, routes });
  scene.current = { positions: actual, routes };
  const width = Math.max(arranged.graph?.width ?? 0, ...Object.values(actual).map((point) => point.x + NODE_WIDTH + 24));
  const height = Math.max(arranged.graph?.height ?? 0, ...Object.values(actual).map((point) => point.y + NODE_HEIGHT + 24));
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    function resize() {
      const bounds = element!.getBoundingClientRect();
      if (bounds.width && bounds.height) {
        setCamera(fitGraph(scene.current.positions, scene.current.routes, bounds));
      }
    }
    resize();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    return () => observer.disconnect();
  }, [arranged.graph, listMode]);

  const zoomAt = useCallback((factor: number, anchor?: Point) => {
    const bounds = viewport.current?.getBoundingClientRect();
    const point = anchor ?? { x: (bounds?.width ?? 0) / 2, y: (bounds?.height ?? 0) / 2 };
    setCamera((current) => {
      const nextZoom = clampZoom(current.zoom * factor);
      const ratio = nextZoom / current.zoom;
      return {
        zoom: nextZoom,
        offset: {
          x: point.x - (point.x - current.offset.x) * ratio,
          y: point.y - (point.y - current.offset.y) * ratio,
        },
      };
    });
  }, []);

  const fit = useCallback(() => {
    const bounds = viewport.current?.getBoundingClientRect();
    if (bounds?.width && bounds.height) setCamera(fitGraph(scene.current.positions, scene.current.routes, bounds));
  }, []);

  function reLayout() {
    const bounds = viewport.current?.getBoundingClientRect();
    if (!arranged.graph || !bounds?.width || !bounds.height) return;
    setPositions({});
    setCamera(fitGraph(arranged.graph.positions, arranged.graph.routes, bounds));
  }

  useEffect(() => {
    const element = canvas.current;
    if (!element || !option || listMode) return;
    const keydown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || !(event.ctrlKey || event.metaKey)) return;
      const focused = document.activeElement;
      if (focused instanceof Element && focused.closest("input, textarea, select, [contenteditable]:not([contenteditable='false']), [role='dialog']")) return;
      if (!hovered.current && !element.contains(focused)) return;
      const bounds = viewport.current?.getBoundingClientRect();
      if (!bounds?.width || !bounds.height) return;
      if (["+", "=", "Add"].includes(event.key) || event.code === "NumpadAdd") {
        event.preventDefault();
        zoomAt(ZOOM_STEP);
      } else if (["-", "_", "Subtract"].includes(event.key) || event.code === "NumpadSubtract") {
        event.preventDefault();
        zoomAt(1 / ZOOM_STEP);
      } else if (event.key === "0") {
        event.preventDefault();
        fit();
      }
    };
    const wheel = (event: WheelEvent) => {
      if (event.defaultPrevented || event.altKey || !(event.ctrlKey || event.metaKey) || event.deltaY === 0) return;
      const bounds = viewport.current?.getBoundingClientRect();
      if (!bounds?.width || !bounds.height) return;
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? bounds.height : 1);
      event.preventDefault();
      zoomAt(Math.exp(-Math.max(-100, Math.min(100, delta)) * 0.002), {
        x: event.clientX - bounds.left, y: event.clientY - bounds.top,
      });
    };
    document.addEventListener("keydown", keydown);
    element.addEventListener("wheel", wheel, { passive: false });
    return () => {
      document.removeEventListener("keydown", keydown);
      element.removeEventListener("wheel", wheel);
    };
  }, [option, listMode, zoomAt, fit]);

  function startDrag(event: PointerEvent<HTMLElement>, id: string | null) {
    if (event.button !== 0 || (!id && (event.target as HTMLElement).closest("button"))) return;
    if (!id) canvas.current?.focus({ preventScroll: true });
    event.currentTarget.setPointerCapture?.(event.pointerId);
    drag.current = { id, start: { x: event.clientX, y: event.clientY }, origin: id ? actual[id] ?? { x: 0, y: 0 } : offset };
    if (id) onSelect(id);
    event.stopPropagation();
  }
  function moveDrag(event: PointerEvent<HTMLElement>) {
    const active = drag.current;
    if (!active) return;
    const factor = active.id ? zoom : 1;
    const point = { x: active.origin.x + (event.clientX - active.start.x) / factor, y: active.origin.y + (event.clientY - active.start.y) / factor };
    if (active.id) setPositions((previous) => ({ ...previous, [active.id!]: point }));
    else setCamera((current) => ({ ...current, offset: point }));
  }
  return <section className="st-canvas" aria-label="Interactive architecture canvas" ref={canvas}
    tabIndex={option ? 0 : undefined} aria-describedby={option ? hintId : undefined}
    aria-keyshortcuts={option ? "Control+= Control+- Control+0 Meta+= Meta+- Meta+0" : undefined}
    onPointerEnter={() => { hovered.current = true; }} onPointerLeave={() => { hovered.current = false; }}>
    <div className="st-canvas-caption"><span className="st-overline">TOPOLOGY / {option ? simulated ? "SIMULATED EXAMPLE" : "MODEL-GENERATED" : "NO RESULT"}</span><span>{option ? `${option.components.length} components · ${option.connections.length} connections` : "Your architecture belongs here"}</span></div>
    {!option ? <div className="st-canvas-empty">
      <div className="st-empty-orbit" aria-hidden="true"><i /><i /><i /><span>⌘</span></div>
      <span className="st-overline">FROM INTENT TO INFRASTRUCTURE</span>
      <h2>Think it.<br /><em>Trace it. Build it.</em></h2>
      <p>Describe a real process. Explore the architecture behind it, challenge the trade-offs, and compile the infrastructure.</p>
      <div className="st-empty-steps"><span>01 / Sources</span><span>02 / Architecture</span><span>03 / Compiled files</span></div>
      <small>Illustration only. No architecture has been generated.</small>
    </div> : <>
      {arranged.error && <div className="st-layout-error st-error" role="alert">Layout failed: {arranged.error} Use List view to inspect the unchanged topology.</div>}
      <div className={`st-graph-viewport ${listMode ? "st-list-selected" : ""}`} ref={viewport}
        onPointerDown={(event) => startDrag(event, null)} onPointerMove={moveDrag}
        onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
        <div className="st-graph-plane" style={{ width, height, transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})` }}>
          <svg className="st-edges" width={width} height={height} aria-label="Architecture connections">
            <defs><marker id={markerId} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" /></marker></defs>
            {option.connections.map((edge) => {
              const route = routes[edge.id];
              if (!route) return null;
              const connected = edge.source === selectedId || edge.target === selectedId;
              return <g key={edge.id} data-edge-id={edge.id} className={`st-edge ${connected ? "is-selected" : selectedId ? "is-muted" : ""} ${labels ? "show-label" : ""}`}><title>{edge.source} → {edge.target}: {edge.label}</title>
                <path d={route.points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" ")} markerEnd={`url(#${markerId})`} />
                <text x={route.label.x} y={route.label.y - 10} textAnchor="middle">{edge.label.length > 28 ? `${edge.label.slice(0, 27)}…` : edge.label}</text>
              </g>;
            })}
          </svg>
          {!arranged.error && option.components.map((component, index) => {
            const point = actual[component.id];
            if (!point) return null;
            return <button key={component.id} type="button" className={`st-node st-kind-${component.kind} ${selectedId === component.id ? "is-selected" : ""} ${highlightedIds && !highlightedIds.includes(component.id) ? "is-muted" : ""}`}
              style={{ left: point.x, top: point.y, "--node-index": index } as CSSProperties}
              aria-label={`Inspect ${component.label}`} aria-pressed={selectedId === component.id}
              onClick={() => onSelect(component.id)} onPointerDown={(event) => startDrag(event, component.id)}
              onKeyDown={(event) => {
                if (!event.shiftKey || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
                event.preventDefault();
                setPositions((previous) => ({ ...previous, [component.id]: { x: point.x + (event.key === "ArrowRight" ? 20 : event.key === "ArrowLeft" ? -20 : 0), y: point.y + (event.key === "ArrowDown" ? 20 : event.key === "ArrowUp" ? -20 : 0) } }));
              }}>
              <span className="st-node-top"><span className="st-node-symbol">{kindSymbols[component.kind]}</span><span className="st-overline">{component.kind}</span><span className="st-node-port" /></span>
              <strong>{component.label}</strong><span className="st-node-service">{component.service}</span>
            </button>;
          })}
        </div>
      </div>
      <div className={`st-topology-list ${listMode ? "st-list-selected" : ""}`} aria-label="Architecture component list">
        {option.components.map((component) => <button key={component.id} type="button" aria-label={`Inspect ${component.label} in list`} aria-pressed={selectedId === component.id} onClick={() => onSelect(component.id)}>
          <span>{kindSymbols[component.kind]}</span><strong>{component.label}</strong><small>{component.service}</small>
        </button>)}
        <ul className="st-list-connections">{option.connections.map((edge) => <li key={edge.id}>{option.components.find((item) => item.id === edge.source)?.label} → {option.components.find((item) => item.id === edge.target)?.label}<small>{edge.label}</small></li>)}</ul>
      </div>
      <div className="st-canvas-controls"><div className="st-control-group"><button type="button" aria-label="Zoom out" disabled={zoom <= MIN_ZOOM || listMode} onClick={() => zoomAt(1 / ZOOM_STEP)}>−</button><output aria-label="Canvas zoom">{Math.round(zoom * 100)}%</output><button type="button" aria-label="Zoom in" disabled={zoom >= MAX_ZOOM || listMode} onClick={() => zoomAt(ZOOM_STEP)}>+</button><button type="button" onClick={fit} disabled={listMode || !!arranged.error}>Fit</button></div>
        <div className="st-layout-controls"><button type="button" onClick={reLayout} disabled={listMode || !!arranged.error} title="Restore automatic node placement and route connections">Re-layout</button>
          <select aria-label="Flow direction" value={direction} disabled={listMode} onChange={(event) => { setPositions({}); setDirection(event.target.value === "TB" ? "TB" : "LR"); }}>
            <option value="LR">Left to right</option><option value="TB">Top to bottom</option>
          </select><button type="button" onClick={() => setLabels((value) => !value)} aria-pressed={labels} disabled={listMode} title="Show all connection labels; selected connections always show labels">Labels</button>
          {onExpand && <button type="button" onClick={onExpand} aria-pressed={expanded}>{expanded ? "Restore panels" : "Expand"}</button>}
          <button type="button" onClick={() => setListMode((value) => !value)} aria-pressed={listMode}>{listMode ? "Canvas view" : "List view"}</button></div></div>
      <div className="st-canvas-hint" id={hintId}>Hover/focus canvas: Ctrl/Cmd +/− or Ctrl + wheel to zoom · Ctrl/Cmd 0 to fit · Drag to pan · Shift + arrows move nodes</div>
    </>}
  </section>;
}
