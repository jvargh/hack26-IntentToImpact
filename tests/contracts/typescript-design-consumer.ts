import type { CommonEnvelope, ChecksumMap } from "../../contracts/generated/1.0.0/typescript/core";
import type { PromiseContractReference } from "../../contracts/generated/1.0.0/typescript/risk";
import type { AllowedAction } from "../../contracts/generated/1.0.0/typescript/projections";
import type {
  Requirements, ArchitectureProposal, ArchitectureModel, ArchitectureDecisionRecord,
  Approval, ReviewGateEvaluation, GenerationContract,
} from "../../contracts/generated/1.0.0/typescript/design";

type Expect<T extends true> = T;
type IsAny<T> = 0 extends (1 & T) ? true : false;
type RequiredMetadata<T extends CommonEnvelope> =
  { [K in keyof CommonEnvelope]-?: {} extends Pick<T, K> ? false : IsAny<T[K]> extends true ? false : true }[keyof CommonEnvelope] extends true
    ? true : false;
type RequiredInheritedMetadata = [
  Expect<RequiredMetadata<Requirements>>,
  Expect<RequiredMetadata<ArchitectureProposal>>,
  Expect<RequiredMetadata<ArchitectureModel>>,
  Expect<RequiredMetadata<ArchitectureDecisionRecord>>,
  Expect<RequiredMetadata<Approval>>,
  Expect<RequiredMetadata<ReviewGateEvaluation>>,
  Expect<RequiredMetadata<GenerationContract>>,
];

declare const requirements: Requirements;
declare const proposal: ArchitectureProposal;
declare const approval: Approval;
declare const review: ReviewGateEvaluation;
declare const plan: GenerationContract;
const rpo: 15 | null = requirements.rpoQuestion.valueMinutes;
const sameD03Reference: PromiseContractReference = proposal.promiseContract;
const sameActionId: AllowedAction["actionId"] = approval.binding.actionId;
const checksumMap: ChecksumMap = approval.binding.boundChecksums;
const namedChecksum: string | undefined = checksumMap["requirements"];
const gateResult = review.gate.effectiveStatus;
const independentApprovalStatus = review.gate.approvalStatus;
const plannedRelativePath: string = plan.outputs[0].relativePath;
const decisionId = approval.decisionId;

declare const withoutContext: Omit<Approval, keyof CommonEnvelope>;
// @ts-expect-error Canonical approval metadata remains required.
const missingContext: Approval = withoutContext;
// @ts-expect-error A proposal cannot carry an approval result.
const proposedApproval: ArchitectureProposal = { ...proposal, approvalStatus: "approved" };
// @ts-expect-error A model/agent is not the local human approver.
const agentApproval: Approval = { ...approval, actor: { kind: "agent", actorId: "AGENT-EXAMPLE" } };
// @ts-expect-error A synthesized proposal must identify its agent producer.
const humanProposal: ArchitectureProposal = { ...proposal, producer: { kind: "human", actorId: "demo-human" } };
// @ts-expect-error Only the six declared gates exist.
const inventedGate: ReviewGateEvaluation["gate"]["gateId"] = "budget-ready";
// @ts-expect-error A runtime verdict is not a design gate status.
const runtimeGate: ReviewGateEvaluation["gate"]["effectiveStatus"] = "verified";
