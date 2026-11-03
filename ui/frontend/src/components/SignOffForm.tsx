import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { SignOff } from "../api/types";
import { useReview } from "../hooks/useReview";
import { when } from "../lib/format";
import { ARTEFACT_LABEL, signOffBlockers } from "../lib/revisions";
import { Alert, INPUT, ReviewerField } from "./ReviewControls";
import { SubHead } from "./ui";

// Freeze the run under a reviewer's name (ST12e). The button explains what blocks it;
// the server re-checks (409 when something went stale meanwhile).
export default function SignOffForm() {
  const review = useReview();
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!review) return null;
  const { status } = review;
  if (status.review.sign_off) return <SignOffRecord s={status.review.sign_off} />;
  const reviewer = review.reviewer.trim();
  const blockers = signOffBlockers(status.status, status.review);
  const allowed = status.review.allowed.sign_off;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      await api.signOff(review!.runId, { reviewer, note: note.trim() || null });
      review!.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="border-2 border-ink p-4 md:p-6">
      <form onSubmit={submit} className="grid gap-x-10 gap-y-5 lg:grid-cols-[1fr_auto]">
        <div className="space-y-4">
          <SubHead>Sign off</SubHead>
          <p className="max-w-prose text-[15px] text-muted">
            Freezes every artefact at its current version under your name. Nothing can be revised or regenerated after;
            the summary carries the review history.
          </p>
          <ReviewerField />
          <label className="block max-w-prose">
            <span className="kicker">Note for the record (optional)</span>
            <input className={INPUT} value={note} onChange={(e) => setNote(e.target.value)} maxLength={5000} disabled={!allowed} />
          </label>
          {blockers.length > 0 && (
            <ul className="space-y-1 font-mono text-xs">
              {blockers.map((b) => (
                <li key={b} className="text-accent">
                  × {b}
                </li>
              ))}
            </ul>
          )}
          {error && <Alert>{error}</Alert>}
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            className="btn btn-accent w-full justify-center px-6 py-3 text-sm"
            disabled={!allowed || sending || !reviewer}
          >
            {sending ? "Signing off…" : "Sign off →"}
          </button>
        </div>
      </form>
    </section>
  );
}

function SignOffRecord({ s }: { s: SignOff }) {
  return (
    <section className="border-2 border-ink bg-ink p-4 text-paper md:p-6">
      <p className="kicker text-paper/70">Signed off · frozen</p>
      <p className="mt-2 font-display text-3xl font-semibold tracking-tight">{s.reviewer}</p>
      <p className="mt-1 font-mono text-xs">{when(s.signed_at)}</p>
      {s.note && <p className="mt-3 max-w-prose text-[15px]">{s.note}</p>}
      <p className="mt-3 font-mono text-[11px]">
        {Object.entries(s.versions)
          .map(([a, v]) => `${ARTEFACT_LABEL[a as keyof typeof ARTEFACT_LABEL] ?? a} v${v}`)
          .join(" · ")}
      </p>
    </section>
  );
}
