import { describe, expect, it } from "vitest";
import type { Requirement, Risk, RiskResult, StageEvent, SplitDocument, SolutionSummary } from "../api/types";
import { fromList, reduceStage, stageRows, stagesDone } from "./stages";
import { highlightQuote, plainText } from "./highlight";
import { EMPTY_FILTER, filterRequirements, toggle } from "./requirements";
import { sortRisks } from "./risks";
import { cleanTitle, pages, secs, tokens, usd } from "./format";
import { buildIndex, idKind } from "./ids";
import split from "../../../../runs/samples/missouri/split.json";
import summary from "../../../../runs/samples/missouri/summary.json";

const totals = { input_tokens: 0, output_tokens: 0, cached_input_tokens: 0, cost_usd: 0, latency_s: 0, retries: 0 };
const ev = (stage: string, status: StageEvent["status"]): StageEvent => ({
  stage,
  status,
  started_at: "2026-10-30T00:00:00Z",
  latency_s: 1,
  calls: 0,
  totals,
  error: null,
});

describe("stages", () => {
  it("keeps the latest event per stage and orders rows by pipeline", () => {
    let m = reduceStage({}, ev("problem", "started"));
    m = reduceStage(m, ev("requirements", "started"));
    m = reduceStage(m, ev("problem", "finished"));
    const rows = stageRows(m);
    expect(rows.map((r) => r.id)).toEqual([
      "parse", "parse_quality", "split", "requirements", "problem", "solution", "risk", "assemble",
    ]);
    expect(rows.find((r) => r.id === "requirements")!.state).toBe("running");
    expect(rows.find((r) => r.id === "problem")!.state).toBe("finished");
    expect(rows.find((r) => r.id === "parse")!.state).toBe("pending");
    expect(rows.filter((r) => r.parallel).map((r) => r.id)).toEqual(["requirements", "problem"]);
  });

  it("handles a disk replay with no started events, and failures", () => {
    const m = fromList([ev("parse", "finished"), ev("parse_quality", "failed")]);
    expect(stageRows(m)[1].state).toBe("failed");
    expect(stagesDone(m)).toBe(1);
  });
});

describe("highlight", () => {
  it("strips pymupdf4llm markup", () => {
    expect(plainText("Send to **<u>a@b.org</u>** by<br>noon")).toBe("Send to a@b.org by\nnoon");
  });

  it("finds a quote across markup, curly quotes and whitespace", () => {
    const text = "Intro. Proposals are “due” by\n  **August 21**. End.";
    const h = highlightQuote(text, 'Proposals are "due" by August 21');
    expect(h).not.toBeNull();
    expect(h!.before).toBe("Intro. ");
    expect(h!.match).toBe("Proposals are “due” by\n  **August 21");
    expect(h!.partial).toBe(false);
  });

  it("falls back to the opening of a long quote, else null", () => {
    const text = "The vendor shall provide training to all staff before go-live, at no cost.";
    const h = highlightQuote(text, "The vendor shall provide training to all staff before go-live and afterwards");
    expect(h?.partial).toBe(true);
    expect(highlightQuote(text, "nothing like this")).toBeNull();
    expect(highlightQuote(text, "  ")).toBeNull();
  });

  it("highlights nearly every verified Missouri quote in one of its cited chunks", () => {
    const chunks = new Map(
      (split as SplitDocument).sections.flatMap((s) => s.chunks).map((c) => [c.id, plainText(c.text)]),
    );
    const reqs = (summary as SolutionSummary).requirements.requirements.filter((r) => r.quote_verified);
    const found = reqs.filter((r) =>
      r.chunk_ids.some((id) => {
        const h = chunks.has(id) ? highlightQuote(chunks.get(id)!, r.quote) : null;
        return h !== null && !h.partial;
      }),
    );
    expect(reqs.length).toBeGreaterThan(50);
    expect(found.length / reqs.length).toBeGreaterThanOrEqual(0.95);
  });
});

const req = (id: string, type: Requirement["type"], strictness: Requirement["strictness"], text: string): Requirement => ({
  id, type, strictness, text, quote: text, chunk_ids: ["S1.1"], quote_verified: true, merged_from: [], conflicts_with: [],
});

describe("requirements filter", () => {
  const reqs = [
    req("R001", "submission", "mandatory", "Submit by email"),
    req("R002", "technical", "desired", "Use Python"),
    req("R003", "technical", "mandatory", "WCAG 2.1 AA"),
  ];
  it("filters by type, strictness and text or ID", () => {
    expect(filterRequirements(reqs, EMPTY_FILTER)).toHaveLength(3);
    expect(filterRequirements(reqs, { ...EMPTY_FILTER, types: ["technical"] }).map((r) => r.id)).toEqual(["R002", "R003"]);
    expect(filterRequirements(reqs, { types: ["technical"], strictness: ["mandatory"], query: "" }).map((r) => r.id)).toEqual(["R003"]);
    expect(filterRequirements(reqs, { ...EMPTY_FILTER, query: "python" }).map((r) => r.id)).toEqual(["R002"]);
    expect(filterRequirements(reqs, { ...EMPTY_FILTER, query: "r001" }).map((r) => r.id)).toEqual(["R001"]);
  });
  it("toggles list membership", () => {
    expect(toggle(["a"], "b")).toEqual(["a", "b"]);
    expect(toggle(["a", "b"], "a")).toEqual(["b"]);
  });
});

describe("risks", () => {
  const risk = (id: string, severity: Risk["severity"], likelihood: Risk["likelihood"]) =>
    ({ id, severity, likelihood }) as Risk;
  it("sorts by severity, likelihood, then ID", () => {
    const sorted = sortRisks([risk("K03", "low", "high"), risk("K02", "high", "low"), risk("K01", "high", "low"), risk("K04", "high", "high")]);
    expect(sorted.map((r) => r.id)).toEqual(["K04", "K01", "K02", "K03"]);
  });
});

describe("format and ids", () => {
  it("formats numbers", () => {
    expect(usd(0.0497)).toBe("$0.0497");
    expect(usd(1.5)).toBe("$1.50");
    expect(tokens(950)).toBe("950");
    expect(tokens(12700)).toBe("13k");
    expect(tokens(1234)).toBe("1.2k");
    expect(secs(82)).toBe("1 m 22 s");
    expect(secs(null)).toBe("—");
    expect(pages(5, 5)).toBe("p. 5");
    expect(pages(5, 6)).toBe("pp. 5–6");
    expect(cleanTitle("**(B) Background**")).toBe("(B) Background");
  });
  it("classifies IDs and indexes the summary", () => {
    expect(["S3.2", "R001", "C01", "K12", "A01", "G03", "X1"].map(idKind)).toEqual([
      "chunk", "requirement", "component", "risk", "ambiguity", "gap", null,
    ]);
    const s = summary as SolutionSummary;
    const idx = buildIndex({
      split: split as SplitDocument,
      requirements: s.requirements,
      solution: { solution: s.solution, rounds: [] },
      risks: { assessment: s.risks, findings: {} as RiskResult["findings"] },
    });
    expect(idx.requirements.size).toBe(120);
    expect(idx.chunks.get("S9.1")?.page_start).toBe(5);
    expect(idx.chunks.size).toBe(s.chunks.length);
    expect(idx.addressedBy.get("R005")).toContain("C01");
    expect(idx.risks.get("K01")?.severity).toBe("high");
    expect(buildIndex({}).chunks.size).toBe(0);
  });
});
