import type { BuildFile, BuildResult } from "./contracts";

export const AZURE_PORTAL_DEPLOY_URL = "https://portal.azure.com/#create/Microsoft.Template";
export const AZURE_PORTAL_GUIDE_URL = "https://learn.microsoft.com/azure/azure-resource-manager/templates/quickstart-create-templates-use-the-portal#edit-and-deploy-the-template";
export type DeploymentParameter = { name: string; type: string; required: boolean; description: string };
export type DeploymentHandoff = { template: BuildFile; parameters: BuildFile; fields: DeploymentParameter[] };
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
async function verifiedJson(file: BuildFile): Promise<unknown> {
  const bytes = new TextEncoder().encode(file.content);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const hash = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  if (hash !== file.sha256.toLowerCase()) throw new Error(`${file.path} failed its recorded SHA-256 check. Regenerate the package before using this handoff.`);
  try { return JSON.parse(file.content) as unknown; }
  catch { throw new Error(`${file.path} is not valid JSON. Regenerate the package.`); }
}

export async function prepareDeploymentHandoff(build: BuildResult): Promise<DeploymentHandoff> {
  if (build.status !== "compiled" || build.exitCode !== 0 || !build.compilerVersion || !build.downloadUrl) {
    throw new Error("A successful compiler receipt is required before preparing an Azure deployment handoff.");
  }
  const template = build.files.find((file) => file.path === "main.json");
  const parameters = build.files.find((file) => file.path === "main.parameters.json");
  if (!template || !parameters) throw new Error("The compiled ARM template or parameter file is missing.");
  const [arm, values] = await Promise.all([verifiedJson(template), verifiedJson(parameters)]);
  if (!record(arm) || typeof arm.$schema !== "string" || !arm.$schema.includes("/deploymentTemplate.json#")
    || !(Array.isArray(arm.resources) ? arm.resources.length : record(arm.resources) && Object.keys(arm.resources).length)
    || !record(arm.parameters) || !record(values) || !record(values.parameters)) {
    throw new Error("The generated files are not a resource-group ARM template and parameter document.");
  }
  const fields = Object.entries(arm.parameters).map(([name, definition]) => {
    if (!record(definition) || typeof definition.type !== "string") throw new Error(`Parameter ${name} has an invalid definition.`);
    return { name, type: definition.type, required: !Object.hasOwn(definition, "defaultValue"),
      description: record(definition.metadata) && typeof definition.metadata.description === "string" ? definition.metadata.description : "" };
  });
  return { template, parameters, fields };
}
