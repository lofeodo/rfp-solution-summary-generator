// TypeScript mirrors of the backend models (ui/backend/models.py) and the artifact JSON
// (src/rfp_agent/schemas.py plus the agent wrappers). Field names match the JSON exactly.

export type RunState = "queued" | "running" | "finished" | "failed";
export type StageStatus = "started" | "finished" | "failed";

export interface RunTotals {
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  cost_usd: number;
  latency_s: number;
  retries: number;
}

export interface StageEvent {
  stage: string;
  status: StageStatus;
  started_at: string;
  latency_s: number;
  calls: number;
  totals: RunTotals;
  error: string | null;
}

export interface NodeMetrics {
  node: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  cost_usd: number;
  latency_s: number;
  retries: number;
  started_at: string;
}

export interface RunListItem {
  run_id: string;
  status: RunState;
  sample: boolean;
  source_name: string;
  started_at: string | null;
  finished_at: string | null;
  cost_usd: number;
  latency_s: number | null;
  stages_done: number;
}

export interface RunStatus {
  run_id: string;
  status: RunState;
  sample: boolean;
  source_name: string;
  model: string | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  stages: StageEvent[];
  totals: RunTotals;
  nodes: NodeMetrics[];
  langfuse_trace_url: string | null;
  artifacts: string[];
}

export interface Health {
  status: "ok";
  model: string;
  runs_dir: string;
}

export interface RunCreated {
  run_id: string;
  status: RunState;
}

// ---- Artifacts ----

export type RequirementType =
  | "functional"
  | "technical"
  | "security_compliance"
  | "legal_contractual"
  | "timeline"
  | "budget_pricing"
  | "submission"
  | "other";
export type Strictness = "mandatory" | "desired" | "optional";
export type Level = "low" | "medium" | "high";

export interface Chunk {
  id: string;
  section_id: string;
  section_path: string[];
  page_start: number;
  page_end: number;
  text: string;
}

export interface ChunkRef {
  id: string;
  section_title: string;
  page_start: number;
  page_end: number;
}

export interface Claim {
  text: string;
  kind: "fact" | "inference";
  chunk_ids: string[];
}

export interface Requirement {
  id: string;
  text: string;
  type: RequirementType;
  strictness: Strictness;
  quote: string;
  chunk_ids: string[];
  quote_verified: boolean;
  merged_from: string[];
  conflicts_with: string[];
}

export interface Ambiguity {
  id: string;
  description: string;
  chunk_ids: string[];
  requirement_ids: string[];
}

export interface Gap {
  id: string;
  description: string;
  chunk_ids: string[];
  referenced_document: string | null;
}

export interface RequirementsOutput {
  requirements: Requirement[];
  ambiguities: Ambiguity[];
  gaps: Gap[];
}

export interface ProblemStatement {
  client_situation: Claim[];
  goal: Claim[];
  success_criteria: Claim[];
  constraints: Claim[];
}

export interface Coverage {
  mandatory_total: number;
  mandatory_covered: number;
  uncovered_requirement_ids: string[];
}

export interface SolutionComponent {
  id: string;
  title: string;
  description: string;
  requirement_ids: string[];
  claims: Claim[];
}

export interface Solution {
  summary: string;
  components: SolutionComponent[];
  assumptions: Claim[];
  coverage: Coverage;
}

export interface Risk {
  id: string;
  title: string;
  description: string;
  severity: Level;
  likelihood: Level;
  justification: string;
  source: "rfp" | "solution";
  requirement_ids: string[];
  chunk_ids: string[];
  mitigation: string | null;
}

export interface ReferencedDocument {
  name: string;
  kind: string;
  url: string | null;
  page: number;
  section: string | null;
  present: boolean;
}

export interface PageFlag {
  page: number;
  reason: string;
  detail: string | null;
}

export interface SolutionSummary {
  run_id: string;
  source_path: string;
  document_title: string | null;
  generated_at: string;
  model: string;
  chunks: ChunkRef[];
  requirements: RequirementsOutput;
  problem_statement: ProblemStatement;
  solution: Solution;
  risks: { risks: Risk[] };
  referenced_documents: ReferencedDocument[];
  flags: PageFlag[];
}

export interface ChunkSummary {
  chunk_id: string;
  summary: string;
  relevant: boolean;
  error: string | null;
}

export interface ProblemResult {
  mode: "hierarchical" | "full_text";
  statement: ProblemStatement;
  chunk_summaries: ChunkSummary[];
}

export interface SolutionResult {
  solution: Solution;
  rounds: { iteration: number; coverage: Coverage }[];
}

export interface RiskResult {
  assessment: { risks: Risk[] };
  findings: {
    uncovered_requirement_ids: string[];
    conflicts: [string, string][];
    absent_documents: ReferencedDocument[];
    flags: PageFlag[];
    budget_requirement_count: number;
  };
}

export interface RequirementsReport {
  chunks: number;
  single_call: boolean;
  calls_failed: string[];
  quote_retries: number;
  unverified_quotes: string[];
  dropped_unknown_chunk: number;
  pre_dedupe: number;
  exact_merges: number;
  fuzzy_merges: number;
  conflicts: number;
  dedupe_retried: boolean;
  dedupe_violations: string[];
  dedupe_fallback: boolean;
  dedupe_failed: boolean;
}

export interface Page {
  number: number;
  markdown: string;
  word_count: number;
}

export interface ParsedDocument {
  source_path: string;
  title: string | null;
  outline: { level: number; title: string; page: number }[];
  pages: Page[];
  tables: { page: number; markdown: string }[];
  images: { page: number; width: number; height: number; caption: string | null }[];
  referenced_documents: ReferencedDocument[];
  flags: PageFlag[];
}

export interface PageJudgement {
  text_usable: boolean;
  content_missing: boolean;
  page_kind: string;
  confirmed_flags: string[];
  reason: string;
}

export interface ParseQualityReport {
  judged_pages: number[];
  judgements: Record<string, PageJudgement>;
  escalations: { page: number; triggered_by: string; confirmed_bad: boolean; action: string }[];
}

export interface Section {
  id: string;
  title: string;
  level: number;
  path: string[];
  page_start: number;
  page_end: number;
  kind: "narrative" | "requirement_bearing";
  chunks: Chunk[];
}

export interface SplitDocument {
  sections: Section[];
}

export interface ArtifactMap {
  parsed: ParsedDocument;
  quality: ParseQualityReport;
  split: SplitDocument;
  requirements: RequirementsOutput;
  requirements_report: RequirementsReport;
  problem: ProblemResult;
  solution: SolutionResult;
  risks: RiskResult;
  summary: SolutionSummary;
}
export type ArtifactName = keyof ArtifactMap;
