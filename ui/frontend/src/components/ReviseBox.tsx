import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Artefact } from "../api/types";
import { useReview } from "../hooks/useReview";
import { usd } from "../lib/format";
import { historyOf, totalCost } from "../lib/revisions";
import { RevisionLine } from "./DiffView";
import { AREA, Alert, ReviewerField } from "./ReviewControls";
import { SectionHead } from "./ui";

const HINT: Record<Artefact, string> = {
  requirements: "e.g. Split R014 into the hosting and the support requirement; add the 99.9% uptime clause from section 4.2.",
  problem: "e.g. The goal should say the client wants to retire the mainframe, not just modernise it.",
  solution: "e.g. Add a component for migrating the legacy case data; drop the claim that we host on-premises.",
  risks: "e.g. Raise K03 to high severity: the penalty clause in section 7 applies from day one.",
};

// What a revision of each artefact sets off downstream (versions.DOWNSTREAM).
const CASCADE: Record<Artefact, string> = {
  requirements: "The solution and risks go stale until regenerated; removed requirements are dropped from them at once.",
  problem: "The solution and risks go stale until regenerated.",
  solution: "The risks go stale until regenerated.",
  risks: "Nothing downstream changes.",
};

// "Suggest edits" for one artefact (ST12e): an instruction the model applies under the
// stage's own checks, and this artefact's revisions with their diffs.
export default function ReviseBox({ artefact }: { artefact: Artefact }) {
  const review = useReview();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!review) return null;
  const { status, log } = review;
  const reviewer = review.reviewer.trim();
  const allowed = status.review.allowed.revise.includes(artefact);
  const busy = status.status === "refining";
  const signed = status.status === "signed_off";
  const history = historyOf(log, artefact);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      await api.revise(review!.runId, { reviewer, artefact, instruction: text.trim() });
      setText("");
      review!.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="mt-16">
      <SectionHead
        n="✎"
        title="Suggest edits"
        aside={history.length ? `${history.length} change${history.length > 1 ? "s" : ""} · ${usd(totalCost(history))}` : "model edits, checked by code"}
      />
      <div className="grid gap-x-10 gap-y-8 xl:grid-cols-2">
        {signed ? (
          <p className="text-muted">Signed off: this version is frozen.</p>
        ) : (
          <form onSubmit={submit} className="space-y-3">
            <p className="max-w-prose text-muted">
              Say what to change in plain words. The model rewrites, code checks the result (IDs kept, citations valid, no
              lost coverage) and a failed check leaves it as it was. {CASCADE[artefact]}
            </p>
            <ReviewerField disabled={busy} />
            <textarea
              className={`${AREA} min-h-28`}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={HINT[artefact]}
              disabled={busy || !allowed}
              aria-label={`Instruction for the ${artefact}`}
              maxLength={20000}
            />
            <div className="flex flex-wrap items-center gap-3">
              <button type="submit" className="btn btn-accent" disabled={!allowed || busy || sending || !reviewer || !text.trim()}>
                {busy ? "Applying…" : sending ? "Sending…" : "Apply instruction"}
              </button>
              {!reviewer && <span className="font-mono text-[11px] text-muted">Enter your name first.</span>}
              {!allowed && !busy && (
                <span className="font-mono text-[11px] text-muted">Not available while the run is {status.status.replace("_", " ")}.</span>
              )}
            </div>
            {error && <Alert>{error}</Alert>}
          </form>
        )}
        <div>
          <p className="kicker mb-2">Changes to the {artefact}</p>
          {busy && <p className="hair py-3 font-mono text-xs text-accent">A change is being applied…</p>}
          {history.length === 0 && !busy && <p className="hair py-3 text-muted">None yet: this is the drafted version.</p>}
          <ol className="rule">
            {history.map((r) => (
              <RevisionLine key={r.id} r={r} />
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
