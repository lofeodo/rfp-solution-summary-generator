import { useEffect, useState } from "react";
import type { RunTotals } from "../api/types";
import { stageRows, type StageMap, type StageState } from "../lib/stages";
import { secs, tokens, usd } from "../lib/format";

function Marker({ state }: { state: StageState }) {
  const cls = {
    pending: "border border-hair",
    running: "bg-accent animate-pulse",
    finished: "bg-ink",
    failed: "bg-accent",
  }[state];
  return (
    <span className={`mt-2 inline-flex h-3 w-3 shrink-0 items-center justify-center ${cls}`} aria-label={state}>
      {state === "failed" && <span className="font-mono text-[9px] leading-none text-paper">×</span>}
    </span>
  );
}

// Re-render once a second while a stage runs so its elapsed time ticks.
function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [active]);
  return now;
}

export default function StageTimeline({
  stages,
  totals,
  live,
}: {
  stages: StageMap;
  totals: RunTotals | null;
  live: boolean;
}) {
  const rows = stageRows(stages);
  const now = useNow(rows.some((r) => r.state === "running"));
  return (
    <div>
      <p className="kicker mb-2">
        Pipeline {live && <span className="text-accent">· live</span>}
      </p>
      <ol className="rule">
        {rows.map((r, i) => {
          const ev = r.event;
          const elapsed =
            r.state === "running" && ev ? Math.max(0, (now - Date.parse(ev.started_at)) / 1000) : (ev?.latency_s ?? null);
          return (
            <li
              key={r.id}
              className={`hair flex gap-3 py-2.5 ${r.parallel ? "border-l-2 border-l-accent pl-2" : ""} ${
                r.state === "pending" ? "text-muted" : ""
              }`}
            >
              <Marker state={r.state} />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-display text-lg font-semibold leading-tight tracking-tight">
                    <span className="mr-1.5 font-mono text-[10px] font-normal text-muted">{i + 1}</span>
                    {r.label}
                  </span>
                  <span className="font-mono text-xs tabular-nums">{r.state === "pending" ? "" : secs(elapsed)}</span>
                </div>
                <div className="font-mono text-[10px] text-muted">
                  {r.state === "finished" && ev && ev.calls > 0
                    ? `${ev.calls} calls · ${tokens(ev.totals.input_tokens + ev.totals.output_tokens)} tok · ${usd(ev.totals.cost_usd)}`
                    : r.parallel && r.state !== "finished"
                      ? `${r.what} · parallel`
                      : r.what}
                </div>
                {ev?.error && <p className="mt-1 font-mono text-[11px] text-accent">{ev.error}</p>}
              </div>
            </li>
          );
        })}
      </ol>
      {totals && (
        <dl className="rule mt-0 grid grid-cols-2 gap-x-4 gap-y-2 pt-3 font-mono text-xs">
          <dt className="kicker">Cost</dt>
          <dd className="text-right">{usd(totals.cost_usd)}</dd>
          <dt className="kicker">Tokens in</dt>
          <dd className="text-right">{tokens(totals.input_tokens)}</dd>
          <dt className="kicker">cached</dt>
          <dd className="text-right">{tokens(totals.cached_input_tokens)}</dd>
          <dt className="kicker">Tokens out</dt>
          <dd className="text-right">{tokens(totals.output_tokens)}</dd>
          <dt className="kicker">Retries</dt>
          <dd className="text-right">{totals.retries}</dd>
        </dl>
      )}
    </div>
  );
}
