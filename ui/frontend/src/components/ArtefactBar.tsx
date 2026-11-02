import type { Artefact } from "../api/types";
import { useReview } from "../hooks/useReview";
import { when } from "../lib/format";
import { ARTEFACT_LABEL, stageOf } from "../lib/revisions";
import { Alert, RegenerateButton } from "./ReviewControls";

// The top of an artefact tab under review (ST12e): which version is shown, a read-only
// look at older ones, the stale banner with Regenerate, and the frozen note after sign-off.
export default function ArtefactBar({
  artefact,
  viewing,
  onView,
  loading,
  error,
}: {
  artefact: Artefact;
  viewing: number | null;
  onView: (n: number | null) => void;
  loading: boolean;
  error: string | null;
}) {
  const review = useReview();
  if (!review) return null;
  const rs = review.status.review;
  const v = rs.versions.artefacts[artefact];
  const current = v?.version ?? 1;
  const signed = rs.sign_off;
  const busy = review.status.status === "refining";

  return (
    <div className="mb-8 space-y-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-hair pb-2">
        <span className="kicker">{ARTEFACT_LABEL[artefact]} · version</span>
        <div className="flex flex-wrap gap-1" role="radiogroup" aria-label="Version">
          {Array.from({ length: current }, (_, i) => i + 1).map((n) => {
            const on = (viewing ?? current) === n;
            return (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => onView(n === current ? null : n)}
                className={`border px-1.5 py-px font-mono text-[11px] transition-colors ${
                  on ? "border-ink bg-ink text-paper" : "border-hair hover:border-ink"
                }`}
              >
                v{n}
                {n === current && current > 1 ? " · current" : ""}
              </button>
            );
          })}
        </div>
        {v?.updated_at && <span className="font-mono text-[11px] text-muted">updated {when(v.updated_at)}</span>}
        {busy && <span className="font-mono text-[11px] text-accent">a change is being applied…</span>}
      </div>

      {viewing !== null && (
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-l-4 border-ink bg-ink/5 px-3 py-2">
          <span className="font-mono text-xs">
            Viewing v{viewing} of {current}: read-only{loading ? ", loading…" : ""}.
          </span>
          <button type="button" className="kicker hover:text-accent" onClick={() => onView(null)}>
            back to the current version →
          </button>
          <span className="w-full font-mono text-[11px] text-muted">
            Citation chips still describe the current outputs.
          </span>
        </div>
      )}
      {error && <Alert>Could not load v{viewing}: {error}</Alert>}

      {v?.stale && !signed && (
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3 border-l-4 border-accent bg-accentsoft px-3 py-3">
          <div className="max-w-prose">
            <p className="kicker text-accent">Stale</p>
            <p className="mt-1 text-[15px]">
              {v.stale_because ?? "An input changed"}, so this may no longer match it.{" "}
              {stageOf(artefact)
                ? "Regenerate re-runs the stage on the current inputs; a revision below also clears it."
                : "A revision below clears it."}{" "}
              Sign-off waits until nothing is stale.
            </p>
          </div>
          <RegenerateButton artefact={artefact} accent />
        </div>
      )}

      {signed && (
        <p className="border-l-4 border-ink px-3 py-2 font-mono text-xs">
          Signed off by {signed.reviewer} {when(signed.signed_at)} at v{signed.versions[artefact] ?? current}. Frozen: no
          further changes.
        </p>
      )}
    </div>
  );
}
