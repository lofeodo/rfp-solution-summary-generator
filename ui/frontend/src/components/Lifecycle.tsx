import { Link } from "react-router-dom";
import type { ReviewState, RunState } from "../api/types";
import { PHASES, lifecycle, phaseIndex, refineNote } from "../lib/lifecycle";

// Where the run stands in the human loop, and what happens next (ST12d).
export default function Lifecycle({
  runId,
  state,
  review,
  tab,
}: {
  runId: string;
  state: RunState;
  review?: ReviewState | null;
  tab: string;
}) {
  const lc = lifecycle(state);
  const note = refineNote(state, review);
  const at = phaseIndex(lc.phase);
  const yourTurn = state === "awaiting_checkpoint";
  return (
    <div className={`border-y-2 border-ink py-2.5 ${yourTurn ? "bg-accentsoft" : ""}`} aria-label="Run lifecycle">
      <ol className="flex flex-wrap items-center gap-x-1 gap-y-1 font-mono text-[11px] uppercase tracking-wider">
        {PHASES.map((p, i) => (
          <li key={p.id} className="flex items-center gap-1">
            {i > 0 && <span className={i <= at ? "text-ink" : "text-hair"}>──</span>}
            <span
              aria-current={i === at ? "step" : undefined}
              className={`inline-flex items-center gap-1.5 border px-1.5 py-px ${
                i === at ? "border-accent bg-accent text-paper" : i < at ? "border-ink text-ink" : "border-hair text-muted"
              }`}
            >
              {i === at && lc.busy && <span className="h-1.5 w-1.5 animate-pulse bg-paper" />}
              {i < at && "✓ "}
              {p.label}
            </span>
          </li>
        ))}
      </ol>
      <p className="mt-2 flex flex-wrap items-baseline gap-x-3 text-[15px]">
        <span className={yourTurn ? "font-semibold" : ""}>{lc.next}</span>
        {yourTurn && tab !== "checkpoint" && (
          <Link to={`/runs/${runId}/checkpoint`} className="btn btn-accent py-0.5">
            Open the checkpoint →
          </Link>
        )}
        {note && <span className={review?.stale.length ? "text-accent" : "font-semibold"}>{note}</span>}
        {note && tab !== "review" && (
          <Link to={`/runs/${runId}/review`} className="btn py-0.5">
            {review?.stale.length ? "Open the review →" : "Sign off →"}
          </Link>
        )}
      </p>
    </div>
  );
}
