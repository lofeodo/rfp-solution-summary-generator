import { useState } from "react";
import { Link } from "react-router-dom";
import type { RunListItem, RunState } from "../api/types";
import { STAGES } from "../lib/stages";
import { prettySource, secs, usd, when } from "../lib/format";
import { StateBadge, Tag } from "./ui";

// A run with a job queued or in flight cannot be removed (the server answers 409).
const BUSY: ReadonlySet<RunState> = new Set<RunState>(["queued", "running", "drafting", "refining"]);
const CONTROL_COL = "flex w-20 shrink-0 flex-col items-end justify-center gap-1 break-words py-3 pl-3 text-right";

interface Props {
  runs: RunListItem[];
  /** Remove a run; omitted for the samples, which are read-only. Rejects with a message. */
  onRemove?: (runId: string) => Promise<void>;
}

export default function RunList({ runs, onRemove }: Props) {
  if (runs.length === 0) return <p className="text-muted">No runs yet.</p>;
  return (
    <ol>
      {runs.map((r, i) => (
        <li key={r.run_id} className={`flex items-stretch transition-colors hover:bg-white/60 ${i === 0 ? "rule" : "hair"}`}>
          <Link
            to={`/runs/${r.run_id}`}
            className="group grid min-w-0 flex-1 grid-cols-12 items-baseline gap-x-4 gap-y-1 py-3"
          >
            <span className="col-span-1 hidden font-mono text-xs text-muted md:block">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="col-span-12 min-w-0 md:col-span-6">
              <span className="block truncate font-display text-2xl font-semibold tracking-tight group-hover:text-accent">
                {prettySource(r.source_name)}
              </span>
              <span className="font-mono text-[11px] text-muted">
                {r.run_id} · {when(r.started_at)}
              </span>
            </span>
            <span className="col-span-12 flex flex-wrap items-center gap-2 md:col-span-2">
              <StateBadge state={r.status} />
              {r.sample && <Tag>sample</Tag>}
            </span>
            <span className="col-span-12 grid grid-cols-3 gap-2 whitespace-nowrap font-mono text-xs md:col-span-3 md:text-right">
              <span>{usd(r.cost_usd)}</span>
              <span>{secs(r.latency_s)}</span>
              <span className="text-muted">
                {r.stages_done}/{STAGES.length}
              </span>
            </span>
          </Link>
          {/* Every row keeps the column, so the samples list lines up with the own runs. */}
          <div className={CONTROL_COL}>{onRemove && !r.sample && <RemoveControl run={r} onRemove={onRemove} />}</div>
        </li>
      ))}
    </ol>
  );
}

// Two clicks: "Remove" asks, "Yes" deletes. The run's files go with it.
function RemoveControl({ run, onRemove }: { run: RunListItem; onRemove: (runId: string) => Promise<void> }) {
  const [asking, setAsking] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const busy = BUSY.has(run.status);
  const name = prettySource(run.source_name);

  async function remove() {
    setSending(true);
    setError(null);
    try {
      await onRemove(run.run_id); // on success the row unmounts
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setSending(false);
      setAsking(false);
    }
  }

  const link = "font-mono text-[11px] uppercase tracking-wider underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <>
      {asking ? (
        <span className="flex flex-col items-end gap-0.5">
          <span className="font-mono text-[11px] text-muted">Remove?</span>
          <span className="flex gap-2">
            <button type="button" className={`${link} text-accent`} disabled={sending} onClick={remove} aria-label={`Confirm removing ${name}`}>
              {sending ? "…" : "Yes"}
            </button>
            <button type="button" className={link} disabled={sending} onClick={() => setAsking(false)}>
              No
            </button>
          </span>
        </span>
      ) : (
        <button
          type="button"
          className={`${link} text-muted hover:text-accent`}
          disabled={busy}
          title={busy ? "Wait for the current job to finish" : "Delete this run and its files"}
          aria-label={`Remove ${name}`}
          onClick={() => setAsking(true)}
        >
          Remove
        </button>
      )}
      {error && <span className="font-mono text-[10px] text-accent">{error}</span>}
    </>
  );
}
