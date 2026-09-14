import { createHash, webcrypto } from "node:crypto";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ArchitectureOption, BuildFile, BuildResult, ReviewFinding } from "../contracts";
import { AZURE_PORTAL_DEPLOY_URL, prepareDeploymentHandoff } from "../deployment";
import { BuildConsole } from "./BuildConsole";
import { DeploymentPanel } from "./DeploymentPanel";

function file(path: string, value: unknown): BuildFile {
  const content = JSON.stringify(value);
  return { path, content, sha256: createHash("sha256").update(content).digest("hex") };
}
function compiled(): BuildResult {
  return { buildId: "build-portal", resultId: "result-portal", optionId: "option-portal", status: "compiled",
    compilerVersion: "test-compiler", exitCode: 0, diagnostics: "Test fixture only.",
    files: [file("main.json", {
      $schema: "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
      parameters: { entraApplicationClientId: { type: "string", metadata: { description: "Existing Entra client ID." } },
        location: { type: "string", defaultValue: "[resourceGroup().location]" } },
      resources: [{ type: "Microsoft.Web/sites", name: "fixture" }],
    }), file("main.parameters.json", { parameters: {} })],
    downloadUrl: "/api/studio/builds/build-portal/download", limitations: ["Fixture"], deploymentStatus: "not-deployed" };
}
const review: ReviewFinding[] = [{ dimension: "integration", severity: "blocker", finding: "Provider token support is unknown.", recommendation: "Confirm provider support.", sourceIds: ["prompt"] }];
beforeEach(() => { vi.stubGlobal("crypto", webcrypto); });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("Azure Portal deployment handoff", () => {
  it("verifies exact file hashes and lists required parameters without inventing values", async () => {
    const ready = await prepareDeploymentHandoff(compiled());
    expect(ready.fields).toEqual([
      { name: "entraApplicationClientId", type: "string", required: true, description: "Existing Entra client ID." },
      { name: "location", type: "string", required: false, description: "" },
    ]);
    expect(JSON.parse(ready.parameters.content).parameters).toEqual({});
  });

  it.each(["failed", "blocked"] as const)("refuses a %s build", async (status) => {
    await expect(prepareDeploymentHandoff({ ...compiled(), status })).rejects.toThrow("successful compiler receipt");
  });

  it("refuses missing, corrupt and incorrectly shaped ARM files", async () => {
    await expect(prepareDeploymentHandoff({ ...compiled(), files: [] })).rejects.toThrow("missing");
    const tampered = compiled();
    tampered.files[0] = { ...tampered.files[0]!, content: "{}" };
    await expect(prepareDeploymentHandoff(tampered)).rejects.toThrow("SHA-256");
    await expect(prepareDeploymentHandoff({ ...compiled(), files: [file("main.json", { resources: [] }), file("main.parameters.json", { parameters: {} })] })).rejects.toThrow("ARM template");
  });

  it("requires acknowledgement before portal navigation, warns about blockers and makes no network call", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    render(<DeploymentPanel build={compiled()} review={review} onClose={vi.fn()} />);
    await screen.findByText(/SHA-256 checks passed/);
    expect(screen.getByText("1 unresolved design blocker")).toBeVisible();
    expect(screen.getByRole("button", { name: "Open Azure Portal deployment" })).toBeDisabled();
    expect(screen.queryByRole("link", { name: "Open Azure Portal deployment" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /manual handoff/ }));
    const link = screen.getByRole("link", { name: "Open Azure Portal deployment" });
    expect(link).toHaveAttribute("href", AZURE_PORTAL_DEPLOY_URL);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute("target", "_blank");
    expect(fetch).not.toHaveBeenCalled();
    expect(screen.getByText(/remains not-deployed/)).toBeVisible();
  });

  it("downloads the exact verified JSON without uploading it", async () => {
    const create = vi.fn(() => "blob:fixture");
    const revoke = vi.fn();
    vi.stubGlobal("URL", class extends URL { static createObjectURL = create; static revokeObjectURL = revoke; });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<DeploymentPanel build={compiled()} review={[]} onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Download ARM template" }));
    expect(create).toHaveBeenCalledWith(expect.any(Blob));
    expect(click).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/No file has been uploaded to Azure/)).toBeVisible();
  });

  it("shows a validation failure explicitly without a portal action", async () => {
    render(<DeploymentPanel build={{ ...compiled(), files: [] }} review={[]} onClose={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("missing");
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Open Azure Portal deployment" })).not.toBeInTheDocument();
  });

  it("closes the handoff on a stale selection and exposes regeneration separately", async () => {
    const option: ArchitectureOption = { id: "option-portal", name: "Portal option", rationale: "Fixture", tradeoffs: ["Fixture"],
      costNotes: "Fixture", components: [], connections: [] };
    const onBuild = vi.fn();
    const props = { option, resultId: "result-portal", build: compiled(), stale: false, busy: null, onBuild, onDownload: vi.fn(), review };
    const { rerender } = render(<BuildConsole {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Deploy to Azure" }));
    const dialog = await screen.findByRole("dialog", { name: "Deploy to Azure" });
    await within(dialog).findByText(/SHA-256 checks passed/);
    rerender(<BuildConsole {...props} stale />);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Deploy to Azure" })).not.toBeInTheDocument();
    expect(onBuild).not.toHaveBeenCalled();
  });
});
