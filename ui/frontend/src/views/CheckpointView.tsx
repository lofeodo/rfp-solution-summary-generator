import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Artefact, CheckpointRecord, Requirement, RevisionRecord, RunStatus } from "../api/types";
import { RevisionLine } from "../components/DiffView";
import { CiteChip } from "../components/source";
import { SectionHead, SubHead, Waiting } from "../components/ui";
import type { RunData } from "../hooks/useRunData";
import { BRIEF_TEMPLATE, dropUnfilledTemplate, parseBrief } from "../lib/brief";
import { counts, decisions, prune, setRow, type CheckpointDraft, type RowDraft } from "../lib/checkpoint";
import { secs, when } from "../lib/format";
import { TYPE_LABELS } from "../lib/requirements";
import { checkpointKey, load, save } from "../lib/storage";
import { useReview } from "../hooks/useReview";
import CheckpointRows from "./CheckpointRows";

const INPUT =
  "block w-full border-b-2 border-ink bg-transparent py-1 font-mono text-sm placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-50";
const AREA =
  "block w-full border-2 border-ink bg-white/40 p-3 font-serif text-[15px] leading-relaxed placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-50";

interface Props {
  runId: string;
  data: RunData;
  status: RunStatus | null;
  refresh: () => void;
}

// The Checkpoint tab (ST12d): the form while the run waits, the record once confirmed.
export default function CheckpointView({ runId, data, status, refresh }: Props) {
  if (!status) return <Waiting what="Loading the run." loading />;
  const record = status.review?.checkpoint ?? null;
  if (record) return <CheckpointRecordView record={record} reqs={data.extracted?.requirements ?? []} drafting={status.status === "drafting"} />;
  const s = status.status;
  if (s === "queued" || s === "running")
    return <Waiting what="The checkpoint opens once the requirements and the problem statement are extracted." />;
  // A paused run keeps the form while a revision of its requirements or problem runs.
  const paused = s === "awaiting_checkpoint" || (s === "refining" && !data.has("solution"));
  if (!paused)
    return (
      <div className="hair py-10">
        <p className="kicker">No checkpoint</p>
        <p className="mt-2 font-display text-2xl text-muted">
          {s === "failed"
            ? "The run failed before reaching the checkpoint."
            : "This run went straight through without a reviewer (unattended, or made before the checkpoint existed)."}
        </p>
      </div>
    );
  return <CheckpointForm runId={runId} data={data} status={status} refresh={refresh} />;
}

// ---- the form ----------------------------------------------------------------------

interface Saved {
  draft: CheckpointDraft;
  brief: string;
  note: string;
}

function CheckpointForm({ runId, data, status, refresh }: Props & { status: RunStatus }) {
  const reqs = data.requirements?.requirements ?? null;
  const allowed = status.review.allowed;
  const busy = status.status !== "awaiting_checkpoint";

  // The reviewer's name lives on the run page, shared with the refine and sign-off forms.
  const review = useReview();
  const reviewer = review?.reviewer ?? "";
  const setReviewer = review?.setReviewer ?? (() => undefined);
  const [saved, setSaved] = useState<Saved>(() => ({ draft: {}, brief: "", note: "", ...load<Partial<Saved>>(checkpointKey(runId), {}) }));
  const { draft, brief, note } = saved;
  const update = (patch: Partial<Saved>) => setSaved((prev) => ({ ...prev, ...patch }));

  useEffect(() => save(checkpointKey(runId), saved), [runId, saved]);
  // A revision may remove requirements or apply a change the reviewer had drafted.
  useEffect(() => {
    if (reqs) setSaved((prev) => ({ ...prev, draft: prune(prev.draft, reqs) }));
  }, [reqs]);

  const onRow = (req: Requirement, patch: RowDraft) => setSaved((prev) => ({ ...prev, draft: setRow(prev.draft, req, patch) }));

  if (!reqs) return <Waiting what="Loading the requirements." loading={data.has("requirements")} />;
  const c = counts(draft, reqs);
  const toSend = dropUnfilledTemplate(brief);
  const parsed = parseBrief(toSend);

  return (
    <div className="space-y-16">
      <section>
        <SectionHead n="00" title="Checkpoint" aside={busy ? <span className="text-accent">applying a change…</span> : "waiting for a reviewer"} />
        <p className="max-w-prose text-[17px]">
          Nothing is drafted yet. Check what the machine read, tell it what the RFP does not say, then confirm. The
          solution and risks are written from the list and the brief you confirm here.
        </p>
        <label className="mt-6 block max-w-sm">
          <span className="kicker">Reviewing as</span>
          <input
            className={INPUT}
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            placeholder="Your name"
            autoComplete="name"
            maxLength={200}
          />
        </label>
      </section>

      <section>
        <SectionHead
          n="01"
          title="Requirements"
          aside={`${c.kept} kept of ${c.total} · ${c.mandatoryKept} mandatory · ${c.rejected} rejected · ${c.edited} edited`}
        />
        <CheckpointRows
          reqs={reqs}
          draft={draft}
          onChange={onRow}
          onReset={() => update({ draft: {} })}
          disabled={busy}
        />
      </section>

      <section>
        <SectionHead n="02" title="Instructions" aside="model edits, checked by code" />
        <InstructionBox
          runId={runId}
          reviewer={reviewer.trim()}
          targets={allowed.revise.filter((a) => a === "requirements" || a === "problem")}
          busy={busy}
          revisions={status.review.revisions}
          refresh={refresh}
        />
      </section>

      <section>
        <SectionHead n="03" title="Pursuit brief" aside={parsed ? `${parsed.chunks.length} citable paragraphs` : "optional"} />
        <div className="grid gap-x-10 gap-y-6 xl:grid-cols-2">
          <div>
            <p className="mb-3 max-w-prose text-muted">
              What the RFP does not contain: win themes, our capabilities, constraints, client context, things to avoid.
              Each paragraph becomes evidence the drafter cites as H1, H2…, shown apart from the RFP's own.
            </p>
            <textarea
              className={`${AREA} min-h-72`}
              value={brief}
              onChange={(e) => update({ brief: e.target.value })}
              placeholder="Paragraphs separated by blank lines. A line ending in a colon heads the paragraph under it. Or insert the template."
              disabled={busy}
              aria-label="Pursuit brief"
            />
            <div className="mt-2 flex flex-wrap gap-3">
              <button type="button" className="btn" disabled={busy || brief.trim().length > 0} onClick={() => update({ brief: BRIEF_TEMPLATE })}>
                Insert template
              </button>
              {brief && (
                <button type="button" className="kicker hover:text-accent" disabled={busy} onClick={() => update({ brief: "" })}>
                  clear ×
                </button>
              )}
            </div>
          </div>
          <div>
            <p className="kicker mb-2">How the drafter will cite it</p>
            {parsed ? (
              <ol className="rule">
                {parsed.chunks.map((ch) => (
                  <li key={ch.id} className="hair grid grid-cols-[2.5rem_1fr] gap-x-2 py-2">
                    <span className="font-mono text-xs text-accent">{ch.id}</span>
                    <span className="whitespace-pre-line text-[15px]">{ch.text}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="hair py-3 text-muted">No brief: the draft rests on the RFP alone.</p>
            )}
            {toSend !== brief && parsed && (
              <p className="mt-2 font-mono text-[11px] text-muted">Template headings left empty are not sent.</p>
            )}
          </div>
        </div>
      </section>

      <ConfirmBox
        reviewer={reviewer.trim()}
        note={note}
        onNote={(n) => update({ note: n })}
        rejected={c.rejected}
        edited={c.edited}
        kept={c.kept}
        briefChunks={parsed?.chunks.length ?? 0}
        disabled={busy || !allowed.checkpoint}
        onConfirm={async () => {
          await api.checkpoint(runId, {
            reviewer: reviewer.trim(),
            decisions: decisions(draft, reqs),
            brief: parsed ? toSend : null,
            note: note.trim() || null,
          });
          save(checkpointKey(runId), null);
          refresh();
        }}
      />
    </div>
  );
}

// ---- instructions --------------------------------------------------------------------

const TARGET_LABEL: Partial<Record<Artefact, string>> = { requirements: "Requirements", problem: "Problem statement" };
const TARGET_HINT: Partial<Record<Artefact, string>> = {
  requirements: "e.g. Split R014 into the hosting and the support requirement; add the 99.9% uptime clause from section 4.2.",
  problem: "e.g. The goal should say the client wants to retire the mainframe, not just modernise it.",
};

function InstructionBox({
  runId,
  reviewer,
  targets,
  busy,
  revisions,
  refresh,
}: {
  runId: string;
  reviewer: string;
  targets: Artefact[];
  busy: boolean;
  revisions: number;
  refresh: () => void;
}) {
  const [target, setTarget] = useState<Artefact>("requirements");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [log, setLog] = useState<RevisionRecord[]>([]);

  // The revision log, reread whenever a record is added and the run is at rest again.
  useEffect(() => {
    if (busy || revisions === 0) return;
    let alive = true;
    api.revisions(runId).then(
      (l) => alive && setLog(l.revisions),
      () => undefined,
    );
    return () => {
      alive = false;
    };
  }, [runId, revisions, busy]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      await api.revise(runId, { reviewer, artefact: target, instruction: text.trim() });
      setText("");
      refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  const blocked = busy || sending || !targets.includes(target);
  return (
    <div className="grid gap-x-10 gap-y-8 xl:grid-cols-2">
      <form onSubmit={submit} className="space-y-3">
        <p className="max-w-prose text-muted">
          For changes that need new text: merge, split, add, reword. The model applies the instruction and code checks
          the result (quotes verbatim from the RFP, IDs kept); a failed check leaves the list as it was.
        </p>
        <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="What to change">
          {(["requirements", "problem"] as Artefact[]).map((a) => (
            <button
              key={a}
              type="button"
              role="radio"
              aria-checked={target === a}
              disabled={!targets.includes(a)}
              onClick={() => setTarget(a)}
              className={`border px-2 py-0.5 font-mono text-[11px] transition-colors disabled:opacity-40 ${
                target === a ? "border-ink bg-ink text-paper" : "border-hair hover:border-ink"
              }`}
            >
              {TARGET_LABEL[a]}
            </button>
          ))}
        </div>
        <textarea
          className={`${AREA} min-h-28`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={TARGET_HINT[target]}
          disabled={busy}
          aria-label="Instruction"
          maxLength={20000}
        />
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" className="btn btn-accent" disabled={blocked || !reviewer || !text.trim()}>
            {busy ? "Applying…" : sending ? "Sending…" : "Apply instruction"}
          </button>
          {!reviewer && <span className="font-mono text-[11px] text-muted">Enter your name above first.</span>}
          {target === "problem" && (
            <Link to={`/runs/${runId}/problem`} className="kicker hover:text-accent">
              see the problem statement →
            </Link>
          )}
        </div>
        {error && (
          <p role="alert" className="border-l-4 border-accent bg-accentsoft px-3 py-2 font-mono text-xs">
            {error}
          </p>
        )}
      </form>
      <div>
        <p className="kicker mb-2">Applied at the checkpoint</p>
        {busy && <p className="hair py-3 font-mono text-xs text-accent">A change is being applied…</p>}
        {log.length === 0 && !busy && <p className="hair py-3 text-muted">No instruction yet.</p>}
        <ol className="rule">
          {[...log].reverse().map((r) => (
            <RevisionLine key={r.id} r={r} />
          ))}
        </ol>
      </div>
    </div>
  );
}

// ---- confirm -------------------------------------------------------------------------

function ConfirmBox({
  reviewer,
  note,
  onNote,
  rejected,
  edited,
  kept,
  briefChunks,
  disabled,
  onConfirm,
}: {
  reviewer: string;
  note: string;
  onNote: (n: string) => void;
  rejected: number;
  edited: number;
  kept: number;
  briefChunks: number;
  disabled: boolean;
  onConfirm: () => Promise<void>;
}) {
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      await onConfirm();
    } catch (err) {
      setError((err as Error).message);
      setSending(false);
    }
  }

  return (
    <section className="border-2 border-ink p-4 md:p-6">
      <form onSubmit={submit} className="grid gap-x-10 gap-y-5 lg:grid-cols-[1fr_auto]">
        <div className="space-y-4">
          <SubHead>Confirm and draft</SubHead>
          <ul className="font-mono text-xs leading-6">
            <li>
              {kept} requirements go to the drafter · {rejected} rejected · {edited} edited
            </li>
            <li>{briefChunks ? `Brief: ${briefChunks} citable paragraphs (H1–H${briefChunks})` : "No brief"}</li>
            <li>Reviewer: {reviewer || <span className="text-accent">enter your name at the top</span>}</li>
          </ul>
          <label className="block max-w-prose">
            <span className="kicker">Note for the record (optional)</span>
            <input className={INPUT} value={note} onChange={(e) => onNote(e.target.value)} maxLength={5000} disabled={disabled} />
          </label>
          {error && (
            <p role="alert" className="border-l-4 border-accent bg-accentsoft px-3 py-2 font-mono text-xs">
              {error}
            </p>
          )}
        </div>
        <div className="flex items-end">
          <button type="submit" className="btn btn-accent w-full justify-center px-6 py-3 text-sm" disabled={disabled || sending || !reviewer}>
            {sending ? "Confirming…" : "Confirm and draft →"}
          </button>
        </div>
      </form>
    </section>
  );
}

// ---- the record ----------------------------------------------------------------------

function CheckpointRecordView({ record, reqs, drafting }: { record: CheckpointRecord; reqs: Requirement[]; drafting: boolean }) {
  const byId = useMemo(() => new Map(reqs.map((r) => [r.id, r])), [reqs]);
  const rejected = record.decisions.filter((d) => d.action === "reject");
  const edited = record.decisions.filter((d) => d.action === "accept" && (d.strictness || d.type));
  return (
    <div className="space-y-12">
      <section>
        <SectionHead n="00" title="Checkpoint" aside={drafting ? <span className="text-accent">drafting…</span> : "confirmed"} />
        <dl className="grid max-w-3xl grid-cols-[8rem_1fr] gap-x-4 gap-y-2 font-mono text-sm">
          <dt className="kicker">Reviewer</dt>
          <dd>{record.reviewer}</dd>
          <dt className="kicker">Confirmed</dt>
          <dd>{when(record.confirmed_at)}</dd>
          <dt className="kicker">Waited</dt>
          <dd>{secs(record.waited_s)}</dd>
          {record.note && (
            <>
              <dt className="kicker">Note</dt>
              <dd className="font-serif">{record.note}</dd>
            </>
          )}
        </dl>
      </section>

      <section className="grid gap-x-10 gap-y-10 xl:grid-cols-2">
        <div>
          <div className="rule mb-3 flex items-baseline justify-between pt-2">
            <SubHead>Rejected</SubHead>
            <span className="font-mono text-[11px] text-muted">{rejected.length}</span>
          </div>
          {rejected.length === 0 && <p className="text-muted">None.</p>}
          <ul className="space-y-2">
            {rejected.map((d) => (
              <li key={d.requirement_id} className="grid grid-cols-[3.5rem_1fr] gap-x-2 text-[15px]">
                <span className="font-mono text-xs text-muted line-through">{d.requirement_id}</span>
                <span className="text-muted">{byId.get(d.requirement_id)?.text ?? ""}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="rule mb-3 flex items-baseline justify-between pt-2">
            <SubHead>Edited</SubHead>
            <span className="font-mono text-[11px] text-muted">{edited.length}</span>
          </div>
          {edited.length === 0 && <p className="text-muted">None.</p>}
          <ul className="space-y-2">
            {edited.map((d) => {
              const r = byId.get(d.requirement_id);
              return (
                <li key={d.requirement_id} className="grid grid-cols-[3.5rem_1fr] items-start gap-x-2 text-[15px]">
                  <CiteChip id={d.requirement_id} />
                  <span>
                    {r?.text}
                    <span className="mt-0.5 block font-mono text-[11px] text-muted">
                      {d.strictness && `${r?.strictness ?? "?"} → ${d.strictness}`}
                      {d.strictness && d.type && " · "}
                      {d.type && `${r ? TYPE_LABELS[r.type] : "?"} → ${TYPE_LABELS[d.type]}`}
                    </span>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      <section>
        <div className="rule mb-3 flex items-baseline justify-between pt-2">
          <SubHead>Pursuit brief</SubHead>
          <span className="font-mono text-[11px] text-muted">{record.brief?.chunks.length ?? 0} paragraphs</span>
        </div>
        {!record.brief && <p className="text-muted">No brief: the draft rests on the RFP alone.</p>}
        <ol>
          {record.brief?.chunks.map((ch) => (
            <li key={ch.id} className="hair grid grid-cols-[3.5rem_1fr] items-start gap-x-2 py-2">
              <span className="font-mono text-xs text-accent">{ch.id}</span>
              <span className="whitespace-pre-line text-[15px]">{ch.text}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
