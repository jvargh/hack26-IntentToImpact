import type {
  AuthorizationContext,
  CaseState,
  CommandExecutionReceipt,
  CoreContract,
  DomainEvent,
  ErrorEnvelope,
  ExecutionActor,
  EvidenceReference,
  LocalRunManifest,
  WorkEnvelope,
} from "../../contracts/generated/1.0.0/typescript/core";

declare const run: LocalRunManifest;
declare const auth: AuthorizationContext;
declare const caseState: CaseState;
declare const receipt: CommandExecutionReceipt;
declare const event: DomainEvent;
declare const error: ErrorEnvelope;
declare const evidence: EvidenceReference;
declare const work: WorkEnvelope;

const roots: CoreContract[] = [run, auth, caseState, receipt, event, error, evidence, work];

function describe(value: CoreContract): string {
  switch (value.artifactType) {
    case "local-run-manifest":
      return `${value.runMode}/${value.purpose}/${value.scenarioHash}`;
    case "case-state":
      return `${value.lifecycleState}/${value.logicalRevision}/${value.events.length}`;
    case "evidence-reference":
      return `${value.origin}/${value.evidenceState}`;
    case "command-execution-receipt":
      return `${value.exitCode}/${value.stdoutChecksum}`;
    case "work-envelope":
      return `${value.status}/${value.attempt}`;
    case "domain-event":
      return `${value.eventType}/${value.sequence}`;
    case "error-envelope":
      return `${value.code}/${value.retryable}`;
    case "authorization-context":
      return `${value.caller.callerClass}/${value.caller.channel}/${value.caller.actor.actorId}`;
    default: {
      const unreachable: never = value;
      return unreachable;
    }
  }
}

roots.map(describe);

const modelCaller: AuthorizationContext["caller"] = {
  callerClass: "agent",
  channel: "model",
  actor: { kind: "agent", actorId: "AGENT-EXAMPLE" },
};
const operatorInitiatedModel: AuthorizationContext = {
  ...auth,
  caller: modelCaller,
  humanInitiator: { actorId: "demo-human", identityAssurance: "local-demo" },
};
const automaticEvent: DomainEvent = {
  ...event,
  actor: { kind: "system", actorId: "SYSTEM-OBSERVER" },
};
const preContextError: ErrorEnvelope = {
  schemaVersion: "1.0.0",
  artifactType: "error-envelope",
  createdAt: "2026-09-12T17:00:00Z",
  code: "invalid-artifact",
  message: "Create a valid run before creating a case.",
  diagnosticId: "DIAGNOSTIC-EXAMPLE",
  correlationId: "CORRELATION-EXAMPLE",
  retryable: false,
  allowedRecoveryActions: ["create-run"],
};

function executorLabel(actor: ExecutionActor): string {
  switch (actor.kind) {
    case "human": {
      const fixedHuman: "demo-human" = actor.actorId;
      return fixedHuman;
    }
    case "agent":
    case "system":
      return `${actor.kind}/${actor.actorId}`;
    default: {
      const unreachable: never = actor;
      return unreachable;
    }
  }
}
executorLabel(automaticEvent.actor);
describe(operatorInitiatedModel);
describe(preContextError);

// @ts-expect-error Invalid modes must not become unrestricted strings.
const invalidMode: LocalRunManifest = { ...run, runMode: "demo" };
// @ts-expect-error No other human identity is representable.
const invalidActor: ExecutionActor = { kind: "human", actorId: "admin", identityAssurance: "local-demo" };
// @ts-expect-error An agent cannot claim human assurance.
const verifiedAgent: ExecutionActor = { kind: "agent", actorId: "AGENT-EXAMPLE", identityAssurance: "entra-verified" };
// @ts-expect-error Model channel cannot masquerade as a human caller.
const confusedCaller: AuthorizationContext["caller"] = { ...modelCaller, callerClass: "human" };
const { diagnosticId, ...withoutDiagnostic } = preContextError;
// @ts-expect-error Pre-context errors still require a diagnostic identifier.
const missingDiagnostic: ErrorEnvelope = withoutDiagnostic;
// @ts-expect-error Origin and freshness are distinct contracts.
const invalidOrigin: EvidenceReference = { ...evidence, origin: "fresh" };
// @ts-expect-error Required envelope metadata cannot be omitted.
const missingMetadata: LocalRunManifest = { artifactType: "local-run-manifest", runMode: "fixture" };
// @ts-expect-error Only D01 owns logicalRevision.
const nonCaseRevision: WorkEnvelope = { ...work, logicalRevision: 1 };
// @ts-expect-error Source timestamps are JSON strings, not Date objects.
const nonJsonTime: DomainEvent = { ...event, createdAt: new Date() };
