import { describe, expect, it } from "vitest";
import type { Requirement } from "../api/types";
import { BRIEF_TEMPLATE, dropUnfilledTemplate, parseBrief } from "./brief";
import { counts, decisions, prune, setRow } from "./checkpoint";
import { lifecycle, phaseIndex } from "./lifecycle";

// Mirrors tests/test_checkpoint.py so the preview splits like rfp_agent.brief.parse_brief.
describe("parseBrief", () => {
  it("splits paragraphs into H1..Hn and normalises line ends", () => {
    const b = parseBrief("Win theme: speed.\n\nWe have delivered this twice.\r\n\r\n\nAvoid Oracle.")!;
    expect(b.chunks.map((c) => c.id)).toEqual(["H1", "H2", "H3"]);
    expect(b.chunks.map((c) => c.text)).toEqual(["Win theme: speed.", "We have delivered this twice.", "Avoid Oracle."]);
    expect(b.text).not.toContain("\r");
  });

  it("attaches headings to the next paragraph and keeps a trailing heading", () => {
    const b = parseBrief("# Win themes\n\n- speed\n- price\n\nConstraints:\n\nNo offshore team.\n\n## Trailing")!;
    expect(b.chunks.map((c) => c.text)).toEqual([
      "# Win themes\n- speed\n- price",
      "Constraints:\nNo offshore team.",
      "## Trailing",
    ]);
  });

  it("is null when blank", () => {
    for (const t of [null, undefined, "", "   \n\n  "]) expect(parseBrief(t)).toBeNull();
  });

  it("keeps lines inside a paragraph", () => {
    const b = parseBrief("# Themes\n\nspeed and\nprice\n\nAzure only.")!;
    expect(b.chunks.map((c) => c.text)).toEqual(["# Themes\nspeed and\nprice", "Azure only."]);
  });
});

describe("dropUnfilledTemplate", () => {
  it("drops template headings left empty, so they neither become chunks nor stick to the next section", () => {
    const text = BRIEF_TEMPLATE.replace("Constraints:\n\n", "Constraints:\n\nTeam of four, onshore.\n\n");
    const out = dropUnfilledTemplate(text);
    expect(parseBrief(out)!.chunks.map((c) => c.text)).toEqual(["Constraints:\nTeam of four, onshore."]);
  });

  it("leaves an untouched template as nothing and the reviewer's own headings alone", () => {
    expect(parseBrief(dropUnfilledTemplate(BRIEF_TEMPLATE))).toBeNull();
    const own = "Our story:\n\n## Trailing";
    expect(dropUnfilledTemplate(own)).toBe(own);
  });
});

const req = (id: string, strictness: Requirement["strictness"] = "mandatory", type: Requirement["type"] = "functional"): Requirement => ({
  id,
  text: `${id} text`,
  type,
  strictness,
  quote: "q",
  chunk_ids: ["C0001"],
  quote_verified: true,
  merged_from: [],
  conflicts_with: [],
});

describe("checkpoint draft", () => {
  const reqs = [req("R001"), req("R002", "desired"), req("R003", "mandatory", "technical")];

  it("keeps only rows that differ, and sends them in list order", () => {
    let d = setRow({}, reqs[2], { strictness: "desired" });
    d = setRow(d, reqs[0], { reject: true });
    d = setRow(d, reqs[1], { strictness: "desired" }); // unchanged: no row
    expect(Object.keys(d).sort()).toEqual(["R001", "R003"]);
    expect(decisions(d, reqs)).toEqual([
      { requirement_id: "R001", action: "reject" },
      { requirement_id: "R003", action: "accept", strictness: "desired", type: null },
    ]);
  });

  it("drops a row set back to the extracted values", () => {
    let d = setRow({}, reqs[0], { type: "technical" });
    d = setRow(d, reqs[0], { type: "functional" });
    expect(d).toEqual({});
    d = setRow(setRow({}, reqs[0], { reject: true }), reqs[0], { reject: false });
    expect(d).toEqual({});
  });

  it("a rejection sends no edits", () => {
    const d = setRow(setRow({}, reqs[0], { strictness: "optional" }), reqs[0], { reject: true });
    expect(decisions(d, reqs)).toEqual([{ requirement_id: "R001", action: "reject" }]);
  });

  it("prunes rows a revision removed or already applied", () => {
    let d = setRow({}, reqs[0], { reject: true });
    d = setRow(d, reqs[1], { strictness: "mandatory" });
    const revised = [req("R002", "mandatory"), req("R003")];
    expect(prune(d, revised)).toEqual({});
  });

  it("counts what will be kept", () => {
    let d = setRow({}, reqs[0], { reject: true });
    d = setRow(d, reqs[1], { strictness: "mandatory" });
    expect(counts(d, reqs)).toEqual({ total: 3, rejected: 1, edited: 1, kept: 2, mandatoryKept: 2 });
  });
});

describe("lifecycle", () => {
  it("maps every state to a phase", () => {
    expect(lifecycle("running").phase).toBe("read");
    expect(lifecycle("awaiting_checkpoint")).toMatchObject({ phase: "checkpoint", busy: false });
    expect(lifecycle("drafting")).toMatchObject({ phase: "draft", busy: true });
    expect(lifecycle("refining")).toMatchObject({ phase: "refine", busy: true });
    expect(phaseIndex(lifecycle("signed_off").phase)).toBe(4);
    expect(phaseIndex(lifecycle("failed").phase)).toBe(-1);
  });
});
