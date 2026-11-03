import type { StageEvent } from "../api/types";

// Pipeline order, mirroring rfp_agent.graph.STAGES. requirements and problem run in parallel.
export const STAGES = [
  { id: "parse", label: "Parse", what: "PDF to markdown, flags" },
  { id: "parse_quality", label: "Quality", what: "LLM judges flagged pages" },
  { id: "split", label: "Split", what: "Sections and citable chunks" },
  { id: "requirements", label: "Requirements", what: "Per-chunk extraction, dedupe", parallel: true },
  { id: "problem", label: "Problem", what: "Hierarchical summaries", parallel: true },
  { id: "checkpoint", label: "Checkpoint", what: "Reviewer confirms, writes the brief", human: true },
  { id: "solution", label: "Solution", what: "Components, coverage loop" },
  { id: "risk", label: "Risks", what: "Risk assessment" },
  { id: "assemble", label: "Assemble", what: "summary.json and .md" },
] as const;

export type StageId = (typeof STAGES)[number]["id"];
// `skipped`: a human stage the run went past without (runs from before ST12).
export type StageState = "pending" | "running" | "finished" | "failed" | "waiting" | "skipped";

export type StageMap = Record<string, StageEvent>;

// Keep the latest event per stage. Replays from disk have no `started` events, so a stage
// may go straight from absent to finished; that is fine.
export function reduceStage(map: StageMap, ev: StageEvent): StageMap {
  return { ...map, [ev.stage]: ev };
}

export function fromList(events: StageEvent[]): StageMap {
  return events.reduce(reduceStage, {} as StageMap);
}

export interface StageRow {
  id: string;
  label: string;
  what: string;
  parallel: boolean;
  human: boolean;
  state: StageState;
  event: StageEvent | undefined;
}

export function stageRows(map: StageMap): StageRow[] {
  return STAGES.map((s, i) => {
    const ev = map[s.id];
    const later = STAGES.slice(i + 1).some((t) => map[t.id]);
    const state: StageState = !ev
      ? "human" in s && later
        ? "skipped"
        : "pending"
      : ev.status === "started"
        ? "running"
        : ev.status;
    return { id: s.id, label: s.label, what: s.what, parallel: "parallel" in s, human: "human" in s, state, event: ev };
  });
}

// Finished stages of the timeline (revision records do not count).
export function stagesDone(map: StageMap): number {
  return STAGES.filter((s) => map[s.id]?.status === "finished").length;
}
