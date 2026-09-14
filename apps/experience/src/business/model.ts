export type Step = "intent" | "understanding" | "architecture" | "assessment" | "handoff";
export type ReviewStatus = "not-reviewed" | "needs-work" | "reviewed";

export interface SourceDocument {
  id: string;
  name: string;
  text: string;
  bytes: number;
}

export interface BusinessBrief {
  goal: string;
  actors: string;
  process: string;
  systems: string;
  constraints: string;
}

export interface Clarification {
  id: "scale" | "recovery" | "budget" | "ownership";
  question: string;
  reason: string;
  answer: string;
}

export interface ReviewDimension {
  id: string;
  title: string;
  question: string;
  finding: string;
  recommendation: string;
  sourceIds: string[];
}

export interface ReviewNote {
  status: ReviewStatus;
  note: string;
}

export interface ArchitectureNode {
  id: string;
  title: string;
  service: string;
  responsibility: string;
}

export interface ArchitectureOption {
  id: string;
  title: string;
  subtitle: string;
  fit: string;
  tradeoff: string;
  costDriver: string;
  nodes: ArchitectureNode[];
  flows: { from: string; to: string; label: string }[];
}

export interface DesignDraft {
  version: 1;
  id: string;
  updatedAt: string;
  kind: "custom" | "example";
  title: string;
  prompt: string;
  documents: SourceDocument[];
  brief: BusinessBrief;
  questions: Clarification[];
  selectedOptionId: string | null;
  designRationale: string;
  reviews: Record<string, ReviewNote>;
}

export const STEPS: { id: Step; number: string; title: string; description: string }[] = [
  { id: "intent", number: "01", title: "Your business", description: "Start with the problem" },
  { id: "understanding", number: "02", title: "Understanding", description: "Make the brief yours" },
  { id: "architecture", number: "03", title: "Architecture", description: "Explore the trade-offs" },
  { id: "assessment", number: "04", title: "360 review", description: "Challenge the design" },
  { id: "handoff", number: "05", title: "Design brief", description: "Take the work forward" },
];

export const DIMENSIONS: ReviewDimension[] = [
  { id: "business", title: "Business fit", question: "Does every important process step have an owner and a system responsibility?", finding: "An accepted order is not a fulfilled order. A durable order state is needed across payment, stock and dispatch.", recommendation: "Make the order lifecycle explicit; show customers the current stage and give support staff a recovery path.", sourceIds: ["example-process"] },
  { id: "security", title: "Security & privacy", question: "Who can access what, and where does sensitive data cross a boundary?", finding: "Customer contact details and payment references cross the storefront, payment provider and fulfilment system.", recommendation: "Keep card data with the payment provider. Use scoped identities, secret management and separate customer/operator permissions.", sourceIds: ["example-process", "example-requirements"] },
  { id: "reliability", title: "Reliability & recovery", question: "What happens when a dependency fails or the same event arrives twice?", finding: "The warehouse can be unavailable while orders arrive. The example workshop proposes a 60-minute recovery time and 15-minute recovery point; neither has been demonstrated.", recommendation: "Buffer fulfilment work, use idempotency keys and a dead-letter recovery workflow. Validate the proposed recovery targets with failure and restore tests.", sourceIds: ["example-process", "example-clarifications"] },
  { id: "performance", title: "Performance & scale", question: "Where are latency and throughput targets needed?", finding: "The example assumes 2,000 orders per day and campaign bursts of 50 submissions per second. These are planning inputs, not measured demand.", recommendation: "Keep acknowledgement separate from fulfilment. Load-test the assumed burst and dependency limits before capacity sizing.", sourceIds: ["example-requirements", "example-clarifications"] },
  { id: "cost", title: "Cost & efficiency", question: "Which usage assumptions dominate cost, and what budget has been agreed?", finding: "The example workshop sets a USD 1,500 monthly planning budget. Execution volume, messaging, database operations and telemetry are cost drivers. No price estimate has been calculated.", recommendation: "Price each viable option against the assumed workload and budget using current regional rates. Include support effort; budget is not an estimated bill.", sourceIds: ["example-clarifications"] },
  { id: "integration", title: "Integration & data", question: "Are ownership, contracts and consistency defined between systems?", finding: "Stock remains owned by the existing ERP. Warehouse updates occur asynchronously.", recommendation: "Version event contracts, reconcile stock and order state, and define compensation for a payment accepted when inventory changes.", sourceIds: ["example-process"] },
  { id: "compliance", title: "Compliance & governance", question: "Which data residency, retention and audit obligations actually apply?", finding: "EU customer-data residency is stated. Retention and deletion periods have not been specified.", recommendation: "Confirm jurisdiction, retention and deletion requirements with the appropriate owner. A design review is not compliance certification.", sourceIds: ["example-requirements"] },
  { id: "operations", title: "Operations & observability", question: "Can the team detect, investigate and recover failed business transactions?", finding: "Support needs customer-visible order status. The example names fulfilment operations as the process owner and the integration team as the ERP interface owner.", recommendation: "Trace by order ID, monitor stuck orders and queue age, and agree replay/reconciliation runbooks with the named teams.", sourceIds: ["example-process", "example-clarifications"] },
  { id: "delivery", title: "Delivery & evolution", question: "Can this be delivered safely by the team and changed without a big-bang migration?", finding: "The ERP must remain in place. The example proposes a pilot in 12 weeks; team capacity and release constraints still need validation.", recommendation: "Start with one order flow, test contracts with the ERP, and use a staged rollout with a rollback plan.", sourceIds: ["example-process", "example-clarifications"] },
];

export const OPTIONS: ArchitectureOption[] = [
  {
    id: "event-driven",
    title: "Event-driven services",
    subtitle: "Separate a fast response from reliable fulfilment",
    fit: "A useful starting pattern for bursty traffic and dependencies that may be temporarily unavailable.",
    tradeoff: "Asynchronous state, retries and compensation need explicit design. More moving parts than a single application.",
    costDriver: "Usage-based compute, messaging, persistence and observability. Not priced or sized.",
    nodes: [
      { id: "experience", title: "Customer experience", service: "Web application", responsibility: "Capture requests and show progress." },
      { id: "api", title: "Business API", service: "API Management + Functions", responsibility: "Authenticate, validate and acknowledge commands." },
      { id: "data", title: "Business state", service: "Azure SQL", responsibility: "Own transaction state and idempotency records." },
      { id: "queue", title: "Durable work", service: "Service Bus", responsibility: "Buffer work, retry and isolate downstream failure." },
      { id: "worker", title: "Process workers", service: "Functions", responsibility: "Execute steps and publish outcomes." },
      { id: "external", title: "Existing systems", service: "ERP / external APIs", responsibility: "Retain their existing business ownership." },
    ],
    flows: [
      { from: "experience", to: "api", label: "Submit and query" }, { from: "api", to: "data", label: "Persist command" },
      { from: "data", to: "queue", label: "Transactional outbox" }, { from: "queue", to: "worker", label: "Deliver work" },
      { from: "worker", to: "external", label: "Integrate / reconcile" }, { from: "worker", to: "data", label: "Record outcome" },
    ],
  },
  {
    id: "modular-app",
    title: "Modular application",
    subtitle: "Start cohesive; split only when the need is clear",
    fit: "A useful starting pattern for a small team, modest scale and closely related business capabilities.",
    tradeoff: "Shared deployment and scaling boundaries. Background work still needs retries and recovery.",
    costDriver: "Provisioned application capacity, database, background jobs and support. Not priced or sized.",
    nodes: [
      { id: "experience", title: "Customer experience", service: "Web application", responsibility: "Capture requests and show progress." },
      { id: "api", title: "Business modules", service: "App Service", responsibility: "Keep business capabilities separate within one deployable application." },
      { id: "data", title: "Business state", service: "Azure SQL", responsibility: "Persist transactions and the outbox." },
      { id: "queue", title: "Work queue", service: "Service Bus", responsibility: "Decouple slow external work." },
      { id: "worker", title: "Background processor", service: "Worker service", responsibility: "Run integrations and recover failures." },
      { id: "external", title: "Existing systems", service: "ERP / external APIs", responsibility: "Own external records and return outcomes." },
    ],
    flows: [
      { from: "experience", to: "api", label: "Request / response" }, { from: "api", to: "data", label: "Commit state" },
      { from: "data", to: "queue", label: "Transactional outbox" }, { from: "queue", to: "worker", label: "Background work" },
      { from: "worker", to: "external", label: "Integrate / reconcile" }, { from: "worker", to: "data", label: "Record outcome" },
    ],
  },
  {
    id: "workflow-led",
    title: "Integration-led workflows",
    subtitle: "Make cross-system coordination visible",
    fit: "A useful starting pattern for connector-heavy processes and explicit orchestration between existing systems.",
    tradeoff: "Connector limits, workflow versioning and complex business logic need careful boundaries.",
    costDriver: "Workflow actions, connector tiers, API calls and persisted state. Not priced or sized.",
    nodes: [
      { id: "experience", title: "Customer experience", service: "Web application", responsibility: "Capture requests and show progress." },
      { id: "api", title: "Process entry", service: "API Management", responsibility: "Authenticate and control access." },
      { id: "data", title: "Business state", service: "Azure SQL", responsibility: "Store process and transaction history." },
      { id: "queue", title: "Durable ingress", service: "Service Bus", responsibility: "Accept work independently of connector availability." },
      { id: "worker", title: "Process orchestration", service: "Logic Apps", responsibility: "Coordinate connector calls and recovery branches." },
      { id: "external", title: "Existing systems", service: "ERP / external APIs", responsibility: "Expose agreed integration contracts." },
    ],
    flows: [
      { from: "experience", to: "api", label: "Submit process" }, { from: "api", to: "queue", label: "Accept work" },
      { from: "queue", to: "worker", label: "Start workflow" }, { from: "worker", to: "external", label: "Connector / API" },
      { from: "worker", to: "data", label: "Record outcome" }, { from: "experience", to: "api", label: "Query progress" },
    ],
  },
];

export const QUESTIONS: Omit<Clarification, "answer">[] = [
  { id: "scale", question: "What normal and peak volumes should the design support?", reason: "Sizing and cost depend on measured demand, not a generic architecture." },
  { id: "recovery", question: "How much downtime and data loss can the business tolerate?", reason: "Recovery objectives change redundancy, replication and operating cost." },
  { id: "budget", question: "What is the monthly budget and intended delivery date?", reason: "Compare viable options against real financial and delivery constraints." },
  { id: "ownership", question: "Who owns integrations, sensitive data and day-to-day support?", reason: "An architecture needs accountable owners and clear trust boundaries." },
];

export const EXAMPLE_PROMPT = "Help us redesign our order-to-fulfilment process. Customers need an immediate order acknowledgement and reliable status updates, even when the warehouse is offline. Keep our existing ERP and payment provider. We need an architecture we can deliver incrementally, with a clear view of risks and trade-offs.";

export const EXAMPLE_ANSWERS: Record<Clarification["id"], string> = {
  scale: "Plan for 2,000 orders per day and campaign bursts of 50 order submissions per second. These are illustrative workload assumptions; validate them against traffic measurements and load tests before sizing.",
  recovery: "Use an illustrative recovery time objective (RTO) of 60 minutes and recovery point objective (RPO) of 15 minutes. Continue accepting orders during warehouse outages. Confirm the targets with the business and prove recovery through testing.",
  budget: "Use USD 1,500 per month as an illustrative planning budget and aim for a pilot in 12 weeks. This is a sample budget, not a calculated Azure estimate or a delivery commitment; pricing and team capacity still need validation.",
  ownership: "Fulfilment operations owns the process and stuck-order recovery. The integration team owns ERP and warehouse interfaces. The payment provider owns card data; customer support receives scoped order access. The privacy owner confirms retention and EU residency controls.",
};

export const EXAMPLE_DOCUMENTS: SourceDocument[] = [
  {
    id: "example-process", name: "Order fulfilment - business process.md", bytes: 0,
    text: "# Order-to-fulfilment process\n\nCustomers submit an order through the storefront. The payment provider handles card details and sends a payment reference and callback. The existing ERP owns stock availability. The warehouse receives fulfilment requests and returns dispatch updates asynchronously.\n\nThe ERP, payment provider and warehouse are existing integrations that must be retained; they are not new Azure resources to provision.\n\nPayment callbacks can be retried. The warehouse may be unavailable while orders continue to arrive. Support staff need to find stuck orders and explain the current order status to customers. The ERP will remain in place during migration.",
  },
  {
    id: "example-requirements", name: "Operating requirements.md", bytes: 0,
    text: "# Operating requirements\n\nEU customer contact data must remain in approved EU regions. Store payment references, not card details. Campaign traffic is bursty; peak orders per minute have not been measured.\n\nProvide an immediate acknowledgement and subsequent order-status updates. Monitor stuck orders and give support staff a recovery process. Monthly budget, recovery time, recovery point, retention periods and team capacity are not yet confirmed.",
  },
  {
    id: "example-clarifications", name: "Example clarification workshop.md", bytes: 0,
    text: "# Illustrative clarification workshop\n\nThese authored sample answers extend the initially incomplete operating requirements. They demonstrate a completed clarification step, not AI extraction, real customer confirmation or validated targets.\n\n"
      + QUESTIONS.map((question) => `## ${question.question}\n\n${EXAMPLE_ANSWERS[question.id]}`).join("\n\n"),
  },
];
