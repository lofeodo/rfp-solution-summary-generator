import type { Requirement, RequirementDecision, RequirementType, Strictness } from "../api/types";

// The reviewer's row actions at the checkpoint, before they are sent. Only rows that differ
// from the list are kept: accepting as extracted is the default and needs no decision.

export interface RowDraft {
  reject?: boolean;
  strictness?: Strictness;
  type?: RequirementType;
}

export type CheckpointDraft = Record<string, RowDraft>;

function normalise(req: Requirement, row: RowDraft): RowDraft | null {
  const out: RowDraft = {};
  if (row.reject) out.reject = true;
  if (row.strictness && row.strictness !== req.strictness) out.strictness = row.strictness;
  if (row.type && row.type !== req.type) out.type = row.type;
  return Object.keys(out).length ? out : null;
}

export function setRow(draft: CheckpointDraft, req: Requirement, patch: RowDraft): CheckpointDraft {
  const row = normalise(req, { ...draft[req.id], ...patch });
  const { [req.id]: _, ...rest } = draft;
  return row ? { ...rest, [req.id]: row } : rest;
}

// The draft against the list as it stands now: rows whose requirement a revision removed
// are dropped, and changes a revision already made are no longer changes.
export function prune(draft: CheckpointDraft, reqs: Requirement[]): CheckpointDraft {
  const out: CheckpointDraft = {};
  for (const r of reqs) {
    const row = draft[r.id] && normalise(r, draft[r.id]);
    if (row) out[r.id] = row;
  }
  return out;
}

// The decisions to send, in list order. A rejection carries no edits (the server refuses
// a rejected requirement that is also edited).
export function decisions(draft: CheckpointDraft, reqs: Requirement[]): RequirementDecision[] {
  const out: RequirementDecision[] = [];
  for (const r of reqs) {
    const row = draft[r.id];
    if (!row) continue;
    if (row.reject) out.push({ requirement_id: r.id, action: "reject" });
    else out.push({ requirement_id: r.id, action: "accept", strictness: row.strictness ?? null, type: row.type ?? null });
  }
  return out;
}

export function effective(req: Requirement, row: RowDraft | undefined): { strictness: Strictness; type: RequirementType } {
  return { strictness: row?.strictness ?? req.strictness, type: row?.type ?? req.type };
}

export interface DraftCounts {
  total: number;
  rejected: number;
  edited: number;
  kept: number;
  mandatoryKept: number;
}

export function counts(draft: CheckpointDraft, reqs: Requirement[]): DraftCounts {
  let rejected = 0;
  let edited = 0;
  let mandatoryKept = 0;
  for (const r of reqs) {
    const row = draft[r.id];
    if (row?.reject) {
      rejected++;
      continue;
    }
    if (row) edited++;
    if (effective(r, row).strictness === "mandatory") mandatoryKept++;
  }
  return { total: reqs.length, rejected, edited, kept: reqs.length - rejected, mandatoryKept };
}
