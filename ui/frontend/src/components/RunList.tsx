import { Link } from "react-router-dom";
import type { RunListItem } from "../api/types";
import { STAGES } from "../lib/stages";
import { secs, usd, when } from "../lib/format";
import { StateBadge, Tag } from "./ui";

export function displayName(source: string): string {
  return source.replace(/\.pdf$/i, "").replace(/[_-]+/g, " ");
}

export default function RunList({ runs }: { runs: RunListItem[] }) {
  if (runs.length === 0) return <p className="text-muted">No runs yet.</p>;
  return (
    <ol>
      {runs.map((r, i) => (
        <li key={r.run_id} className={i === 0 ? "rule" : "hair"}>
          <Link
            to={`/runs/${r.run_id}`}
            className="group grid grid-cols-12 items-baseline gap-x-4 gap-y-1 py-3 transition-colors hover:bg-white/60"
          >
            <span className="col-span-1 hidden font-mono text-xs text-muted md:block">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="col-span-12 min-w-0 md:col-span-6">
              <span className="block truncate font-display text-2xl font-semibold tracking-tight group-hover:text-accent">
                {displayName(r.source_name)}
              </span>
              <span className="font-mono text-[11px] text-muted">
                {r.run_id} · {when(r.started_at)}
              </span>
            </span>
            <span className="col-span-12 flex flex-wrap items-center gap-2 md:col-span-2">
              <StateBadge state={r.status} />
              {r.sample && <Tag>sample</Tag>}
            </span>
            <span className="col-span-12 grid grid-cols-3 gap-2 font-mono text-xs md:col-span-3 md:text-right">
              <span>{usd(r.cost_usd)}</span>
              <span>{secs(r.latency_s)}</span>
              <span className="text-muted">
                {r.stages_done}/{STAGES.length}
              </span>
            </span>
          </Link>
        </li>
      ))}
    </ol>
  );
}
