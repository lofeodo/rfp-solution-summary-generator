import type { Artefact, DiffSummary, RegenerateStage, ReviewState, RevisionRecord, RunState } from "../api/types";

// A revision's diff by item, for a one-line account: which items were added, removed or
// changed. Diff paths look like `requirements[R005]` (a whole item) or
// `requirements[R001].chunk_ids[S4.1]` (a field inside one); a nested add or remove is a
// change of its item. Items without an ID keep their field (`goal[0]`); paths without an
// item group by their first segment (`summary`).

const ITEM = /^\w+\[[^\]]+\]$/;
const FIRST_ITEM = /^(\w+)\[([^\]]+)\]/;

function itemOf(path: string): string {
  const m = path.match(FIRST_ITEM);
  if (!m) return path.split(".")[0];
  return /^\d+$/.test(m[2]) ? `${m[1]}[${m[2]}]` : m[2];
}

export interface CompactDiff {
  added: string[];
  removed: string[];
  changed: string[];
}

export function compactDiff(d: DiffSummary): CompactDiff {
  const added = new Set<string>();
  const removed = new Set<string>();
  const changed = new Set<string>();
  for (const p of d.added) (ITEM.test(p) ? added : changed).add(itemOf(p));
  for (const p of d.removed) (ITEM.test(p) ? removed : changed).add(itemOf(p));
  for (const c of d.changed) changed.add(itemOf(c.path));
  for (const id of [...added, ...removed]) changed.delete(id);
  return { added: [...added], removed: [...removed], changed: [...changed] };
}

// ---- the full diff view (ST12e) -------------------------------------------------------

export type ChangeKind = "added" | "removed" | "changed";

export interface DiffField {
  field: string; // the path inside the item, "" for the item itself
  kind: ChangeKind;
  before?: string;
  after?: string;
}

export interface DiffRow {
  item: string;
  kind: ChangeKind; // added or removed: the whole item; changed: fields inside it
  fields: DiffField[];
}

// The part of a path after its item: `components[C2].title` -> `title`, `summary` -> "".
function fieldOf(path: string): string {
  const m = path.match(FIRST_ITEM);
  const prefix = m ? m[0] : path.split(".")[0];
  return path.slice(prefix.length).replace(/^\./, "");
}

const VALUE_CHARS = 600;

// A stored before/after value as one line of text.
export function showValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  const s =
    typeof v === "string"
      ? v
      : Array.isArray(v)
        ? v.map(showValue).join(", ")
        : typeof v === "object"
          ? JSON.stringify(v)
          : String(v);
  return s.length > VALUE_CHARS ? `${s.slice(0, VALUE_CHARS - 1)}…` : s;
}

// A revision's stored diff, item by item, in the order the items first appear.
export function diffRows(d: DiffSummary): DiffRow[] {
  const rows = new Map<string, DiffRow>();
  const row = (item: string) => {
    let r = rows.get(item);
    if (!r) rows.set(item, (r = { item, kind: "changed", fields: [] }));
    return r;
  };
  const whole = (path: string, kind: "added" | "removed") => {
    const item = itemOf(path);
    if (ITEM.test(path) || !path.includes(".")) row(item).kind = kind;
    else row(item).fields.push({ field: fieldOf(path), kind });
  };
  for (const p of d.removed) whole(p, "removed");
  for (const p of d.added) whole(p, "added");
  for (const c of d.changed)
    row(itemOf(c.path)).fields.push({
      field: fieldOf(c.path),
      kind: "changed",
      before: showValue(c.before),
      after: showValue(c.after),
    });
  return [...rows.values()];
}

// ---- review state (ST12e) --------------------------------------------------------------

export const ARTEFACT_LABEL: Record<Artefact, string> = {
  requirements: "Requirements",
  problem: "Problem statement",
  solution: "Solution",
  risks: "Risks",
};

// The pipeline stage that regenerates an artefact, if any (the risk stage writes `risks`).
export function stageOf(a: Artefact): RegenerateStage | null {
  return a === "solution" ? "solution" : a === "risks" ? "risk" : null;
}

export function canRegenerate(review: ReviewState, a: Artefact): boolean {
  const s = stageOf(a);
  return s !== null && review.allowed.regenerate.includes(s);
}

// Why the run cannot be signed off now; empty when it can (or already is). Mirrors the
// server's refusals so the button explains itself; the server stays the authority.
export function signOffBlockers(state: RunState, review: ReviewState): string[] {
  if (state === "signed_off") return [];
  if (state === "failed") return ["the run failed"];
  if (state === "awaiting_checkpoint") return ["the checkpoint is not confirmed yet"];
  if (state !== "finished") return ["a job is running; wait for it to end"];
  return review.stale.map((a) => `${ARTEFACT_LABEL[a]} is stale: regenerate or revise it`);
}

// The records that touched one artefact, newest first (sign-offs touch none).
export function historyOf(log: RevisionRecord[], a: Artefact): RevisionRecord[] {
  return log.filter((r) => r.artefact === a).reverse();
}

export function totalCost(log: RevisionRecord[]): number {
  return log.reduce((sum, r) => sum + r.cost_usd, 0);
}
