import type { RunState } from "../api/types";

// The human loop as five phases (ST12): the machine reads, the reviewer checks, the machine
// drafts, both refine, the reviewer signs off.
export const PHASES = [
  { id: "read", label: "Read" },
  { id: "checkpoint", label: "Checkpoint" },
  { id: "draft", label: "Draft" },
  { id: "refine", label: "Refine" },
  { id: "sign_off", label: "Sign-off" },
] as const;

export type PhaseId = (typeof PHASES)[number]["id"];

const PHASE_OF: Record<Exclude<RunState, "failed">, PhaseId> = {
  queued: "read",
  running: "read",
  awaiting_checkpoint: "checkpoint",
  drafting: "draft",
  finished: "refine",
  refining: "refine",
  signed_off: "sign_off",
};

export interface Lifecycle {
  phase: PhaseId | null; // null for a failed run
  busy: boolean; // the machine is working; the reviewer waits
  next: string; // one line: what happens now, or what the reviewer does next
}

export function lifecycle(state: RunState): Lifecycle {
  switch (state) {
    case "queued":
      return { phase: PHASE_OF[state], busy: true, next: "Queued behind another job." };
    case "running":
      return { phase: PHASE_OF[state], busy: true, next: "Reading the RFP: parse, split, requirements and problem." };
    case "awaiting_checkpoint":
      return {
        phase: PHASE_OF[state],
        busy: false,
        next: "Your turn: check the requirements, write the pursuit brief, then confirm to start drafting.",
      };
    case "drafting":
      return { phase: PHASE_OF[state], busy: true, next: "Drafting the solution and risks from the confirmed list and the brief." };
    case "finished":
      return { phase: PHASE_OF[state], busy: false, next: "Draft ready. Review it, refine it, then sign off." };
    case "refining":
      return { phase: PHASE_OF[state], busy: true, next: "Applying a change; the run is busy until it ends." };
    case "signed_off":
      return { phase: PHASE_OF[state], busy: false, next: "Signed off. This version is frozen." };
    case "failed":
      return { phase: null, busy: false, next: "A pipeline stage failed; see the error above." };
  }
}

export function phaseIndex(phase: PhaseId | null): number {
  return phase === null ? -1 : PHASES.findIndex((p) => p.id === phase);
}
