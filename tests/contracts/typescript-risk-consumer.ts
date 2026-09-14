import type { CommonEnvelope as CoreEnvelope } from "../../contracts/generated/1.0.0/typescript/core";
import type {
  CommonEnvelope as ExpandedCoreEnvelope,
  CustomerPromiseContract,
  SandboxOperationReceipt,
  RuntimeBinding,
  RuntimeSnapshot,
  DriftFinding,
  PromiseEvaluation,
  HumanAttentionEvent,
  EvidenceLink,
} from "../../contracts/generated/1.0.0/typescript/risk";
import type {
  ExperienceOverview,
  OperationsRisk,
  IntentContinuityGraph,
} from "../../contracts/generated/1.0.0/typescript/projections";
import type { ClaimsScenarioV2 } from "../../contracts/generated/1.0.0/typescript/scenario";

type Expect<T extends true> = T;
type IsAny<T> = 0 extends (1 & T) ? true : false;
type RequiredMetadata<T extends CoreEnvelope> =
  { [K in keyof CoreEnvelope]-?: {} extends Pick<T, K> ? false : IsAny<T[K]> extends true ? false : true }[keyof CoreEnvelope] extends true
    ? true
    : false;

type RequiredInheritedMetadata = [
  Expect<RequiredMetadata<CustomerPromiseContract>>,
  Expect<RequiredMetadata<SandboxOperationReceipt>>,
  Expect<RequiredMetadata<RuntimeBinding>>,
  Expect<RequiredMetadata<RuntimeSnapshot>>,
  Expect<RequiredMetadata<DriftFinding>>,
  Expect<RequiredMetadata<PromiseEvaluation>>,
  Expect<RequiredMetadata<HumanAttentionEvent>>,
  Expect<RequiredMetadata<ExperienceOverview>>,
  Expect<RequiredMetadata<OperationsRisk>>,
  Expect<RequiredMetadata<IntentContinuityGraph>>,
];

declare const original: CoreEnvelope;
declare const expanded: ExpandedCoreEnvelope;
const sameCoreShape: ExpandedCoreEnvelope = original;
const reverseCoreShape: CoreEnvelope = expanded;
declare const snapshot: RuntimeSnapshot;
declare const overview: ExperienceOverview;
declare const operations: OperationsRisk;
declare const attention: HumanAttentionEvent;
declare const scenario: ClaimsScenarioV2;
declare const evidence: EvidenceLink;
const snapshotContext: CoreEnvelope = snapshot;
const experienceContext: CoreEnvelope = overview;
const https: boolean | null | undefined = snapshot.observations[0]?.properties.supportsHttpsTrafficOnly;
const initialRpo: null = scenario.rpoMinutes;
const scriptedAnswer: 15 = scenario.scriptedRpoAnswerMinutes;
const overviewActionId: HumanAttentionEvent["actionId"] = overview.allowedActions[0].actionId;
const operationsActionId: HumanAttentionEvent["actionId"] = operations.allowedActions[0].actionId;
const issuedActionAttention: HumanAttentionEvent = { ...attention, actionId: overview.allowedActions[0].actionId };

declare const noMetadata: Omit<RuntimeSnapshot, keyof CoreEnvelope>;
// @ts-expect-error Runtime metadata is required, not just named in a comment.
const missingMetadata: RuntimeSnapshot = noMetadata;
const { runId, ...withoutRunId } = snapshot;
// @ts-expect-error A single missing inherited run ID is also rejected.
const missingRunId: RuntimeSnapshot = withoutRunId;
// @ts-expect-error Fixture/live origin is an explicit enum, not an arbitrary mode string.
const unsupportedOrigin: EvidenceLink = { ...evidence, origin: "live" };
// @ts-expect-error An agent execution is not actual human attention.
const automaticAttention: HumanAttentionEvent = { ...attention, actor: { ...attention.actor, kind: "agent" } };
// @ts-expect-error The V2 desired property cannot silently become the V1 private-network requirement.
const wrongDesired: ClaimsScenarioV2["desiredStorageConfiguration"] = { ...scenario.desiredStorageConfiguration, publicNetworkAccess: "Disabled" };
// @ts-expect-error No automatic RPO answer is embedded in the canonical scenario.
const answeredRpo: ClaimsScenarioV2 = { ...scenario, rpoMinutes: 15 };
