import { useCallback, useMemo, useState } from "react";
import { Link, NavLink, useParams } from "react-router-dom";
import { api } from "../api/client";
import Masthead from "../components/Masthead";
import SourcePanel from "../components/SourcePanel";
import StageTimeline from "../components/StageTimeline";
import { SourceContext, type SourceCtx } from "../components/source";
import { StateBadge } from "../components/ui";
import { useRun } from "../hooks/useRun";
import { useRunData } from "../hooks/useRunData";
import { secs, usd, when } from "../lib/format";
import SolutionView from "./SolutionView";
import RequirementsView from "./RequirementsView";
import RisksView from "./RisksView";
import ProblemView from "./ProblemView";
import ParseView from "./ParseView";
import MetricsView from "./MetricsView";

const TABS = [
  { id: "solution", label: "Solution" },
  { id: "requirements", label: "Requirements" },
  { id: "risks", label: "Risks" },
  { id: "problem", label: "Problem" },
  { id: "parse", label: "Parse & chunks" },
  { id: "metrics", label: "Metrics" },
] as const;

export default function RunPage() {
  const { id = "", tab = "solution" } = useParams();
  const { status, stages, error } = useRun(id);
  const data = useRunData(id, status);
  const [stack, setStack] = useState<string[]>([]);

  const open = useCallback((target: string) => setStack((s) => (s[s.length - 1] === target ? s : [...s, target])), []);
  const ctx: SourceCtx = useMemo(() => ({ runId: id, index: data.index, open }), [id, data.index, open]);

  if (error)
    return (
      <main className="mx-auto max-w-screen-2xl px-4 py-6 md:px-10">
        <Masthead compact />
        <p className="display mt-16 text-5xl">Run not found.</p>
        <p className="mt-4 font-mono text-sm text-muted">{error}</p>
      </main>
    );

  const title = data.parsed?.title || status?.source_name.replace(/\.pdf$/i, "") || id;
  const done = status?.artifacts.includes("summary") ?? false;
  const counts: Record<string, number | undefined> = {
    requirements: data.requirements?.requirements.length,
    risks: data.risks?.assessment.risks.length,
  };

  return (
    <SourceContext.Provider value={ctx}>
      <main className="mx-auto max-w-screen-2xl px-4 pb-24 pt-4 md:px-10">
        <Masthead compact />

        <header className="grid grid-cols-12 gap-x-10 gap-y-4 pb-6 pt-8">
          <div className="col-span-12 lg:col-span-9">
            <div className="flex flex-wrap items-center gap-3">
              {status && <StateBadge state={status.status} />}
              <span className="font-mono text-[11px] text-muted">
                {id} · {status?.model ?? "—"} · {when(status?.started_at ?? null)}
              </span>
            </div>
            <h1 className="display mt-3 max-w-[22ch] text-[clamp(2rem,4.2vw,3.75rem)] [overflow-wrap:anywhere]">{title}</h1>
            {status?.error && (
              <p className="mt-3 border-l-4 border-accent bg-accentsoft px-3 py-2 font-mono text-xs">{status.error}</p>
            )}
          </div>
          <div className="col-span-12 flex flex-col gap-3 lg:col-span-3 lg:items-end lg:justify-end">
            <div className="flex gap-6 font-mono text-sm">
              <span>
                <span className="kicker block">Cost</span>
                {usd(status?.totals.cost_usd ?? 0)}
              </span>
              <span>
                <span className="kicker block">Wall</span>
                {secs(runWall(status?.started_at, status?.finished_at))}
              </span>
              <span>
                <span className="kicker block">Calls</span>
                {status?.nodes.length || "—"}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <a className={`btn ${done ? "" : "pointer-events-none opacity-40"}`} href={api.downloadUrl(id, "summary.md")}>
                ↓ .md
              </a>
              <a className={`btn ${done ? "" : "pointer-events-none opacity-40"}`} href={api.downloadUrl(id, "summary.json")}>
                ↓ .json
              </a>
              <a className="btn" href={api.pdfUrl(id)} target="_blank" rel="noreferrer">
                PDF ↗
              </a>
              {status?.langfuse_trace_url && (
                <a className="btn btn-accent" href={status.langfuse_trace_url} target="_blank" rel="noreferrer">
                  Trace ↗
                </a>
              )}
            </div>
          </div>
        </header>

        <div className="grid grid-cols-12 gap-x-10 gap-y-10">
          <aside className="col-span-12 lg:col-span-3">
            <div className="lg:sticky lg:top-6">
              <StageTimeline
                stages={stages}
                totals={status?.totals ?? null}
                live={status?.status === "running" || status?.status === "queued"}
              />
            </div>
          </aside>

          <section className="col-span-12 min-w-0 lg:col-span-9">
            <nav
              className="mb-8 flex gap-x-5 overflow-x-auto overflow-y-hidden border-b-2 border-ink [scrollbar-width:none]"
              aria-label="Outputs"
            >
              {TABS.map((t) => (
                <NavLink
                  key={t.id}
                  to={`/runs/${id}/${t.id}`}
                  className={() =>
                    `whitespace-nowrap border-b-4 pb-1.5 pt-1 font-display text-lg font-semibold tracking-tight transition-colors ${
                      tab === t.id ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"
                    }`
                  }
                >
                  {t.label}
                  {counts[t.id] !== undefined && (
                    <sup className="ml-0.5 font-mono text-[10px] font-normal text-muted">{counts[t.id]}</sup>
                  )}
                </NavLink>
              ))}
            </nav>
            {tab === "solution" && <SolutionView data={data} />}
            {tab === "requirements" && <RequirementsView data={data} />}
            {tab === "risks" && <RisksView data={data} />}
            {tab === "problem" && <ProblemView data={data} />}
            {tab === "parse" && <ParseView data={data} />}
            {tab === "metrics" && <MetricsView status={status} stages={stages} />}
            {!TABS.some((t) => t.id === tab) && (
              <p className="text-muted">
                Unknown view. <Link to={`/runs/${id}`}>Back to the solution</Link>.
              </p>
            )}
          </section>
        </div>
      </main>
      <SourcePanel stack={stack} onBack={() => setStack((s) => s.slice(0, -1))} onClose={() => setStack([])} />
    </SourceContext.Provider>
  );
}

function runWall(start?: string | null, end?: string | null): number | null {
  if (!start || !end) return null;
  return (Date.parse(end) - Date.parse(start)) / 1000;
}
