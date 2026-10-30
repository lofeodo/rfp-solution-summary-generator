import type {
  Ambiguity,
  Chunk,
  Gap,
  Requirement,
  RequirementsOutput,
  Risk,
  RiskResult,
  SolutionComponent,
  SolutionResult,
  SplitDocument,
} from "../api/types";

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

export interface IndexedChunk extends Chunk {
  section_title: string;
}

// Built from the per-stage artifacts, each optional, so a live run's index fills in as
// stages finish.
export interface RunIndex {
  chunks: Map<string, IndexedChunk>;
  requirements: Map<string, Requirement>;
  ambiguities: Map<string, Ambiguity>;
  gaps: Map<string, Gap>;
  components: Map<string, SolutionComponent>;
  risks: Map<string, Risk>;
  // requirement ID -> component IDs that address it
  addressedBy: Map<string, string[]>;
}

export interface IndexInputs {
  split?: SplitDocument | null;
  requirements?: RequirementsOutput | null;
  solution?: SolutionResult | null;
  risks?: RiskResult | null;
}

export function buildIndex({ split, requirements, solution, risks }: IndexInputs): RunIndex {
  const chunks = new Map<string, IndexedChunk>();
  for (const s of split?.sections ?? [])
    for (const c of s.chunks) chunks.set(c.id, { ...c, section_title: s.title });
  const components = solution?.solution.components ?? [];
  const addressedBy = new Map<string, string[]>();
  for (const c of components)
    for (const r of c.requirement_ids) addressedBy.set(r, [...(addressedBy.get(r) ?? []), c.id]);
  return {
    chunks,
    requirements: new Map((requirements?.requirements ?? []).map((r) => [r.id, r])),
    ambiguities: new Map((requirements?.ambiguities ?? []).map((a) => [a.id, a])),
    gaps: new Map((requirements?.gaps ?? []).map((g) => [g.id, g])),
    components: new Map(components.map((c) => [c.id, c])),
    risks: new Map((risks?.assessment.risks ?? []).map((r) => [r.id, r])),
    addressedBy,
  };
}
