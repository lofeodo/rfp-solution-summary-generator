import type { ReactNode } from "react";
import type { Level, RunState } from "../api/types";

export function SectionHead({ n, title, aside }: { n: string; title: string; aside?: ReactNode }) {
  return (
    <header className="rule mb-6 flex flex-wrap items-baseline gap-x-4 gap-y-1 pt-3">
      <span className="font-mono text-sm text-accent">{n}</span>
      <h2 className="display text-4xl md:text-5xl">{title}</h2>
      {aside && <div className="ml-auto kicker">{aside}</div>}
    </header>
  );
}

export function SubHead({ children }: { children: ReactNode }) {
  return <h3 className="font-display text-xl font-semibold tracking-tight">{children}</h3>;
}

const LEVEL_CLS: Record<Level, string> = {
  high: "bg-accent text-paper border-accent",
  medium: "border-ink text-ink",
  low: "border-hair text-muted",
};

export function LevelBadge({ level, label }: { level: Level; label?: string }) {
  return (
    <span className={`inline-block border px-1.5 py-px font-mono text-[10px] uppercase tracking-wider ${LEVEL_CLS[level]}`}>
      {label ? `${label} ` : ""}
      {level}
    </span>
  );
}

const STATE_CLS: Record<RunState, string> = {
  queued: "border-hair text-muted",
  running: "border-accent text-accent",
  finished: "border-ink text-ink",
  failed: "bg-accent border-accent text-paper",
};

export function StateBadge({ state }: { state: RunState }) {
  return (
    <span className={`inline-flex items-center gap-1.5 border px-1.5 py-px font-mono text-[10px] uppercase tracking-wider ${STATE_CLS[state]}`}>
      {state === "running" && <span className="h-1.5 w-1.5 animate-pulse bg-accent" />}
      {state}
    </span>
  );
}

export function Tag({ children, tone = "muted" }: { children: ReactNode; tone?: "muted" | "accent" | "ink" }) {
  const cls = { muted: "text-muted border-hair", accent: "text-accent border-accent", ink: "text-ink border-ink" }[tone];
  return <span className={`inline-block border px-1.5 py-px font-mono text-[10px] uppercase tracking-wider ${cls}`}>{children}</span>;
}

export function Waiting({ what, loading = false }: { what: string; loading?: boolean }) {
  return (
    <div className="hair py-10">
      <p className="kicker">{loading ? "Loading" : "Not yet"}</p>
      <p className="mt-2 font-display text-2xl text-muted">{loading ? "Fetching the output…" : what}</p>
    </div>
  );
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="kicker">{label}</div>
      <div className="truncate font-mono text-lg">{value}</div>
    </div>
  );
}
