import type { Level, Risk } from "../api/types";

const RANK: Record<Level, number> = { high: 0, medium: 1, low: 2 };

// Same order as render/markdown.py: severity, then likelihood (high first), then ID.
export function sortRisks(risks: Risk[]): Risk[] {
  return [...risks].sort(
    (a, b) =>
      RANK[a.severity] - RANK[b.severity] ||
      RANK[a.likelihood] - RANK[b.likelihood] ||
      a.id.localeCompare(b.id),
  );
}

export function countBySeverity(risks: Risk[]): Record<Level, number> {
  const out: Record<Level, number> = { high: 0, medium: 0, low: 0 };
  for (const r of risks) out[r.severity]++;
  return out;
}
