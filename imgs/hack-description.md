## From business intent to build-ready architecture.

_Explain the customer need once. Carry its context through architecture choices, risk review and a compiler-checked Azure infrastructure package, with humans in control._

Intent-to-Impact Studio reinvents the handoff where business intent too often becomes disconnected diagrams, review comments and implementation assumptions. It connects discovery, architecture review and infrastructure generation in one inspectable workflow, designed to reduce repeated explanations and expose critical gaps before delivery.

A team supplies its business intent and process documents. Microsoft Foundry proposes source-linked architecture alternatives; a separate assurance pass challenges them. People inspect the evidence, challenge findings and authorize revisions. Code validates the output, preserves each decision and compiles the selected design. **The delivery team receives more than a diagram: the reasons behind the design, the risks still unresolved, and the exact infrastructure package to take forward.**

The real-model implementation has been exercised with actual Foundry calls, revisions and compiled downloads. The public ACA judge experience uses disclosed, scripted AI responses with no model calls; validation, revision records, history and Bicep compilation remain real. “Build-ready” means an engineering starting point, not a deployed business application.

**Challenge:** Reinvent Customer Experience Moments That Matter  
**Customer moment:** Turning a business need into an architecture decision and a clear engineering handoff  
**Primary users:** Customer architects, Microsoft account and delivery teams, and implementation partners  
**Repository:** \<https://github.com/jvargh/hack26-IntentToImpact\>  
**Judge experience:** [Open the ACA demo](https://intent2impact-hack26.yellowmeadow-9b9c790a.eastus2.azurecontainerapps.io/)

## 1\. The customer problem: intent gets lost between teams

An architecture engagement often starts with a simple request: “Keep accepting orders when the warehouse is offline, and tell our customers what is happening.”

That request then travels through workshop notes, diagrams, review comments and infrastructure files. Each translation can lose a constraint or turn an assumption into an apparent fact. Customers repeat themselves. Reviewers cannot easily see why a component exists. Engineers inherit a diagram but must reconstruct the decisions behind it.

**Intent-to-Impact reinvents that decision-and-handoff moment.** The customer can ask “Why this design?” and “What still needs work?” in the same place the delivery team asks “Which version should we build from?”

The studio designs the system; it does not itself process orders. Its immediate customer experience is the business-to-engineering handoff.

![Intent-to-Impact concept overview connecting business intent, governed architecture design and the longer-term vision of continuous Azure outcome verification.](/api/events/571ba5dc6cf9/content-images/e887a06b-06a3-43e4-b015-bf96741f22c9.png?scope=project&scopeId=proj-d1619faa-f25e-4e1c-8751-fbf5b013df5d)

_Project vision._ The overview connects customer needs to governed design and engineering action. The implemented experience reaches source-linked designs and compiler-checked infrastructure; continuous assurance, runtime drift detection and verified business outcomes shown in this concept are the next horizon, not delivered capabilities.

## 2\. One connected workflow, not a sequence of disconnected answers

![Stylized Intent-to-Impact experience showing business input, architecture alternatives, an interactive topology and review information in one workspace.](/api/events/571ba5dc6cf9/content-images/1c15ff18-beb5-4464-ab1b-546286ddfe8b.png?scope=project&scopeId=proj-d1619faa-f25e-4e1c-8751-fbf5b013df5d)

_Experience concept._ This illustration shows how a customer brief, architecture choices and review context belong together.

### Step 1: Start with the customer's intent

Describe the business problem, constraints and existing systems; attach TXT or Markdown process documents. In real mode, the system proposes source-linked requirements and explicit unknowns. The original text remains available for inspection.

### Step 2: Compare architectures and understand the choices

Compare service boundaries and trade-offs. Select a component to see its responsibility and linked requirements. Re-layout, expand or zoom the topology, or use the component list. Layout changes affect the view, not the stored design.

### Step 3: Turn review findings into decisions

Assurance covers **business fit, security, reliability, performance, cost, integration, compliance, operations and delivery**.

Real-mode assurance is a separate execution, not synthesis signing off its own response. Both roles use the same model deployment; this is additional scrutiny, not independent certification.

A finding is actionable:

*   **Request recommended change** starts from the suggested correction.
*   **Challenge finding** lets a person explain a disagreement and propose a different direction.

### Step 4: Approve a revision without erasing the evidence

The server binds the approved instruction to the exact parent result, content hash, selected alternative and finding. A new proposal and review are recorded without overwriting the original.

**The approval means “produce and review this revision,” not “this risk is resolved.”** In judge mode, the same decision workflow runs with explicitly scripted changes; arbitrary instructions are recorded, not interpreted by AI.

### Step 5: Produce something the delivery team can use

The selected design is translated through a bounded catalog and compiled with Bicep. An eight-file ZIP includes Bicep, compiled ARM, parameters, catalog, manifest, README, configuration and validation results.

Regeneration creates a distinct build without another model call. History preserves inputs, revisions, approvals, failures and packages.

The **Deploy to Azure** button prepares a manual Azure Portal handoff. It does not automatically provision the generated workload or declare it production-ready.

## 3\. How this differs from existing approaches

The differentiator is the connected workflow, not a claim that architecture chat, diagramming or infrastructure generation is new. Existing approaches solve valuable parts of the problem. Intent-to-Impact brings those parts into one source-linked, versioned path from customer need to delivery artifact.

| Existing approach | What it does well | What Intent-to-Impact connects |
| --- | --- | --- |
| Chat-based architecture assistants | Explore options and explain design choices conversationally | Structured alternatives, source inspection, a separate assurance stage and persisted results that can become build inputs |
| Diagramming tools and reference architectures | Communicate topology and established design patterns | Component responsibilities and requirement links carried from the supplied brief into a selected design and supported infrastructure mappings |
| Manual documents, review checklists and approval threads | Capture expert feedback and organizational decisions | Contextual challenge/change actions, approval bound to the exact result and finding, and a new review without overwriting the original evidence |
| IaC generators and reusable templates | Produce repeatable infrastructure definitions | Business context and unresolved findings alongside fixed catalog generation, actual compiler results, file hashes and downloadable packages |

Individual tools may overlap with these capabilities. The distinction is their integration: a reviewer can move from **“Why does this component exist?”** to **“Change this assumption”** and then **“Build from this version”** without losing the source context or the decision record.

**Customer intent → source-linked architecture → review → human revision request → revised design → compiled package.**

## 4\. The engine behind the experience

![Engine concept showing the canonical schema, React workspace, code-owned control plane, two bounded reasoning roles, human revision loop, deterministic Bicep builder and evidence store.](/api/events/571ba5dc6cf9/content-images/b96d857a-39ca-453a-a1a9-5be0aaaf7a7b.png?scope=project&scopeId=proj-d1619faa-f25e-4e1c-8751-fbf5b013df5d)

_Engine concept._ The illustration explains the separation of authority: models propose, code checks and records, and people direct revisions. The two reasoning roles, canonical contract, builder and saved history are implemented. The runtime-continuity and runtime-evidence areas depict the roadmap. The local boundary shown here is distinct from the public ACA deployment.

The **governed design-to-evidence engine** is a set of cooperating modules with distinct authority:

| Responsibility | Owner | Boundary |
| --- | --- | --- |
| Interpret context, propose alternatives and review trade-offs | Foundry model roles in real mode; authored simulator in judge mode | Proposals, not authoritative approval or execution |
| Sequence work, validate contracts/references and preserve results | Python/FastAPI control plane | Code decides whether an output can enter the workflow |
| Direct consequential revisions | Human through the studio | Permission to revise is recorded against exact prior evidence |
| Render infrastructure and run the compiler | Deterministic catalog and Bicep builder | No arbitrary model-authored Bicep or shell commands |
| Preserve history and make it inspectable | Durable run store and React interface | Saved and simulated results are identified as such |

**Models propose. Code validates and records. People direct the change.**

Microsoft Agent Framework runs two bounded model roles. Application code controls sequencing and persistence. One canonical JSON Schema connects model output, backend validation, browser types and the builder. Source links support inspection; they do not prove every architectural claim or infer component-level impact from a review finding.

Only the two reasoning stages are simulated in judge mode; the surrounding workflow remains executable.

The current catalog supports **App Service, dedicated Functions, Blob Storage, Service Bus and Key Vault**, with existing client/HTTPS integration boundaries. It does not claim arbitrary Azure-service generation.

## 5\. A concrete example of trust being built

The order-fulfilment scenario retains an existing ERP, payment provider and warehouse. Queued work separates immediate acknowledgement from downstream fulfilment, while durable state supports status queries.

A meaningful review concern emerged: the proposed callback ingress assumed that external providers could present a same-tenant Entra bearer token. The documents established callbacks, but not that authentication capability.

The studio exposed the mismatch before implementation. A human could request a revised design and inspect the new review. Adding an adapter responsibility did not automatically clear the blocker: provider capability, callback verification and replay protection still needed evidence and code.

**That is the customer value: expose the difficult assumption early, preserve the decision, and carry the remaining work into delivery.** A successful compilation cannot silently turn that unresolved issue into release approval.

## 6\. Why this fits the challenge and the Frontier ambition

The challenge asks teams to remove friction and move beyond an assistant that only answers questions. Intent-to-Impact advances that pattern:

*   **The human sets direction:** business outcomes, evidence, constraints and revision instructions.
*   **Specialist reasoning performs defined work:** synthesis and a separate assurance pass in real mode.
*   **The system carries the process forward:** validation, review sequencing, versioning, compilation and evidence capture.
*   **The human remains accountable:** change instructions, build requests and deployment decisions are explicit.

This is **human-led, agent-operated design work supported by deterministic orchestration**, not an agent autonomously running the customer's deployed business process.

For MCAPS and partners, it connects customer understanding to an actionable Azure handoff. Personalization comes from the supplied process and constraints in real mode, not a generic diagram presented as customer-specific advice.

## 7\. Demonstrated engineering, with clear proof boundaries

| Demonstrated capability | Evidence and qualification |
| --- | --- |
| Real architecture synthesis and separate assurance | Recorded Foundry calls with distinct response IDs in the local real-model workflow |
| Both human-directed revision paths | Real browser-driven recommendation and challenge runs produced new proposals and reviews |
| Infrastructure generation and regeneration | Actual Bicep compilation, distinct build IDs, eight-file ZIP downloads and matching file hashes |
| ACA-hosted judge workflow | Browser-tested example generation, both scripted revision actions, real Linux compilation and downloads, with zero model calls |
| Durable hosted history | A cold stop/start replaced the original replica; the saved simulated run and compiled package were recovered |
| Honest execution modes | Simulation is identified in the banner, results, review, activity, history and package provenance; custom example edits cannot trigger a paid fallback |
| Public-demo isolation | Separate browser sessions cannot read each other's runs; HTTPS, secure cookies, origin/CSRF checks and workload limits remain |

The public ACA site demonstrates the workflow, **not new AI reasoning**. Real-model proof comes from the local implementation; hosted live-model execution was not proven functional and is not used for judging.

Tests and verification procedures are in the repository. Raw run records remain operator-local to avoid publishing sensitive input.

## 8\. Expected impact and how to measure it

The project targets three practical improvements:

1.  **Less repeated discovery:** source context remains attached to the design and its revisions.
2.  **Earlier risk conversations:** reviewers can challenge assumptions before engineers translate them into deployed dependencies.
3.  **A clearer engineering handoff:** the team receives a selected architecture, explicit gaps and compiler-checked infrastructure instead of recreating them from workshop notes.

These are intended benefits, not measured customer savings. A customer pilot should compare:

*   Time from an agreed business brief to the first reviewable architecture/package.
*   Clarification cycles caused by lost or ambiguous requirements.
*   Design issues identified before implementation rather than after deployment.
*   Time to understand and approve a revision with its source context.
*   Engineering effort needed to complete the handoff.

No delivery-time reduction, cost saving or satisfaction improvement is claimed without pilot evidence. The live engine can accept other business briefs within its supported catalog; broader industry coverage needs evaluation, not just a new example.

## 9\. What judges can try

[**Open the ACA judge demo**](https://intent2impact-hack26.yellowmeadow-9b9c790a.eastus2.azurecontainerapps.io/). No sign-in is required.

1.  Select **Load example inputs**, then **Generate architecture**.
2.  Compare the two alternatives. Select a block, open **Inspect**, and follow a requirement through **Sources**.
3.  Open **Assurance**. Try **Request recommended change** or **Challenge finding** and approve the scripted demonstration.
4.  Open **Build**, confirm package generation, and download the compiled ZIP. Regenerate to see a separate build attempt.
5.  Use **Run history** to reopen the saved simulation and its package.

The hosted experience discloses its simulated AI responses and sends no requests to Foundry. It accepts the supplied example and scripted revisions, not arbitrary AI instructions. There is no paid model fallback; Azure hosting and storage still incur costs.

**Availability checked:** 17 September 2026, 15:28 UTC; readiness returned HTTP 200. Recheck before judging; this is not a new end-to-end test. Use fictional data only.

## 10\. Delivered now; deliberately next

**Delivered:** source-linked alternatives, separate real-mode assurance, contextual revision approval, immutable result history, deterministic infrastructure generation, real compilation, manual Azure handoff, and an ACA-hosted no-model judge experience.

**Not yet delivered:** generated business application handlers, automated target provisioning/validation, final release gates for unresolved blockers, live workload observation, continuous drift detection, verified remediation, or measured business-outcome reporting. The public demo is a bounded single-writer deployment, not production multi-tenant SaaS; its private NFS mount is encrypted at rest, not in transit.

**Next: Intent Continuity.** Extend the evidence chain into separately authorized deployment and runtime observations, then connect drift and verified remediation back to customer requirements. Continuous outcome verification is the roadmap, not today's claim.

## The takeaway

**Intent-to-Impact makes the path from customer need to engineering action inspectable.** It combines architectural reasoning with a workflow that keeps assumptions visible, changes accountable and infrastructure tangible.

**Not just “Here is an architecture.”**  
**“Here is why it exists, what we challenged, what remains unresolved, and the exact package the team can take forward.”**