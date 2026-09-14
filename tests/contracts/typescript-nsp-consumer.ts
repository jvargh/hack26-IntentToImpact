import type { CommonEnvelope as LegacyEnvelope, Scope } from "../../contracts/generated/1.0.0/typescript/core";
import type { RuntimeSnapshot as LegacySnapshot } from "../../contracts/generated/1.0.0/typescript/risk";
import type { RuntimeSnapshot, RuntimeBinding, PromiseEvaluation, CustomerPromiseContract, SandboxOperationReceipt, DriftFinding } from "../../contracts/generated/2.0.0/typescript/risk";
import type { Requirements, ArchitectureProposal, ArchitectureModel, ArchitectureDecisionRecord, Approval, ReviewGateEvaluation, GenerationContract } from "../../contracts/generated/2.0.0/typescript/design";
import type { ExperienceOverview, OperationsRisk, IntentContinuityGraph } from "../../contracts/generated/2.0.0/typescript/projections";
import type { ClaimsScenarioV3 } from "../../contracts/generated/2.0.0/typescript/scenario";
import type { RuleCollection } from "../../contracts/generated/2.0.0/typescript/nsp";

type Expect<T extends true> = T;
type IsAny<T> = 0 extends (1 & T) ? true : false;
type RequiredV2<T extends Record<keyof LegacyEnvelope, unknown>> =
  { [K in keyof LegacyEnvelope]-?: {} extends Pick<T, K> ? false : IsAny<T[K]> extends true ? false : true }[keyof LegacyEnvelope] extends true
    ? T["schemaVersion"] extends "2.0.0" ? true : false
    : false;
type RequiredRoots = [
  Expect<RequiredV2<CustomerPromiseContract>>, Expect<RequiredV2<SandboxOperationReceipt>>,
  Expect<RequiredV2<RuntimeBinding>>, Expect<RequiredV2<RuntimeSnapshot>>, Expect<RequiredV2<DriftFinding>>,
  Expect<RequiredV2<PromiseEvaluation>>, Expect<RequiredV2<Requirements>>, Expect<RequiredV2<ArchitectureProposal>>,
  Expect<RequiredV2<ArchitectureModel>>, Expect<RequiredV2<ArchitectureDecisionRecord>>, Expect<RequiredV2<Approval>>,
  Expect<RequiredV2<ReviewGateEvaluation>>, Expect<RequiredV2<GenerationContract>>,
  Expect<RequiredV2<ExperienceOverview>>, Expect<RequiredV2<OperationsRisk>>, Expect<RequiredV2<IntentContinuityGraph>>,
];
declare const snapshot: RuntimeSnapshot;
declare const scenario: ClaimsScenarioV3;
declare const rules: RuleCollection;
const sameScopePrimitive: Scope = snapshot.scope;
const schemaVersion: "2.0.0" = scenario.schemaVersion;
const scenarioVersion: "3.0.0" = scenario.scenarioVersion;
const secured: "SecuredByPerimeter" = scenario.desiredStorageConfiguration.publicNetworkAccess;
const explicitUnknown = snapshot.observation.association.value;
const missingRules: RuleCollection["items"] = null;
const knownEmptyRules: RuleCollection["items"] = [];

// @ts-expect-error Versioned metadata prevents accidental legacy assignment.
const legacy: LegacySnapshot = snapshot;
// @ts-expect-error Schema and scenario versions are independent and cannot be interchanged.
const wrongSchema: RuntimeSnapshot = { ...snapshot, schemaVersion: "3.0.0" };
// @ts-expect-error No old public Enabled intent is valid for V3.
const enabled: ClaimsScenarioV3["desiredStorageConfiguration"] = { ...scenario.desiredStorageConfiguration, publicNetworkAccess: "Enabled" };
const { items, ...withoutItems } = rules;
// @ts-expect-error Missing rules cannot silently become a complete empty collection.
const implicitEmpty: RuleCollection = withoutItems;
const { runId, ...withoutRunId } = snapshot;
// @ts-expect-error Inherited metadata remains required.
const missingRunId: RuntimeSnapshot = withoutRunId;
