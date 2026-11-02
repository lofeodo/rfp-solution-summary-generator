import type { DiffSummary } from "../api/types";

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
