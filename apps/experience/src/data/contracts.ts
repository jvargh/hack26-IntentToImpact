import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import coreSchema from "../../../../contracts/schemas/1.0.0/core.schema.json";
import scenarioSchema from "../../../../contracts/schemas/1.0.0/scenario.schema.json";
import riskSchema from "../../../../contracts/schemas/1.0.0/risk.schema.json";
import projectionSchema from "../../../../contracts/schemas/1.0.0/projections.schema.json";
import type { EvidenceReference, LocalRunManifest } from "@contracts/core";
import type { RiskContract } from "@contracts/risk";
import type { ArtifactLink, ExperienceOverview, RiskProjectionContract } from "@contracts/projections";

export type FixtureRecord = EvidenceReference | RiskContract | RiskProjectionContract;

// Synchronous local schema registry only; there is no remote schema loader.
const ajv = new Ajv2020({ strict: false, allErrors: true });
addFormats(ajv);
ajv.addSchema(coreSchema, "https://intent-to-impact.invalid/contracts/1.0.0/core.schema.json");
ajv.addSchema(scenarioSchema);
ajv.addSchema(riskSchema);
ajv.addSchema(projectionSchema);

export const isOverview = ajv.compile<ExperienceOverview>({
  $ref: `${projectionSchema.$id}#/definitions/ExperienceOverview`,
});
export const isRun = ajv.compile<LocalRunManifest>({
  $ref: `${coreSchema.$id}#/definitions/LocalRunManifest`,
});
export const isArtifactLink = ajv.compile<ArtifactLink>({
  $ref: `${riskSchema.$id}#/definitions/ArtifactLink`,
});
const isEvidence = ajv.compile<EvidenceReference>({
  $ref: `${coreSchema.$id}#/definitions/EvidenceReference`,
});
const isRisk = ajv.compile<RiskContract>({ $ref: riskSchema.$id });
const isProjection = ajv.compile<RiskProjectionContract>({ $ref: projectionSchema.$id });

export function isFixtureRecord(value: unknown): value is FixtureRecord {
  return isEvidence(value) || isRisk(value) || isProjection(value);
}

export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
