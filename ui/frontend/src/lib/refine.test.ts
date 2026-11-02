import { describe, expect, it } from "vitest";
import type { ReviewState, RevisionRecord } from "../api/types";
import { buildIndex, idKind } from "./ids";
import { refineNote } from "./lifecycle";
import { canRegenerate, diffRows, historyOf, showValue, signOffBlockers, stageOf, totalCost } from "./revisions";

function review(patch: Partial<ReviewState> = {}, allowed: Partial<ReviewState["allowed"]> = {}): ReviewState {
  return {
    checkpoint: null,
    versions: { artefacts: {}, signed_off: null },
    stale: [],
    sign_off: null,
    revisions: 0,
    ...patch,
    allowed: { checkpoint: false, revise: [], regenerate: [], sign_off: false, ...allowed },
  };
}

function rec(id: string, patch: Partial<RevisionRecord> = {}): RevisionRecord {
  return {
    id,
    kind: "revise",
    artefact: "solution",
    reviewer: "Ana",
    instruction: "x",
    note: null,
    from_version: 1,
    to_version: 2,
    made_stale: [],
    model: null,
    calls: 1,
    cost_usd: 0.01,
    latency_s: 2,
    diff: null,
    status: "applied",
    error: null,
    created_at: "2026-11-02T12:00:00Z",
    ...patch,
  };
}

describe("diffRows", () => {
  it("groups fields under their item, whole items as added or removed", () => {
    const rows = diffRows({
      added: ["components[C04]", "components[C02].requirement_ids[R009]"],
      removed: ["components[C03]"],
      changed: [
        { path: "components[C02].title", before: "Hosting", after: "Managed hosting" },
        { path: "summary", before: "Old.", after: "New." },
        { path: "coverage.mandatory_covered", before: 40, after: 41 },
      ],
    });
    expect(rows.map((r) => [r.item, r.kind])).toEqual([
      ["C03", "removed"],
      ["C04", "added"],
      ["C02", "changed"],
      ["summary", "changed"],
      ["coverage", "changed"],
    ]);
    const c02 = rows.find((r) => r.item === "C02")!;
    expect(c02.fields).toEqual([
      { field: "requirement_ids[R009]", kind: "added" },
      { field: "title", kind: "changed", before: "Hosting", after: "Managed hosting" },
    ]);
    expect(rows.find((r) => r.item === "summary")!.fields[0]).toMatchObject({ field: "", before: "Old.", after: "New." });
    expect(rows.find((r) => r.item === "coverage")!.fields[0]).toMatchObject({ field: "mandatory_covered", before: "40", after: "41" });
  });

  it("keys claims by their text and positional items by index", () => {
    const rows = diffRows({
      added: ["assumptions[The client hosts on Azure.]", "goal[2]"],
      removed: [],
      changed: [{ path: "goal[0].text", before: "a", after: "b" }],
    });
    expect(rows.map((r) => [r.item, r.kind])).toEqual([
      ["The client hosts on Azure.", "added"],
      ["goal[2]", "added"],
      ["goal[0]", "changed"],
    ]);
    expect(rows[2].fields[0].field).toBe("text");
  });

  it("is empty for an empty diff", () => {
    expect(diffRows({ added: [], removed: [], changed: [] })).toEqual([]);
  });
});

describe("showValue", () => {
  it("renders values as one line, capped", () => {
    expect(showValue(null)).toBe("—");
    expect(showValue(["S1.1", "S2.3"])).toBe("S1.1, S2.3");
    expect(showValue(true)).toBe("true");
    expect(showValue({ a: 1 })).toBe('{"a":1}');
    const long = showValue("x".repeat(1000));
    expect(long.length).toBe(600);
    expect(long.endsWith("…")).toBe(true);
  });
});

describe("review state", () => {
  it("maps artefacts to the stage that regenerates them", () => {
    expect(["requirements", "problem", "solution", "risks"].map((a) => stageOf(a as never))).toEqual([null, null, "solution", "risk"]);
    const r = review({}, { regenerate: ["risk"] });
    expect(canRegenerate(r, "risks")).toBe(true);
    expect(canRegenerate(r, "solution")).toBe(false);
    expect(canRegenerate(r, "problem")).toBe(false);
  });

  it("explains why sign-off is blocked", () => {
    expect(signOffBlockers("finished", review())).toEqual([]);
    expect(signOffBlockers("finished", review({ stale: ["solution", "risks"] }))).toEqual([
      "Solution is stale: regenerate or revise it",
      "Risks is stale: regenerate or revise it",
    ]);
    expect(signOffBlockers("refining", review())).toHaveLength(1);
    expect(signOffBlockers("awaiting_checkpoint", review())[0]).toContain("checkpoint");
    expect(signOffBlockers("signed_off", review({ stale: ["risks"] }))).toEqual([]);
  });

  it("lists an artefact's records newest first and totals cost", () => {
    const log = [rec("V01"), rec("V02", { artefact: "risks" }), rec("V03"), rec("V04", { kind: "sign_off", artefact: null, cost_usd: 0 })];
    expect(historyOf(log, "solution").map((r) => r.id)).toEqual(["V03", "V01"]);
    expect(historyOf(log, "problem")).toEqual([]);
    expect(totalCost(log)).toBeCloseTo(0.03);
  });

  it("says what stands before the sign-off", () => {
    expect(refineNote("finished", review({ stale: ["risks"] }))).toContain("Stale: risks");
    expect(refineNote("finished", review({}, { sign_off: true }))).toBe("Ready to sign off.");
    expect(refineNote("refining", review({}, { sign_off: true }))).toBeNull();
    expect(refineNote("finished", null)).toBeNull();
  });
});

describe("brief citations", () => {
  it("indexes H IDs from the checkpoint's brief", () => {
    expect(idKind("H3")).toBe("brief");
    const idx = buildIndex({
      checkpoint: {
        reviewer: "Ana",
        confirmed_at: "2026-11-02T12:00:00Z",
        waited_s: 3,
        decisions: [],
        brief: { text: "a\n\nb", chunks: [{ id: "H1", text: "a" }, { id: "H2", text: "b" }] },
        note: null,
      },
    });
    expect(idx.brief.get("H2")?.text).toBe("b");
    expect(idx.briefBy).toBe("Ana");
    expect(buildIndex({}).brief.size).toBe(0);
  });
});
