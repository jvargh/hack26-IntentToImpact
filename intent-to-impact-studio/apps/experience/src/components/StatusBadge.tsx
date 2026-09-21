export type Tone = "neutral" | "risk" | "warning" | "verified" | "local" | "fixture";

export function statusTone(status: string): Tone {
  if (status === "breached" || status === "known-risk" || status === "broken") return "risk";
  if (status === "verified") return "verified";
  if (status === "prepared") return "local";
  if (["stale", "pending", "gap", "verification-pending", "restoration-pending", "blocked", "awaiting-operator"].includes(status)) return "warning";
  return "neutral";
}

export function StatusBadge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return <span className="status-badge" data-tone={tone}><span aria-hidden="true" className="status-dot" />{label}</span>;
}

export function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time unavailable";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium", timeStyle: "short", timeZone: "UTC",
  }).format(date) + " UTC";
}
