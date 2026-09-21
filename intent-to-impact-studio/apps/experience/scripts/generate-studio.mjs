import { compileFromFile } from "../../../contracts/node_modules/json-schema-to-typescript/dist/src/index.js";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv from "ajv";
import addFormats from "ajv-formats";
import standaloneCode from "ajv/dist/standalone/index.js";
import { buildSync } from "esbuild";

const app = fileURLToPath(new URL("../", import.meta.url));
const input = resolve(app, "..", "control-plane", "studio", "studio.schema.json");
const output = resolve(app, "src", "studio", "contracts.d.ts");
const generated = await compileFromFile(input, {
  ignoreMinAndMaxItems: true,
  bannerComment: "/* Generated from apps/control-plane/studio/studio.schema.json. Do not edit. */",
});
const schema = JSON.parse(readFileSync(input, "utf8"));
const validatorNames = {
  jobShape: "StudioJob", buildShape: "BuildResult",
  inputShape: "AnalysisRequest", requestBuildShape: "BuildRequest",
  historyShape: "RunHistory", savedRunShape: "SavedRun",
};
const ajv = new Ajv({ allErrors: true, strict: false, code: { source: true, esm: true } });
addFormats(ajv);
ajv.addSchema(schema);
const exports = {};
for (const [name, definition] of Object.entries(validatorNames)) {
  const id = `urn:studio:generated:${name}`;
  ajv.addSchema({ $id: id, $ref: `${schema.$id}#/definitions/${definition}` });
  exports[name] = id;
}
const validators = buildSync({
  stdin: { contents: standaloneCode(ajv, exports), sourcefile: "studio-validators.js", resolveDir: app },
  bundle: true, platform: "browser", format: "esm", write: false, target: "es2022",
  banner: { js: "/* Generated from studio.schema.json. CSP-safe static validators; do not edit. */" },
}).outputFiles[0].text;
const declarations = "/* Generated from studio.schema.json. Do not edit. */\n"
  + 'import type { StudioJob, BuildResult, AnalysisRequest, BuildRequest, RunHistory, SavedRun } from "./contracts";\n'
  + Object.entries(validatorNames).map(([name, definition]) =>
    `export declare function ${name}(value: unknown): value is ${definition};`).join("\n") + "\n";
const outputs = new Map([
  [output, generated],
  [resolve(app, "src", "studio", "validators.js"), validators],
  [resolve(app, "src", "studio", "validators.d.ts"), declarations],
]);
if (process.argv.includes("--check")) {
  for (const [path, content] of outputs) {
    if (readFileSync(path, "utf8") !== content) throw new Error(`Studio generated output drift: ${path}`);
  }
  console.log("Studio generated types and CSP-safe validators match the authoritative schema.");
} else {
  for (const [path, content] of outputs) writeFileSync(path, content);
  console.log("Studio types and CSP-safe validators generated.");
}
