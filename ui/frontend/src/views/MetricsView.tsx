import { useMemo } from "react";
import type { NodeMetrics, RunStatus } from "../api/types";
import { SectionHead, SubHead, Waiting } from "../components/ui";
import { secs, tokens, usd } from "../lib/format";
import { stageRows, type StageMap } from "../lib/stages";

interface NodeAgg {
  node: string;
  calls: number;
  input: number;
  cached: number;
  output: number;
  cost: number;
  latency: number;
  maxLatency: number;
  retries: number;
}

// Node names carry a per-chunk suffix (e.g. requirements:S3.2); group by the part before it.
function nodeGroup(n: NodeMetrics): string {
  return n.node.split(/[:[]/)[0];
}

function aggregate(nodes: NodeMetrics[]): NodeAgg[] {
  const m = new Map<string, NodeAgg>();
  for (const n of nodes) {
    const k = nodeGroup(n);
    const a = m.get(k) ?? { node: k, calls: 0, input: 0, cached: 0, output: 0, cost: 0, latency: 0, maxLatency: 0, retries: 0 };
    a.calls++;
    a.input += n.input_tokens;
    a.cached += n.cached_input_tokens;
    a.output += n.output_tokens;
    a.cost += n.cost_usd;
    a.latency += n.latency_s;
    a.maxLatency = Math.max(a.maxLatency, n.latency_s);
    a.retries += n.retries;
    m.set(k, a);
  }
  return [...m.values()].sort((a, b) => b.cost - a.cost);
}

// Single-series horizontal bars: one measure per chart, ink marks, value labelled at the end.
function Bars({ rows, fmt, label }: { rows: { key: string; label: string; value: number }[]; fmt: (v: number) => string; label: string }) {
  const max = Math.max(...rows.map((r) => r.value), 1e-9);
  return (
    <figure>
      <figcaption className="kicker mb-2">{label}</figcaption>
      <ul className="space-y-1.5">
        {rows.map((r) => (
          <li key={r.key} className="grid grid-cols-[6.5rem_1fr] items-center gap-x-3 text-sm" title={`${r.label}: ${fmt(r.value)}`}>
            <span className="truncate font-display font-semibold tracking-tight">{r.label}</span>
            <span className="flex items-center gap-2">
              <span className="h-3 rounded-r bg-ink" style={{ width: `${Math.max(0.5, (r.value / max) * 80)}%` }} />
              <span className="font-mono text-[11px] tabular-nums">{fmt(r.value)}</span>
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

export default function MetricsView({ status, stages }: { status: RunStatus | null; stages: StageMap }) {
  const groups = useMemo(() => aggregate(status?.nodes ?? []), [status?.nodes]);
  const rows = stageRows(stages).filter((r) => r.event && r.state !== "running");
  if (!status) return <Waiting what="Loading run status." />;
  const t = status.totals;

  return (
    <div className="space-y-16">
      <section>
        <SectionHead n="09" title="Metrics" aside={`${status.nodes.length} LLM calls`} />
        <dl className="grid grid-cols-2 gap-x-6 gap-y-6 border-b border-hair pb-8 md:grid-cols-5">
          {[
            ["Cost", usd(t.cost_usd)],
            ["Input tokens", tokens(t.input_tokens)],
            [
              "Cached input",
              <>
                {tokens(t.cached_input_tokens)}
                <span className="ml-1 font-mono text-sm font-normal tracking-normal text-muted">
                  {t.input_tokens ? Math.round((t.cached_input_tokens / t.input_tokens) * 100) : 0}%
                </span>
              </>,
            ],
            ["Output tokens", tokens(t.output_tokens)],
            ["Retries", String(t.retries)],
          ].map(([k, v]) => (
            <div key={k as string}>
              <dt className="kicker">{k}</dt>
              <dd className="display mt-1 text-4xl">{v}</dd>
            </div>
          ))}
        </dl>
        {rows.length === 0 ? (
          <Waiting what="No stage has finished yet." />
        ) : (
          <div className="mt-8 grid gap-x-12 gap-y-10 xl:grid-cols-2">
            <Bars label="Wall time per stage" fmt={secs} rows={rows.map((r) => ({ key: r.id, label: r.label, value: r.event!.latency_s }))} />
            <Bars
              label="Cost per stage"
              fmt={usd}
              rows={rows.map((r) => ({ key: r.id, label: r.label, value: r.event!.totals?.cost_usd ?? 0 }))}
            />
          </div>
        )}
      </section>

      <section>
        <div className="rule mb-4 flex items-baseline justify-between pt-2">
          <SubHead>Per node</SubHead>
          <span className="kicker">{status.nodes.length ? "from run_log.json" : "available when the run ends"}</span>
        </div>
        {groups.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] border-collapse text-right font-mono text-xs tabular-nums">
              <thead>
                <tr className="border-b-2 border-ink">
                  {["Node", "Calls", "In", "Cached", "Out", "Cost", "Σ latency", "Max", "Retries"].map((h, i) => (
                    <th key={h} className={`kicker py-1.5 font-normal ${i === 0 ? "text-left" : ""}`}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => (
                  <tr key={g.node} className="border-b border-hair">
                    <td className="py-1.5 text-left font-semibold">{g.node}</td>
                    <td>{g.calls}</td>
                    <td>{tokens(g.input)}</td>
                    <td className="text-muted">{tokens(g.cached)}</td>
                    <td>{tokens(g.output)}</td>
                    <td>{usd(g.cost)}</td>
                    <td>{secs(g.latency)}</td>
                    <td className="text-muted">{secs(g.maxLatency)}</td>
                    <td className={g.retries ? "text-accent" : "text-muted"}>{g.retries}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-3 text-sm text-muted">
          Σ latency adds call latencies; it exceeds wall time where calls run concurrently.
          {status.langfuse_trace_url ? (
            <>
              {" "}
              <a className="underline decoration-accent" href={status.langfuse_trace_url} target="_blank" rel="noreferrer">
                Open the Langfuse trace ↗
              </a>
            </>
          ) : (
            " No Langfuse trace for this run (keys absent)."
          )}
        </p>
      </section>
    </div>
  );
}
