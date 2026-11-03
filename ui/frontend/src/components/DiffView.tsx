import { useState } from "react";
import type { DiffSummary, RevisionRecord } from "../api/types";
import { secs, usd, when } from "../lib/format";
import { compactDiff, diffRows, type ChangeKind } from "../lib/revisions";
import { Tag } from "./ui";

const MARK: Record<ChangeKind, string> = { added: "+", removed: "−", changed: "~" };
const MARK_CLS: Record<ChangeKind, string> = { added: "text-ink", removed: "text-accent", changed: "text-muted" };

// A revision's stored diff, item by item: whole items added or removed, and each changed
// field with its value before and after. Computed by code on the server (ST12b).
export function DiffView({ diff }: { diff: DiffSummary }) {
  const rows = diffRows(diff);
  if (rows.length === 0) return <p className="font-mono text-[11px] text-muted">No change.</p>;
  return (
    <ul className="border-l-2 border-hair pl-3">
      {rows.map((row) => (
        <li key={row.item} className="py-1.5">
          <p className="font-mono text-[11px]">
            <span className={`mr-1.5 ${MARK_CLS[row.kind]}`}>{MARK[row.kind]}</span>
            <span className={row.kind === "removed" ? "line-through" : ""}>{row.item}</span>
            {row.kind !== "changed" && <span className="ml-2 text-muted">{row.kind}</span>}
          </p>
          {row.fields.length > 0 && (
            <ul className="mt-1 space-y-1.5 pl-4">
              {row.fields.map((f, i) => (
                <li key={i} className="text-[14px] leading-snug">
                  <span className="mr-2 font-mono text-[11px] text-muted">
                    <span className={MARK_CLS[f.kind]}>{MARK[f.kind]}</span> {f.field || "value"}
                  </span>
                  {f.kind === "changed" && (
                    <>
                      <span className="bg-accentsoft text-muted line-through decoration-accent">{f.before}</span>
                      <span className="mx-1.5 font-mono text-[11px] text-muted">→</span>
                      <span>{f.after}</span>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}

const LIST_ITEMS = 6;

function short(items: string[]): string {
  return items.length <= LIST_ITEMS ? items.join(", ") : `${items.slice(0, LIST_ITEMS).join(", ")} +${items.length - LIST_ITEMS}`;
}

const KIND_LABEL: Record<RevisionRecord["kind"], string> = { revise: "revised", regenerate: "regenerated", sign_off: "signed off" };

// One record of the revision log: who, what, cost, a compact account of the change, and
// the full diff on demand (or always, with `open`).
export function RevisionLine({ r, open = false, showDiff = true }: { r: RevisionRecord; open?: boolean; showDiff?: boolean }) {
  const [expanded, setExpanded] = useState(open);
  const d = r.diff ? compactDiff(r.diff) : null;
  const changes = d ? d.added.length + d.removed.length + d.changed.length : 0;
  return (
    <li className="hair space-y-1 py-2.5">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-xs">{r.id}</span>
        {r.kind === "sign_off" ? <Tag tone="accent">signed off</Tag> : <Tag tone={r.status === "failed" ? "accent" : "ink"}>{r.status === "failed" ? "failed" : KIND_LABEL[r.kind]}</Tag>}
        <span className="font-mono text-[11px] text-muted">
          {r.artefact ?? ""}
          {r.to_version && r.to_version !== r.from_version ? ` v${r.from_version}→v${r.to_version}` : ""} · {r.reviewer} · {when(r.created_at)}
          {r.kind !== "sign_off" && ` · ${usd(r.cost_usd)} · ${secs(r.latency_s)}`}
        </span>
      </div>
      {r.instruction && <p className="text-[15px] italic">“{r.instruction}”</p>}
      {r.note && <p className="text-[15px]">{r.note}</p>}
      {r.error && <p className="font-mono text-[11px] text-accent">{r.error}</p>}
      {d && r.status === "applied" && (
        <p className="font-mono text-[11px]">
          {d.added.length > 0 && <span className="mr-3">+ added {short(d.added)}</span>}
          {d.removed.length > 0 && <span className="mr-3 text-accent">− removed {short(d.removed)}</span>}
          {d.changed.length > 0 && <span className="mr-3 text-muted">~ changed {short(d.changed)}</span>}
          {changes === 0 && <span className="mr-3 text-muted">no change</span>}
          {showDiff && changes > 0 && (
            <button type="button" className="kicker hover:text-accent" aria-expanded={expanded} onClick={() => setExpanded((x) => !x)}>
              {expanded ? "hide diff ▴" : "show diff ▾"}
            </button>
          )}
        </p>
      )}
      {r.made_stale.length > 0 && r.status === "applied" && (
        <p className="font-mono text-[11px] text-muted">made stale: {r.made_stale.join(", ")}</p>
      )}
      {showDiff && expanded && r.diff && <DiffView diff={r.diff} />}
    </li>
  );
}
