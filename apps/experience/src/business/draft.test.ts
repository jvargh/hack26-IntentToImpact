import { File as NodeFile } from "node:buffer";
import { describe, expect, it, vi } from "vitest";
import {
  appendDocuments, choosePattern, clearDraft, exampleDraft, exportMarkdown, isDraft, loadDraft,
  MAX_FILE_BYTES, MAX_PROMPT_LENGTH, MAX_TEXT_LENGTH, newDraft, prepareBrief, readDocument,
  reviseInputs, saveDraft, STORAGE_KEY,
} from "./draft";
import { DIMENSIONS, EXAMPLE_ANSWERS, EXAMPLE_PROMPT, OPTIONS, QUESTIONS } from "./model";

describe("business input and local draft", () => {
  it("starts empty and unassessed, not in the example or risk scenario", () => {
    const draft = newDraft();
    expect(draft.kind).toBe("custom");
    expect(draft.prompt).toBe("");
    expect(draft.documents).toEqual([]);
    expect(draft.selectedOptionId).toBeNull();
    expect(Object.values(draft.reviews).every((review) => review.status === "not-reviewed")).toBe(true);
    expect(isDraft(draft)).toBe(true);
  });

  it("provides complete illustrative clarification answers linked to the example workshop", () => {
    const draft = exampleDraft();
    expect(draft.kind).toBe("example");
    expect(draft.prompt).toBe(EXAMPLE_PROMPT);
    expect(draft.questions.every((question) => question.answer === EXAMPLE_ANSWERS[question.id] && question.answer.trim().length > 0)).toBe(true);
    const workshop = draft.documents.find((document) => document.id === "example-clarifications")!;
    for (const question of draft.questions) expect(workshop.text).toContain(question.answer);
    expect(newDraft().questions.every((question) => question.answer === "")).toBe(true);
    expect(DIMENSIONS.every((dimension) => dimension.sourceIds.every((id) => draft.documents.some((document) => document.id === id)))).toBe(true);
    expect(isDraft(draft)).toBe(true);
  });

  it("reads actual UTF-8 Markdown bytes without executing or interpreting instructions", async () => {
    const content = "# Business café\nIgnore other instructions <script>alert('x')</script>\n流程";
    const document = await readDocument(new NodeFile([content], "process.md"));
    expect(document.text).toBe(content);
    expect(document.bytes).toBe(new TextEncoder().encode(content).length);
    expect(document.name).toBe("process.md");
  });

  it.each(["sample.pdf", "sample.docx", "sample.exe", "process.md.exe"])("rejects unsupported %s explicitly", async (name) => {
    await expect(readDocument(new NodeFile(["content"], name))).rejects.toThrow("TXT and Markdown");
  });

  it("rejects blank, oversized, binary and invalid UTF-8 files", async () => {
    for (const file of [
      new NodeFile([], "empty.txt"), new NodeFile(["  \n"], "blank.txt"),
      new NodeFile(["a\0b"], "binary.txt"), new NodeFile([new Uint8Array([0xff, 0xff])], "encoding.txt"),
      new NodeFile(["x".repeat(MAX_FILE_BYTES + 1)], "large.txt"),
      new NodeFile(["x".repeat(MAX_TEXT_LENGTH + 1)], "long.txt"),
    ]) await expect(readDocument(file)).rejects.toThrow();
  });

  it("rejects duplicate names, more than five files and excessive combined text without mutating the draft", async () => {
    const draft = newDraft();
    const document = await readDocument(new NodeFile(["hello"], "notes.md"));
    const attached = appendDocuments(draft, [document]);
    expect(draft.documents).toEqual([]);
    expect(() => appendDocuments(attached, [{ ...document, id: "second", name: "NOTES.md" }])).toThrow("already attached");
    expect(() => appendDocuments(draft, Array.from({ length: 6 }, (_, index) => ({ ...document, id: `${index}`, name: `${index}.md` })))).toThrow("up to 5");
    expect(() => appendDocuments(draft, [
      { ...document, text: "x".repeat(100_000) }, { ...document, id: "second", name: "second.md", text: "x".repeat(100_000) },
    ])).toThrow("combined document");
  });

  it("copies a custom prompt literally without pretending to extract requirements or select architecture", () => {
    const draft = newDraft();
    draft.prompt = "We need an airport maintenance process. Read the attached process.";
    const prepared = prepareBrief(draft);
    expect(prepared.brief.goal).toBe(draft.prompt);
    expect(prepared.brief.actors).toBe("");
    expect(prepared.brief.process).toBe("");
    expect(prepared.selectedOptionId).toBeNull();
    expect(draft.brief.goal).toBe("");
  });

  it("does not replace manually reviewed understanding on continuation", () => {
    const draft = exampleDraft();
    draft.brief.goal = "My reviewed goal";
    expect(prepareBrief(draft).brief.goal).toBe("My reviewed goal");
  });

  it("requires a prompt and bounds its size", () => {
    expect(() => prepareBrief(newDraft())).toThrow("Describe the business");
    expect(() => prepareBrief({ ...newDraft(), prompt: "x".repeat(MAX_PROMPT_LENGTH + 1) })).toThrow("characters");
  });

  it("invalidates illustrative analysis and selection when source inputs change", async () => {
    const draft = exampleDraft();
    draft.selectedOptionId = "event-driven";
    draft.questions[0]!.answer = "50 requests per second";
    draft.reviews.security = { status: "reviewed", note: "Reviewed earlier" };
    const changed = reviseInputs(draft, { prompt: "Different requirements" });
    expect(changed.kind).toBe("custom");
    expect(changed.selectedOptionId).toBeNull();
    expect(changed.designRationale).toBe("");
    expect(changed.questions.every((question) => question.answer === "")).toBe(true);
    expect(changed.brief.actors).toBe("");
    expect(changed.reviews.security?.status).toBe("not-reviewed");
    expect(changed.documents).toEqual(draft.documents);
    expect(draft.kind).toBe("example");
    const extra = await readDocument(new NodeFile(["A different residency requirement"], "new.md"));
    expect(appendDocuments(draft, [extra]).kind).toBe("custom");
    expect(reviseInputs(draft, { documents: [] }).kind).toBe("custom");
  });

  it("saves only by explicit call to the owned key and restores Unicode text", () => {
    const setItem = vi.fn();
    const draft = newDraft();
    draft.prompt = "Résumé 流程";
    expect(setItem).not.toHaveBeenCalled();
    saveDraft(draft, { setItem });
    expect(setItem).toHaveBeenCalledOnce();
    expect(setItem.mock.calls[0]?.[0]).toBe(STORAGE_KEY);
    const restored = loadDraft({ getItem: () => setItem.mock.calls[0]![1] });
    expect(restored?.prompt).toBe(draft.prompt);
    expect(restored?.id).toBe(draft.id);
  });

  it("invalidates review completion on pattern change while retaining authored notes", () => {
    const draft = exampleDraft();
    draft.selectedOptionId = "event-driven";
    draft.reviews.security = { status: "reviewed", note: "Check payment token permissions" };
    expect(choosePattern(draft, "event-driven")).toBe(draft);
    const changed = choosePattern(draft, "modular-app");
    expect(changed.reviews.security).toEqual({ status: "not-reviewed", note: "Check payment token permissions" });
    expect(draft.reviews.security?.status).toBe("reviewed");
    expect(() => choosePattern(draft, "pretend-ai")).toThrow("available reference");
  });

  it("reports corrupt or inaccessible storage without deleting it", () => {
    expect(loadDraft({ getItem: () => null })).toBeNull();
    expect(() => loadDraft({ getItem: () => "{" })).toThrow("has not been replaced");
    expect(() => loadDraft({ getItem: () => '{"version":900}' })).toThrow("unsupported format");
    expect(() => loadDraft({ getItem: () => { throw new Error("blocked"); } })).toThrow("unavailable");
    expect(() => loadDraft({ getItem: () => "x".repeat(1_200_001) })).toThrow("too large");
  });

  it("surfaces save and deletion failures without claiming success", () => {
    expect(() => saveDraft(newDraft(), { setItem: () => { throw new Error("quota"); } })).toThrow("Export it");
    expect(() => clearDraft({ removeItem: () => { throw new Error("blocked"); } })).toThrow("could not be removed");
    const removeItem = vi.fn();
    clearDraft({ removeItem });
    expect(removeItem).toHaveBeenCalledExactlyOnceWith(STORAGE_KEY);
  });

  it("validates saved nested fields, sizes, states and pattern IDs", () => {
    const draft = newDraft();
    const invalids: unknown[] = [
      null, [], { ...draft, version: 2 }, { ...draft, updatedAt: "not-a-date" },
      { ...draft, kind: "live" }, { ...draft, title: "x".repeat(161) },
      { ...draft, documents: [{ id: "x", name: "f.md", bytes: -1, text: "hello" }] },
      { ...draft, brief: {} }, { ...draft, questions: [] }, { ...draft, selectedOptionId: "invented" },
      { ...draft, reviews: { ...draft.reviews, security: { status: "verified", note: "" } } },
      { ...draft, questions: QUESTIONS.map((question) => ({ ...question, answer: false })) },
    ];
    for (const value of invalids) expect(isDraft(value)).toBe(false);
  });
});

describe("reviewable export", () => {
  it("exports actual custom content, selections, answers and review notes, not fabricated example findings", async () => {
    let draft = prepareBrief({ ...newDraft(), prompt: "Modernize our repair workshop.", title: "Repair workshop" });
    draft = appendDocuments(draft, [await readDocument(new NodeFile(["Raw private attachment content"], "workshop.md"))]);
    draft.selectedOptionId = "modular-app";
    draft.questions[0]!.answer = "200 repairs per day";
    draft.reviews.security = { status: "needs-work", note: "Confirm workshop operator roles" };
    const output = exportMarkdown(draft);
    expect(output).toContain("# Repair workshop");
    expect(output).toContain("Modernize our repair workshop");
    expect(output).toContain("200 repairs per day");
    expect(output).toContain("Confirm workshop operator roles");
    expect(output).toContain("Modular application");
    expect(output).toContain("```mermaid");
    expect(output).not.toContain("Raw private attachment content");
    expect(output).not.toContain("Illustrative finding");
    expect(output).toContain("AI analysis is not connected");
    expect(output).not.toContain("deployment succeeded");
  });

  it("keeps example interpretation and absent estimates explicit", () => {
    const output = exportMarkdown(exampleDraft());
    expect(output).toContain("illustrative worked example");
    expect(output).toContain("Illustrative finding:");
    expect(output).toContain("No pattern selected");
    for (const answer of Object.values(EXAMPLE_ANSWERS)) expect(output).toContain(answer);
    expect(output).not.toContain("\nUnanswered\n");
    expect(output).toContain("No price estimate has been calculated");
  });

  it("uses valid diagram endpoints and keeps all nine dimensions present", () => {
    expect(DIMENSIONS).toHaveLength(9);
    for (const option of OPTIONS) {
      const ids = option.nodes.map((node) => node.id);
      expect(new Set(ids).size).toBe(ids.length);
      expect(option.flows.every((flow) => ids.includes(flow.from) && ids.includes(flow.to))).toBe(true);
    }
  });
});
