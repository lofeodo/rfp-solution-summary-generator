import type { ChunkRef, Requirement, Risk, SolutionComponent, SolutionSummary } from "../api/types";

// What a citation chip can point at. Chunk IDs look like S3.2, requirements R001,
// components C01, risks K01, ambiguities A01, gaps G01.
export type IdKind = "chunk" | "requirement" | "component" | "risk" | "ambiguity" | "gap";

export function idKind(id: string): IdKind | null {
  if (/^S\d+\.\d+$/.test(id)) return "chunk";
  if (/^R\d+$/.test(id)) return "requirement";
  if (/^C\d+$/.test(id)) return "component";
  if (/^K\d+$/.test(id)) return "risk";
  if (/^A\d+$/.test(id)) return "ambiguity";
  if (/^G\d+$/.test(id)) return "gap";
  return null;
}

export interface SummaryIndex {
  chunks: Map<string, ChunkRef>;
  requirements: Map<string, Requirement>;
  components: Map<string, SolutionComponent>;
  risks: Map<string, Risk>;
  // requirement ID -> component IDs that address it
  addressedBy: Map<string, string[]>;
}

export function buildIndex(s: SolutionSummary): SummaryIndex {
  const addressedBy = new Map<string, string[]>();
  for (const c of s.solution.components)
    for (const r of c.requirement_ids) addressedBy.set(r, [...(addressedBy.get(r) ?? []), c.id]);
  return {
    chunks: new Map(s.chunks.map((c) => [c.id, c])),
    requirements: new Map(s.requirements.requirements.map((r) => [r.id, r])),
    components: new Map(s.solution.components.map((c) => [c.id, c])),
    risks: new Map(s.risks.risks.map((r) => [r.id, r])),
    addressedBy,
  };
}
