import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import tokenManifest from "../../design/tokens/tokens.v2-manifest.json";

const root = fileURLToPath(new URL("../../", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@design-tokens.css": resolve(root, ...tokenManifest.css.path.split("\\")),
    },
  },
  server: {
    host: "127.0.0.1",
    fs: { allow: [
      resolve(root, "apps", "experience"),
      resolve(root, "fixtures", "experience", "initial-v2-r2"),
      resolve(root, "contracts", "schemas", "1.0.0"),
      resolve(root, "apps", "control-plane", "studio"),
      resolve(root, "design", "tokens"),
    ] },
  },
  preview: { host: "127.0.0.1" },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("/node_modules/")) return "vendor";
          const scene = /\/initial-v2-r2\/scenes\/([^/]+)\//.exec(id)?.[1];
          return scene ? `fixture-${scene}` : undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
