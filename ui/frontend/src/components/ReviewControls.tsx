import { useState } from "react";
import { api } from "../api/client";
import type { Artefact } from "../api/types";
import { useReview } from "../hooks/useReview";
import { canRegenerate, stageOf } from "../lib/revisions";

export const INPUT =
  "block w-full border-b-2 border-ink bg-transparent py-1 font-mono text-sm placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-50";
export const AREA =
  "block w-full border-2 border-ink bg-white/40 p-3 font-serif text-[15px] leading-relaxed placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-50";

export function Alert({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="border-l-4 border-accent bg-accentsoft px-3 py-2 font-mono text-xs">
      {children}
    </p>
  );
}

export function ReviewerField({ disabled = false }: { disabled?: boolean }) {
  const review = useReview();
  if (!review) return null;
  return (
    <label className="block max-w-sm">
      <span className="kicker">Reviewing as</span>
      <input
        className={INPUT}
        value={review.reviewer}
        onChange={(e) => review.setReviewer(e.target.value)}
        placeholder="Your name"
        autoComplete="name"
        maxLength={200}
        disabled={disabled}
      />
    </label>
  );
}

// Re-runs the stage that writes `artefact` on the current inputs. Allowed only on a
// finished, unsigned run; the server re-checks.
export function RegenerateButton({ artefact, accent = false }: { artefact: Artefact; accent?: boolean }) {
  const review = useReview();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stage = stageOf(artefact);
  if (!review || !stage) return null;
  const reviewer = review.reviewer.trim();
  const allowed = canRegenerate(review.status.review, artefact);

  async function go() {
    if (!stage) return;
    setSending(true);
    setError(null);
    try {
      await api.regenerate(review!.runId, { reviewer, stage });
      review!.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        className={`btn ${accent ? "btn-accent" : ""}`}
        disabled={!allowed || sending || !reviewer}
        title={!reviewer ? "Enter your name first" : `Re-run the ${stage} stage on the current inputs`}
        onClick={go}
      >
        {sending ? "Sending…" : `Regenerate ${artefact}`}
      </button>
      {!reviewer && allowed && <span className="font-mono text-[11px] text-muted">Enter your name in “Reviewing as” first.</span>}
      {error && <Alert>{error}</Alert>}
    </span>
  );
}
