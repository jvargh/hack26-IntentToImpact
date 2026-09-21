import { DIMENSIONS, EXAMPLE_ANSWERS, EXAMPLE_DOCUMENTS, EXAMPLE_PROMPT, OPTIONS, QUESTIONS } from "./model";
import type { DesignDraft, SourceDocument } from "./model";

export const STORAGE_KEY = "intent-to-impact.business-draft.v1";
export const MAX_DOCUMENTS = 5;
export const MAX_FILE_BYTES = 1024 * 1024;
export const MAX_TEXT_LENGTH = 150_000;
export const MAX_PROMPT_LENGTH = 12_000;

export function newDraft(): DesignDraft {
  return {
    version: 1, id: crypto.randomUUID(), updatedAt: new Date().toISOString(), kind: "custom",
    title: "", prompt: "", documents: [],
    brief: { goal: "", actors: "", process: "", systems: "", constraints: "" },
    questions: QUESTIONS.map((question) => ({ ...question, answer: "" })),
    selectedOptionId: null, designRationale: "",
    reviews: Object.fromEntries(DIMENSIONS.map((dimension) => [dimension.id, { status: "not-reviewed", note: "" }])),
  };
}

export function exampleDraft(): DesignDraft {
  const draft = newDraft();
  return {
    ...draft, kind: "example", title: "A reliable order-to-fulfilment experience",
    prompt: EXAMPLE_PROMPT,
    questions: QUESTIONS.map((question) => ({ ...question, answer: EXAMPLE_ANSWERS[question.id] })),
    documents: EXAMPLE_DOCUMENTS.map((document) => ({ ...document, bytes: new TextEncoder().encode(document.text).length })),
    brief: {
      goal: "Acknowledge orders immediately and give customers a reliable path from payment to dispatch.",
      actors: "Customers; customer support; warehouse operations; ERP owner; payment provider.",
      process: "Submit order -> confirm payment -> check stock -> request fulfilment -> dispatch -> update customer. Reconcile failures and repeated callbacks.",
      systems: "Existing storefront, ERP, payment provider and warehouse interfaces. The ERP remains the stock owner.",
      constraints: "EU customer-data residency. No card storage. Keep the ERP. Example workshop assumptions: 2,000 orders/day, bursts of 50 submissions/second, RTO 60 minutes, RPO 15 minutes, USD 1,500/month budget and a pilot in 12 weeks. These are not validated targets or pricing. Retention periods and actual capacity remain open.",
    },
    designRationale: "Example rationale: decouple acknowledgement from warehouse availability, retain existing systems and make order state recoverable. Validate compensation and transactional outbox behavior before implementation.",
  };
}

export function prepareBrief(draft: DesignDraft): DesignDraft {
  if (!draft.prompt.trim()) throw new Error("Describe the business problem before continuing.");
  if (draft.prompt.length > MAX_PROMPT_LENGTH) throw new Error(`Keep the business prompt within ${MAX_PROMPT_LENGTH.toLocaleString()} characters.`);
  return {
    ...draft, title: draft.title.trim() || "Untitled architecture brief",
    brief: { ...draft.brief, goal: draft.brief.goal || draft.prompt.trim() },
    updatedAt: new Date().toISOString(),
  };
}

export function reviseInputs(draft: DesignDraft, patch: Pick<Partial<DesignDraft>, "prompt" | "documents">): DesignDraft {
  const blank = newDraft();
  return {
    ...draft, ...patch, kind: "custom", updatedAt: blank.updatedAt,
    brief: { ...blank.brief, goal: patch.prompt ?? draft.prompt },
    questions: blank.questions, selectedOptionId: null, designRationale: "", reviews: blank.reviews,
  };
}

export function choosePattern(draft: DesignDraft, optionId: string): DesignDraft {
  if (!OPTIONS.some((option) => option.id === optionId)) throw new Error("Select one of the available reference patterns.");
  if (draft.selectedOptionId === optionId) return draft;
  return {
    ...draft, selectedOptionId: optionId, updatedAt: new Date().toISOString(),
    reviews: Object.fromEntries(Object.entries(draft.reviews).map(([id, review]) =>
      [id, { ...review, status: "not-reviewed" as const }])),
  };
}

export async function readDocument(file: Pick<File, "name" | "size" | "arrayBuffer">): Promise<SourceDocument> {
  if (!/\.(txt|md|markdown)$/i.test(file.name)) {
    throw new Error(`${file.name}: this phase reads TXT and Markdown documents. Export PDF/Word content as text first.`);
  }
  if (file.size > MAX_FILE_BYTES) throw new Error(`${file.name}: keep each file under 1 MB.`);
  if (file.size === 0) throw new Error(`${file.name}: the document is empty.`);
  const buffer = await file.arrayBuffer();
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(buffer);
  } catch {
    throw new Error(`${file.name}: save this document as UTF-8 text before adding it.`);
  }
  if (text.includes("\0")) throw new Error(`${file.name}: binary content is not supported.`);
  if (!text.trim()) throw new Error(`${file.name}: there is no readable content.`);
  if (text.length > MAX_TEXT_LENGTH) throw new Error(`${file.name}: limit documents to ${MAX_TEXT_LENGTH.toLocaleString()} characters.`);
  return { id: crypto.randomUUID(), name: file.name, bytes: file.size, text };
}

export function appendDocuments(draft: DesignDraft, documents: SourceDocument[]): DesignDraft {
  if (draft.documents.length + documents.length > MAX_DOCUMENTS) throw new Error(`Add up to ${MAX_DOCUMENTS} documents per brief.`);
  const names = [...draft.documents, ...documents].map((document) => document.name.toLowerCase());
  if (new Set(names).size !== names.length) throw new Error("A document with that name is already attached. Remove it before adding a replacement.");
  if ([...draft.documents, ...documents].reduce((count, document) => count + document.text.length, 0) > MAX_TEXT_LENGTH) {
    throw new Error(`Keep combined document text within ${MAX_TEXT_LENGTH.toLocaleString()} characters.`);
  }
  return reviseInputs(draft, { documents: [...draft.documents, ...documents] });
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown, max = MAX_TEXT_LENGTH): value is string {
  return typeof value === "string" && value.length <= max;
}

export function isDraft(value: unknown): value is DesignDraft {
  if (!object(value) || value.version !== 1 || !text(value.id, 128) || !text(value.updatedAt, 64)
    || !Number.isFinite(Date.parse(value.updatedAt)) || (value.kind !== "custom" && value.kind !== "example")
    || !text(value.title, 160) || !text(value.prompt, MAX_PROMPT_LENGTH) || !text(value.designRationale, 12_000)) return false;
  if (!object(value.brief) || !["goal", "actors", "process", "systems", "constraints"].every((key) => text(value.brief && object(value.brief) ? value.brief[key] : null, 12_000))) return false;
  if (!Array.isArray(value.documents) || value.documents.length > MAX_DOCUMENTS) return false;
  if (!value.documents.every((document: unknown) => object(document) && text(document.id, 128)
    && text(document.name, 255) && text(document.text) && typeof document.bytes === "number"
    && Number.isInteger(document.bytes) && document.bytes >= 0 && document.bytes <= MAX_FILE_BYTES)) return false;
  if (value.documents.reduce((count: number, document: SourceDocument) => count + document.text.length, 0) > MAX_TEXT_LENGTH) return false;
  if (new Set(value.documents.map((document: SourceDocument) => document.id)).size !== value.documents.length) return false;
  if (!Array.isArray(value.questions) || value.questions.length !== QUESTIONS.length) return false;
  if (!QUESTIONS.every((question, index) => {
    const item: unknown = value.questions instanceof Array ? value.questions[index] : null;
    return object(item) && item.id === question.id && item.question === question.question
      && item.reason === question.reason && text(item.answer, 12_000);
  })) return false;
  if (value.selectedOptionId !== null && !OPTIONS.some((option) => option.id === value.selectedOptionId)) return false;
  if (!object(value.reviews)) return false;
  const reviews = value.reviews;
  return Object.keys(reviews).length === DIMENSIONS.length && DIMENSIONS.every((dimension) => {
    const item = reviews[dimension.id];
    return object(item) && (item.status === "not-reviewed" || item.status === "needs-work" || item.status === "reviewed") && text(item.note, 12_000);
  });
}

export function loadDraft(storage: Pick<Storage, "getItem"> = localStorage): DesignDraft | null {
  let raw: string | null;
  try { raw = storage.getItem(STORAGE_KEY); }
  catch { throw new Error("Browser storage is unavailable. You can work in memory and export your brief."); }
  if (raw === null) return null;
  if (raw.length > 1_200_000) throw new Error("The saved draft is too large. Clear it to start safely.");
  let parsed: unknown;
  try { parsed = JSON.parse(raw); }
  catch { throw new Error("The saved draft could not be read. Clear it to start again; it has not been replaced."); }
  if (!isDraft(parsed)) throw new Error("The saved draft has an unsupported format. Clear it to start again; it has not been replaced.");
  return parsed;
}

export function saveDraft(draft: DesignDraft, storage: Pick<Storage, "setItem"> = localStorage): void {
  if (!isDraft(draft)) throw new Error("This draft has invalid fields and was not saved.");
  try { storage.setItem(STORAGE_KEY, JSON.stringify({ ...draft, updatedAt: new Date().toISOString() })); }
  catch { throw new Error("Your browser could not save this draft. Export it before closing this page."); }
}

export function clearDraft(storage: Pick<Storage, "removeItem"> = localStorage): void {
  try { storage.removeItem(STORAGE_KEY); }
  catch { throw new Error("The saved draft could not be removed from this browser."); }
}

export function exportMarkdown(draft: DesignDraft): string {
  if (!isDraft(draft)) throw new Error("The draft contains invalid fields and could not be exported.");
  const option = OPTIONS.find((item) => item.id === draft.selectedOptionId);
  const lines = [
    `# ${draft.title || "Architecture design brief"}`, "",
    `Origin: ${draft.kind === "example" ? "illustrative worked example" : "user-authored local draft"}.`,
    "AI analysis is not connected. No generated recommendation, pricing validation, compliance certification, deployment or runtime proof is claimed.",
    "", "## Business intent", draft.prompt, "", "## Reviewed understanding",
    ...Object.entries(draft.brief).flatMap(([key, value]) => [`### ${key}`, value || "Not supplied", ""]),
    "## Source documents (local references)",
    ...draft.documents.map((document) => `- ${document.name} (${document.text.length} characters; raw document content is not included in this export)`),
    "", "## Clarifications", ...draft.questions.flatMap((question) => [`### ${question.question}`, question.answer || "Unanswered", ""]),
    "## Architecture starting point",
    option ? `${option.title} - manually selected reference pattern, not AI-generated or approved infrastructure.` : "No pattern selected.",
    draft.designRationale || "Selection rationale not supplied.", "",
  ];
  if (option) lines.push(
    "### Responsibilities", ...option.nodes.map((node) => `- ${node.title} (${node.service}): ${node.responsibility}`),
    "", "### Logical flow", "```mermaid", "flowchart LR",
    ...option.nodes.map((node) => `  ${node.id}["${node.title}"]`),
    ...option.flows.map((flow) => `  ${flow.from} -->|"${flow.label}"| ${flow.to}`),
    "```", "", `Trade-off: ${option.tradeoff}`, `Cost basis: ${option.costDriver}`, "",
  );
  lines.push("## 360 review");
  for (const dimension of DIMENSIONS) {
    const note = draft.reviews[dimension.id];
    if (!note) throw new Error(`Review notes are missing for ${dimension.title}.`);
    lines.push(`### ${dimension.title}`, `Checklist status: ${note.status} (local author review only).`,
      `Question: ${dimension.question}`, `Your notes: ${note.note || "Not supplied"}`);
    if (draft.kind === "example") lines.push(
      `Illustrative finding: ${dimension.finding}`,
      `Illustrative recommendation: ${dimension.recommendation}`,
      `Example sources: ${dimension.sourceIds.join(", ")}`,
    );
    lines.push("");
  }
  lines.push("## Next steps", "- Resolve unanswered requirements and assign owners.",
    "- Connect source-grounded analysis and architecture services.", "- Validate feasibility, cost and control evidence.",
    "- Review the final architecture before generating or deploying infrastructure.", "");
  return lines.join("\n");
}
