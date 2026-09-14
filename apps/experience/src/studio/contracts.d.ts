/* Generated from apps/control-plane/studio/studio.schema.json. Do not edit. */

/**
 * Live architecture proposal transport, not product approval or deployed-state evidence.
 */
export type StudioContract =
  AnalysisRequest | ArchitectureAnalysis | StudioJob | BuildRequest | BuildResult | RunHistory | SavedRun;
export type AnalysisRequest = {
  title: string;
  prompt: string;
  documents: Documents;
  refinement: string;
  previousResultId: string | null;
  idempotencyKey: string;
  consentToModel: true;
  designChange?: DesignChange;
};
/**
 * @maxItems 5
 */
export type Documents = SourceDocument[];

export interface SourceDocument {
  id: string;
  name: string;
  text: string;
}
/**
 * Explicit permission to revise a particular stored design finding, never risk acceptance.
 */
export interface DesignChange {
  optionId: string;
  finding: ReviewFinding;
  intent: "recommendation" | "challenge";
  confirmRevision: true;
}
export interface ReviewFinding {
  dimension:
    | "business"
    | "security"
    | "reliability"
    | "performance"
    | "cost"
    | "integration"
    | "compliance"
    | "operations"
    | "delivery";
  severity: "info" | "warning" | "blocker";
  finding: string;
  recommendation: string;
  /**
   * @minItems 1
   * @maxItems 6
   */
  sourceIds: string[];
}
export interface ArchitectureAnalysis {
  title: string;
  summary: string;
  /**
   * @minItems 2
   * @maxItems 10
   */
  businessProcess: string[];
  /**
   * @minItems 2
   * @maxItems 16
   */
  requirements: Requirement[];
  /**
   * @maxItems 10
   */
  assumptions: string[];
  /**
   * @maxItems 6
   */
  questions: Question[];
  /**
   * @minItems 2
   * @maxItems 3
   */
  options: ArchitectureOption[];
  recommendedOptionId: string;
  /**
   * @minItems 9
   * @maxItems 9
   */
  review: ReviewFinding[];
  changeSummary: string;
}
export interface Requirement {
  id: string;
  text: string;
  /**
   * @minItems 1
   * @maxItems 6
   */
  sourceIds: string[];
}
export interface Question {
  id: string;
  question: string;
  why: string;
}
export interface ArchitectureOption {
  id: string;
  name: string;
  rationale: string;
  /**
   * @minItems 1
   * @maxItems 6
   */
  tradeoffs: string[];
  costNotes: string;
  /**
   * @minItems 2
   * @maxItems 12
   */
  components: Component[];
  /**
   * @minItems 1
   * @maxItems 20
   */
  connections: Connection[];
}
export interface Component {
  id: string;
  label: string;
  kind: "appservice" | "functions" | "storage" | "servicebus" | "keyvault" | "external" | "client";
  service: string;
  responsibility: string;
  /**
   * @minItems 1
   * @maxItems 20
   */
  requirementIds: string[];
  externalDependency?: ExternalDependency | null;
}
/**
 * Named existing integration, distinct from its technical service type, with a literal source quotation.
 */
export interface ExternalDependency {
  name: string;
  sourceId: string;
  quote: string;
}
export interface Connection {
  id: string;
  source: string;
  target: string;
  label: string;
}
export interface StudioJob {
  jobId: string;
  status: "queued" | "running" | "succeeded" | "failed";
  events: StudioEvent[];
  result: StudioResult | null;
  error: StudioError | null;
  changeApproval?: ChangeApproval;
}
export interface StudioEvent {
  sequence: number;
  stage: "intake" | "synthesis" | "assurance" | "complete" | "error";
  message: string;
  at: string;
}
export interface StudioResult {
  resultId: string;
  inputHash: string;
  createdAt: string;
  origin: "live-model";
  analysis: ArchitectureAnalysis;
  /**
   * @minItems 2
   * @maxItems 2
   */
  modelReceipts: ModelReceipt[];
  sources: {
    id: string;
    name: string;
  }[];
}
export interface ModelReceipt {
  role: "synthesis" | "assurance";
  model: string;
  responseId: string;
  durationMs: number;
}
export interface StudioError {
  code: string;
  message: string;
  retryable: boolean;
}
/**
 * Server-bound demo-human authorization to generate and independently review a revision; not sign-off of its result.
 */
export interface ChangeApproval {
  baseResultId: string;
  baseResultHash: string;
  optionId: string;
  finding: ReviewFinding;
  intent: "recommendation" | "challenge";
  instruction: string;
  refinement: string;
  approvedAt: string;
  actor: "demo-human";
  scope: "design-revision-only";
}
export interface BuildRequest {
  resultId: string;
  optionId: string;
  confirmGeneration: true;
  idempotencyKey: string;
}
export interface BuildResult {
  buildId: string;
  resultId: string;
  optionId: string;
  status: "compiled" | "failed" | "blocked";
  compilerVersion: string | null;
  exitCode: number | null;
  diagnostics: string;
  files: BuildFile[];
  downloadUrl: string | null;
  limitations: string[];
  deploymentStatus: "not-deployed";
}
export interface BuildFile {
  path: string;
  content: string;
  sha256: string;
}
export interface RunHistory {
  scope: "session" | "workspace";
  /**
   * @maxItems 64
   */
  runs: RunSummary[];
}
export interface RunSummary {
  jobId: string;
  title: string;
  status: "queued" | "running" | "succeeded" | "failed";
  createdAt: string;
  updatedAt: string;
  documentCount: number;
  resultId: string | null;
  previousResultId: string | null;
  compiledPackageCount: number;
  error: StudioError | null;
}
export interface SavedRun {
  scope: "session" | "workspace";
  summary: RunSummary;
  inputs: SavedInputs;
  job: StudioJob;
  /**
   * @maxItems 64
   */
  builds: SavedBuild[];
}
export interface SavedInputs {
  title: string;
  prompt: string;
  documents: Documents;
  refinement: string;
  previousResultId: string | null;
}
export interface SavedBuild {
  buildId: string;
  resultId: string;
  optionId: string;
  status: "compiled" | "failed" | "blocked";
  compilerVersion: string | null;
  exitCode: number | null;
}
