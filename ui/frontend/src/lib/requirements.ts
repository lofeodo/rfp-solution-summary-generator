import type { Requirement, RequirementType, Strictness } from "../api/types";

export const TYPE_LABELS: Record<RequirementType, string> = {
  functional: "Functional",
  technical: "Technical",
  security_compliance: "Security & compliance",
  legal_contractual: "Legal & contractual",
  timeline: "Timeline",
  budget_pricing: "Budget & pricing",
  submission: "Submission",
  other: "Other",
};

export const TYPES = Object.keys(TYPE_LABELS) as RequirementType[];
export const STRICTNESS: Strictness[] = ["mandatory", "desired", "optional"];

export interface RequirementFilter {
  types: RequirementType[]; // empty means all
  strictness: Strictness[]; // empty means all
  query: string;
}

export const EMPTY_FILTER: RequirementFilter = { types: [], strictness: [], query: "" };

export function filterRequirements(reqs: Requirement[], f: RequirementFilter): Requirement[] {
  const q = f.query.trim().toLowerCase();
  return reqs.filter(
    (r) =>
      (f.types.length === 0 || f.types.includes(r.type)) &&
      (f.strictness.length === 0 || f.strictness.includes(r.strictness)) &&
      (!q || r.id.toLowerCase() === q || r.text.toLowerCase().includes(q) || r.quote.toLowerCase().includes(q)),
  );
}

export function countBy<K extends string>(reqs: Requirement[], key: (r: Requirement) => K): Record<K, number> {
  const out = {} as Record<K, number>;
  for (const r of reqs) out[key(r)] = (out[key(r)] ?? 0) + 1;
  return out;
}

export function toggle<T>(list: T[], v: T): T[] {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}
