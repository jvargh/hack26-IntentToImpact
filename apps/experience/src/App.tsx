import { lazy, Suspense } from "react";
import { StudioApp } from "./studio/StudioApp";

const LegacyPreview = lazy(() => import("./LegacyPreview").then((module) => ({ default: module.LegacyPreview })));

export function App() {
  if (new URLSearchParams(window.location.search).get("view") === "legacy-risk"
    || window.location.pathname.replace(/\/$/, "") === "/legacy-risk") {
    return <Suspense fallback={<p role="status">Opening the historical component preview...</p>}><LegacyPreview /></Suspense>;
  }
  return <StudioApp />;
}
