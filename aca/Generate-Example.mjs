// Canonical demo input comes from the live Load Example button, not a duplicate.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { transformSync } from "../apps/experience/node_modules/esbuild/lib/main.js";

const source = fileURLToPath(new URL("../apps/experience/src/business/model.ts", import.meta.url));
const output = fileURLToPath(new URL("./example-input.json", import.meta.url));
const javascript = transformSync(readFileSync(source, "utf8"), { loader: "ts", format: "esm" }).code;
const { EXAMPLE_PROMPT, EXAMPLE_DOCUMENTS } = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString("base64")}`);
const contents = JSON.stringify({
  prompt: EXAMPLE_PROMPT,
  documents: EXAMPLE_DOCUMENTS.map(({ id, name, text }) => ({ id, name, text })),
}, null, 2) + "\n";
if (process.argv.includes("--check")) {
  if (readFileSync(output, "utf8") !== contents) throw new Error("Judge example input drift. Regenerate from the frontend source.");
  console.log("Judge example matches the Load Example inputs.");
} else {
  writeFileSync(output, contents);
  console.log("Generated the judge example input from the frontend.");
}
