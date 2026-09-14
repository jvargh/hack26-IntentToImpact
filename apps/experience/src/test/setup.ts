import { webcrypto } from "node:crypto";
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

let narrow = false;
export function setNarrowLayout(value: boolean) { narrow = value; }
Object.defineProperty(globalThis, "crypto", { value: webcrypto, configurable: true });
Object.defineProperty(window, "matchMedia", {
  configurable: true,
  value: (query: string): MediaQueryList => ({
    get matches() { return narrow && query.includes("48rem"); },
    media: query, onchange: null,
    addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {},
    dispatchEvent() { return true; },
  }),
});
beforeEach(() => { narrow = false; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
