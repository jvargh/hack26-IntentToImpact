import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Workbench } from "./Workbench";
import { DIMENSIONS, EXAMPLE_ANSWERS, EXAMPLE_PROMPT, QUESTIONS } from "./model";
import { exampleDraft, newDraft, saveDraft, STORAGE_KEY } from "./draft";

function documentFile(name = "process.md", text = "A customer asks support to arrange a delivery.") {
  const file = new File([text], name, { type: "text/plain" });
  Object.defineProperty(file, "arrayBuffer", {
    value: async () => new TextEncoder().encode(text).buffer,
  });
  return file;
}

function nav(title: string) {
  return within(screen.getByRole("navigation", { name: "Architecture design steps" }))
    .getByRole("button", { name: new RegExp(title) });
}

function prompt(text: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "What are you trying to achieve?" }), { target: { value: text } });
}

async function attach(user: ReturnType<typeof userEvent.setup>, file: File) {
  await user.upload(screen.getByLabelText("Attach business-process documents"), file);
}

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    get length() { return values.size; },
    clear: () => values.clear(),
    key: (index: number) => Array.from(values.keys())[index] ?? null,
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value); },
    removeItem: (key: string) => { values.delete(key); },
  } satisfies Storage);
});
afterEach(() => vi.restoreAllMocks());

describe("business-first architecture workbench", () => {
  it("fills every clarification in the worked example and keeps sample answers editable", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await user.click(screen.getByRole("button", { name: /Try worked example/ }));
    await user.click(screen.getByRole("button", { name: /Build my brief/ }));
    expect(screen.getByText(/Sample answers are filled in/)).toBeVisible();
    for (const question of QUESTIONS) {
      expect(screen.getByRole("textbox", { name: new RegExp(question.question.replace(/[?().]/g, "\\$&")) }))
        .toHaveValue(EXAMPLE_ANSWERS[question.id]);
    }
    const scale = screen.getByRole("textbox", { name: /What normal and peak volumes/ });
    await user.clear(scale);
    await user.type(scale, "Updated workshop workload");
    await user.click(nav("Design brief"));
    expect(screen.getByText("Updated workshop workload")).toBeVisible();
    expect(screen.getByText("Confirm the supplied answers with accountable owners.")).toBeVisible();
  });

  it("rejects too many attachments before reading any file bytes", async () => {
    render(<Workbench />);
    const readers = Array.from({ length: 6 }, () => vi.fn(async () => new ArrayBuffer(0)));
    const files = readers.map((arrayBuffer, index) => ({ name: `file-${index}.md`, size: 10, arrayBuffer }));
    const dropzone = screen.getByText("Add the context behind the process").closest(".wb-dropzone")!;
    fireEvent.drop(dropzone, { dataTransfer: { files } });
    expect(await screen.findByRole("alert")).toHaveTextContent("up to 5");
    for (const reader of readers) expect(reader).not.toHaveBeenCalled();
  });

  it("keeps one primary action after selecting an architecture pattern", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await user.click(nav("Architecture"));
    await user.click(screen.getByRole("button", { name: "Use Event-driven services" }));
    expect(document.querySelectorAll("#wb-main button.wb-primary")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Use Event-driven services" })).toHaveAttribute("aria-pressed", "true");
  });

  it("opens on an empty business intake, with no preselected scenario or analysis", () => {
    render(<Workbench />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Turn your business process into an architecture you can defend.");
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("");
    expect(screen.getByRole("textbox", { name: /Project name/ })).toHaveValue("");
    expect(screen.getByRole("button", { name: /Build my brief/ })).toBeVisible();
    expect(screen.getByRole("button", { name: /Try worked example/ })).toBeVisible();
    expect(screen.getByRole("button", { name: "Attach files" })).toBeVisible();
    expect(screen.getByText("Frontend preview · AI analysis not connected")).toBeVisible();
    expect(screen.queryByText(/An accepted order is not a fulfilled order/)).not.toBeInTheDocument();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("supports a full custom journey with literal sources, authoring and no fabricated findings", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    const intent = "Improve the support-led delivery process without replacing our dispatch system.";
    prompt(intent);
    fireEvent.change(screen.getByRole("textbox", { name: /Project name/ }), { target: { value: "Delivery service" } });
    await attach(user, documentFile());
    expect(await screen.findByRole("button", { name: "process.md" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Build my brief/ }));
    expect(screen.getByRole("textbox", { name: "Business outcome" })).toHaveValue(intent);
    expect(screen.getByRole("textbox", { name: "People & responsibilities" })).toHaveValue("");
    expect(screen.getByText("A customer asks support to arrange a delivery.")).toBeVisible();
    fireEvent.change(screen.getByRole("textbox", { name: "People & responsibilities" }), { target: { value: "Customer support owns scheduling." } });
    fireEvent.change(screen.getByRole("textbox", { name: /What normal and peak volumes/ }), { target: { value: "50 requests daily; measure peaks." } });
    await user.click(screen.getByRole("button", { name: /Explore architecture/ }));
    expect(screen.getByText("Preview only · not selected")).toBeVisible();
    expect(screen.getAllByRole("button", { name: /^Use / })).toHaveLength(3);
    await user.click(screen.getByRole("button", { name: "Use Modular application" }));
    expect(screen.getByRole("button", { name: "Use Modular application" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.change(screen.getByRole("textbox", { name: "Your design rationale" }), { target: { value: "Small support team and a cohesive process. Confirm dispatch integration." } });
    expect(screen.getByRole("heading", { name: "Background processor" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Open the 360 review/ }));
    expect(screen.getByText("Your project has not been assessed.")).toBeVisible();
    expect(screen.getAllByText("Not assessed", { exact: true })).toHaveLength(9);
    for (const dimension of DIMENSIONS) {
      expect(screen.getByRole("heading", { name: dimension.title })).toBeVisible();
      expect(screen.queryByText(dimension.finding)).not.toBeInTheDocument();
    }
    await user.selectOptions(screen.getByRole("combobox", { name: "Review status for Business fit" }), "needs-work");
    fireEvent.change(screen.getByRole("textbox", { name: "Notes for Business fit" }), { target: { value: "Confirm the hand-off owner with support." } });
    await user.click(screen.getByRole("button", { name: /Bring it into a design brief/ }));
    expect(screen.getByRole("heading", { name: "Delivery service" })).toBeVisible();
    expect(screen.getByText("Customer support owns scheduling.")).toBeVisible();
    expect(screen.getByText("50 requests daily; measure peaks.")).toBeVisible();
    expect(screen.getByText("Confirm the hand-off owner with support.")).toBeVisible();
    expect(screen.getByText(/Resolve 3 open clarifications/)).toBeVisible();
    expect(screen.getByRole("button", { name: /Download design brief/ })).toBeVisible();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("supports all five rail destinations without claiming incomplete work is complete", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    for (const [title, heading] of [
      ["Understanding", "First, get the business right."],
      ["Architecture", "A design is a set of choices."],
      ["360 review", "Look beyond the happy path."],
      ["Design brief", "Leave with a clear next conversation."],
      ["Your business", "Turn your business process into an architecture you can defend."],
    ]) {
      await user.click(nav(title!));
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(heading!);
      expect(nav(title!)).toHaveAttribute("aria-current", "step");
      expect(screen.getByRole("heading", { level: 1 })).toHaveFocus();
    }
  });

  it("validates an empty prompt without losing attached documents or project name", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    fireEvent.change(screen.getByRole("textbox", { name: /Project name/ }), { target: { value: "Keep this title" } });
    await attach(user, documentFile());
    await screen.findByRole("button", { name: "process.md" });
    await user.click(screen.getByRole("button", { name: /Build my brief/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("Describe the business problem before continuing.");
    expect(screen.getByRole("textbox", { name: /Project name/ })).toHaveValue("Keep this title");
    expect(screen.getByRole("button", { name: "process.md" })).toBeVisible();
  });

  it.each([
    ["unsupported", "process.pdf", "this phase reads TXT and Markdown"],
    ["oversized", "process.md", "keep each file under 1 MB"],
    ["empty", "process.md", "document is empty"],
  ])("shows %s document errors without losing user input", async (kind, name, expected) => {
    const user = userEvent.setup({ applyAccept: false });
    render(<Workbench />);
    prompt("Keep my original process description.");
    const file = documentFile(name, kind === "empty" ? "" : "Process detail");
    if (kind === "oversized") Object.defineProperty(file, "size", { value: 1024 * 1024 + 1 });
    await attach(user, file);
    expect(await screen.findByRole("alert")).toHaveTextContent(expected);
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("Keep my original process description.");
    expect(screen.queryByRole("list", { name: "Attached documents" })).not.toBeInTheDocument();
  });

  it("rejects duplicate documents and preserves the original source", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await attach(user, documentFile());
    await screen.findByRole("button", { name: "process.md" });
    await attach(user, documentFile("PROCESS.md", "Different content"));
    expect(await screen.findByRole("alert")).toHaveTextContent("A document with that name is already attached.");
    const list = screen.getByRole("list", { name: "Attached documents" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    await user.click(within(list).getByRole("button", { name: "process.md" }));
    expect(within(screen.getByRole("dialog")).getByText("A customer asks support to arrange a delivery.")).toBeVisible();
  });

  it("handles dropped files and rejects an over-limit batch without partially attaching it", async () => {
    render(<Workbench />);
    prompt("Keep my process while validating documents.");
    const dropzone = screen.getByText("Add the context behind the process").closest(".wb-dropzone")!;
    fireEvent.drop(dropzone, { dataTransfer: { files: Array.from({ length: 6 }, (_, index) => documentFile(`part-${index}.md`)) } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Add up to 5 documents per brief.");
    expect(screen.queryByRole("list", { name: "Attached documents" })).not.toBeInTheDocument();
    fireEvent.drop(dropzone, { dataTransfer: { files: [documentFile("dropped.md")] } });
    expect(await screen.findByRole("button", { name: "dropped.md" })).toBeVisible();
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("Keep my process while validating documents.");
  });

  it("opens source text accessibly, traps keyboard focus and restores focus on Escape", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await attach(user, documentFile());
    const opener = await screen.findByRole("button", { name: "process.md" });
    await user.click(opener);
    const modal = screen.getByRole("dialog", { name: "process.md" });
    const close = within(modal).getByRole("button", { name: "Close dialog" });
    expect(close).toHaveFocus();
    await user.tab({ shift: true });
    expect(within(modal).getByRole("button", { name: "Edit local copy" })).toHaveFocus();
    await user.tab();
    expect(close).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("edits a local document and requires confirmation before discarding unsaved source edits", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await attach(user, documentFile());
    await user.click(await screen.findByRole("button", { name: "process.md" }));
    await user.click(screen.getByRole("button", { name: "Edit local copy" }));
    fireEvent.change(screen.getByRole("textbox", { name: /Document text/ }), { target: { value: "Dispatch schedules the delivery after support approval." } });
    await user.keyboard("{Escape}");
    expect(screen.getByRole("heading", { name: "Discard source edits?" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Keep editing" }));
    await user.click(screen.getByRole("button", { name: "Apply source changes" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "process.md" }));
    expect(within(screen.getByRole("dialog")).getByText("Dispatch schedules the delivery after support approval.")).toBeVisible();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("requires explicit confirmation before example or New replaces a nonempty draft", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    prompt("My business process must survive cancellation.");
    await user.click(screen.getByRole("button", { name: /Try worked example/ }));
    expect(screen.getByRole("dialog", { name: "Replace this draft with the worked example?" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("My business process must survive cancellation.");
    await user.click(screen.getByRole("button", { name: "New brief" }));
    expect(screen.getByRole("dialog", { name: "Start a new brief?" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.click(screen.getByRole("button", { name: /Try worked example/ }));
    await user.click(screen.getByRole("button", { name: "Replace with example" }));
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue(EXAMPLE_PROMPT);
    await user.click(screen.getByRole("button", { name: "New brief" }));
    await user.click(screen.getByRole("button", { name: "Start new brief" }));
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("");
  });

  it("invalidates worked-example findings, choices and reviews when the prompt changes", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await user.click(screen.getByRole("button", { name: /Try worked example/ }));
    await user.click(nav("Architecture"));
    await user.click(screen.getByRole("button", { name: "Use Event-driven services" }));
    await user.click(nav("360 review"));
    expect(screen.getByText(DIMENSIONS[0]!.finding)).toBeVisible();
    await user.selectOptions(screen.getByRole("combobox", { name: "Review status for Business fit" }), "reviewed");
    fireEvent.change(screen.getByRole("textbox", { name: "Notes for Business fit" }), { target: { value: "A note on the example." } });
    await user.click(nav("Your business"));
    prompt("A different business process, authored by me.");
    await user.click(nav("Understanding"));
    expect(screen.getByRole("textbox", { name: "Business outcome" })).toHaveValue("A different business process, authored by me.");
    expect(screen.getByRole("textbox", { name: "People & responsibilities" })).toHaveValue("");
    await user.click(nav("Architecture"));
    expect(screen.getByText("Preview only · not selected")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Your design rationale" })).toHaveValue("");
    await user.click(nav("360 review"));
    expect(screen.getByText("Your project has not been assessed.")).toBeVisible();
    expect(screen.queryByText(DIMENSIONS[0]!.finding)).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Review status for Business fit" })).toHaveValue("not-reviewed");
    expect(screen.getByRole("textbox", { name: "Notes for Business fit" })).toHaveValue("");
  });

  it("invalidates the example when a source is removed", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await user.click(screen.getByRole("button", { name: /Try worked example/ }));
    await user.click(screen.getByRole("button", { name: "Remove Operating requirements.md" }));
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue(EXAMPLE_PROMPT);
    await user.click(nav("360 review"));
    expect(screen.queryByText(DIMENSIONS[0]!.finding)).not.toBeInTheDocument();
    expect(screen.getAllByText("Not assessed", { exact: true })).toHaveLength(9);
  });

  it("invalidates illustrative analysis when an example document is edited", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await user.click(screen.getByRole("button", { name: /Try worked example/ }));
    await user.click(screen.getByRole("button", { name: "Operating requirements.md" }));
    await user.click(screen.getByRole("button", { name: "Edit local copy" }));
    fireEvent.change(screen.getByRole("textbox", { name: /Document text/ }), { target: { value: "New process requirements, not example evidence." } });
    await user.click(screen.getByRole("button", { name: "Apply source changes" }));
    await user.click(nav("360 review"));
    expect(screen.getByText("Your project has not been assessed.")).toBeVisible();
    expect(screen.queryByText(DIMENSIONS[2]!.finding)).not.toBeInTheDocument();
    await user.click(nav("Understanding"));
    expect(screen.getByRole("textbox", { name: "Non-negotiables & constraints" })).toHaveValue("");
    expect(screen.getByText("New process requirements, not example evidence.")).toBeVisible();
  });

  it("shows traceable example findings whose sources open the supplied document", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    await user.click(screen.getByRole("button", { name: /Try worked example/ }));
    await user.click(nav("360 review"));
    expect(screen.getAllByText("Example finding", { exact: true })).toHaveLength(9);
    const businessCard = screen.getByRole("heading", { name: "Business fit" }).closest("article")!;
    await user.click(within(businessCard).getByRole("button", { name: /Order fulfilment - business process.md/ }));
    expect(screen.getByRole("dialog", { name: "Order fulfilment - business process.md" })).toBeVisible();
    expect(within(screen.getByRole("dialog")).getByText(/The existing ERP owns stock availability/)).toBeVisible();
  });

  it("only persists document contents after explicit local-save disclosure and confirmation", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    prompt("Save this support process.");
    await attach(user, documentFile());
    await screen.findByRole("button", { name: "process.md" });
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Save in browser" }));
    expect(screen.getByRole("dialog", { name: "Save this draft in your browser?" })).toHaveTextContent("full document contents");
    expect(screen.getByRole("dialog")).toHaveTextContent("Avoid shared devices");
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Save draft locally" }));
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)!).documents[0].text).toBe("A customer asks support to arrange a delivery.");
    expect(screen.getByRole("status")).toHaveTextContent("Draft saved in this browser");
    prompt("An unsaved revision.");
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)!).prompt).toBe("Save this support process.");
  });

  it("offers a saved draft without loading it into the workspace until disclosed and confirmed", async () => {
    const user = userEvent.setup();
    saveDraft(exampleDraft());
    render(<Workbench />);
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("");
    await user.click(screen.getByRole("button", { name: "Resume saved draft" }));
    expect(screen.getByRole("dialog", { name: "Open the saved local draft?" })).toHaveTextContent("3 document(s) stored in this browser");
    await user.click(screen.getByRole("button", { name: "Open saved draft" }));
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue(EXAMPLE_PROMPT);
    expect(screen.getByRole("status")).toHaveTextContent("Its documents are stored in this browser");
  });

  it("preserves corrupt saved data until explicit deletion instead of silently overwriting it", async () => {
    const user = userEvent.setup();
    localStorage.setItem(STORAGE_KEY, "{broken");
    render(<Workbench />);
    expect(screen.getByRole("alert")).toHaveTextContent("it has not been replaced");
    prompt("A safe new in-memory draft.");
    await user.click(screen.getByRole("button", { name: "Save in browser" }));
    expect(screen.getByRole("button", { name: "Save draft locally" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(localStorage.getItem(STORAGE_KEY)).toBe("{broken");
    await user.click(screen.getByRole("button", { name: "Remove saved browser data" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(localStorage.getItem(STORAGE_KEY)).toBe("{broken");
    await user.click(screen.getByRole("button", { name: "Remove saved browser data" }));
    await user.click(screen.getByRole("button", { name: "Remove saved data permanently" }));
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("A safe new in-memory draft.");
  });

  it("shows a storage failure and keeps export and in-memory work available", async () => {
    const user = userEvent.setup();
    render(<Workbench />);
    prompt("Keep working even when storage is blocked.");
    vi.spyOn(localStorage, "setItem").mockImplementation(() => { throw new Error("Quota exceeded"); });
    await user.click(screen.getByRole("button", { name: "Save in browser" }));
    await user.click(screen.getByRole("button", { name: "Save draft locally" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Your browser could not save this draft. Export it before closing this page.");
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("Keep working even when storage is blocked.");
    expect(screen.getByRole("button", { name: "Export current brief" })).toBeEnabled();
  });

  it("discloses unavailable browser storage without falling back to the example", () => {
    vi.spyOn(localStorage, "getItem").mockImplementation(() => { throw new Error("Storage denied"); });
    render(<Workbench />);
    expect(screen.getByRole("alert")).toHaveTextContent("Browser storage is unavailable");
    expect(screen.getByRole("textbox", { name: "What are you trying to achieve?" })).toHaveValue("");
    expect(screen.getByRole("button", { name: "Export current brief" })).toBeEnabled();
  });

  it("keeps the intake and five-step navigation usable at a narrow viewport", async () => {
    const width = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    try {
      const user = userEvent.setup();
      render(<Workbench />);
      prompt("A small-screen business brief.");
      await user.click(screen.getByRole("button", { name: /Build my brief/ }));
      expect(screen.getByRole("textbox", { name: "Business outcome" })).toHaveValue("A small-screen business brief.");
      expect(within(screen.getByRole("navigation")).getAllByRole("button")).toHaveLength(5);
      await user.click(nav("Design brief"));
      expect(screen.getByRole("button", { name: /Download design brief/ })).toBeEnabled();
    } finally {
      Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
    }
  });

  it("exports real Markdown content through a downloadable Blob and revokes the URL", async () => {
    const user = userEvent.setup();
    let exported: Blob | undefined;
    const createURL = vi.fn((blob: Blob) => { exported = blob; return "blob:local-brief"; });
    const revokeURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeURL });
    const clicks: { download: string; href: string }[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicks.push({ download: this.download, href: this.href });
    });
    render(<Workbench />);
    prompt("A support process.");
    fireEvent.change(screen.getByRole("textbox", { name: /Project name/ }), { target: { value: "Support process" } });
    await user.click(nav("Architecture"));
    await user.click(screen.getByRole("button", { name: "Use Modular application" }));
    await user.click(nav("Design brief"));
    await user.click(screen.getByRole("button", { name: /Download design brief/ }));
    expect(createURL).toHaveBeenCalledOnce();
    expect(clicks).toEqual([{ download: "Support-process.md", href: "blob:local-brief" }]);
    const markdown = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = reject;
      reader.readAsText(exported!);
    });
    expect(markdown).toContain("# Support process");
    expect(markdown).toContain("A support process.");
    expect(markdown).toContain("Modular application - manually selected reference pattern");
    expect(markdown).toContain("```mermaid");
    expect(markdown).toContain("## 360 review");
    expect(markdown).not.toContain("Illustrative finding:");
    await waitFor(() => expect(revokeURL).toHaveBeenCalledWith("blob:local-brief"), { timeout: 2000 });
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("preserves notes but resets review statuses after a different manual pattern is chosen", async () => {
    const user = userEvent.setup();
    const saved = newDraft();
    saved.prompt = "An authored process";
    saved.selectedOptionId = "event-driven";
    saved.reviews.business = { status: "reviewed", note: "Review this note again for a new pattern." };
    saveDraft(saved);
    render(<Workbench />);
    await user.click(screen.getByRole("button", { name: "Resume saved draft" }));
    await user.click(screen.getByRole("button", { name: "Open saved draft" }));
    await user.click(nav("Architecture"));
    await user.click(screen.getByRole("button", { name: "Use Event-driven services" }));
    expect(screen.getByText("Saved locally", { exact: true })).toBeVisible();
    expect(screen.queryByText("Pattern changed; review notes retained for re-review.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Use Modular application" }));
    expect(screen.getByRole("status")).toHaveTextContent("Pattern changed; review notes retained for re-review.");
    await user.click(nav("360 review"));
    expect(screen.getByRole("combobox", { name: "Review status for Business fit" })).toHaveValue("not-reviewed");
    expect(screen.getByRole("textbox", { name: "Notes for Business fit" })).toHaveValue("Review this note again for a new pattern.");
  });
});
