import { useState } from "react";
import { CiteChip } from "../components/source";
import { SectionHead, Waiting } from "../components/ui";
import type { RunData } from "../hooks/useRunData";
import { ProblemStatementBlock } from "./SolutionView";

export default function ProblemView({ data }: { data: RunData }) {
  const [onlyRelevant, setOnlyRelevant] = useState(false);
  const p = data.problem;
  if (!p) return <Waiting what="The problem stage has not finished." loading={data.has("problem")} />;
  const sums = onlyRelevant ? p.chunk_summaries.filter((s) => s.relevant) : p.chunk_summaries;
  const relevant = p.chunk_summaries.filter((s) => s.relevant).length;

  return (
    <div className="space-y-16">
      <section>
        <SectionHead n="05" title="Problem statement" aside={`mode: ${p.mode}`} />
        <ProblemStatementBlock statement={p.statement} />
      </section>
      <section>
        <SectionHead
          n="06"
          title="Chunk summaries"
          aside={
            <label className="flex cursor-pointer items-center gap-2">
              <input type="checkbox" className="accent-accent" checked={onlyRelevant} onChange={(e) => setOnlyRelevant(e.target.checked)} />
              relevant only ({relevant}/{p.chunk_summaries.length})
            </label>
          }
        />
        {p.chunk_summaries.length === 0 ? (
          <p className="text-muted">Full-text mode writes no per-chunk summaries.</p>
        ) : (
          <ul>
            {sums.map((s) => (
              <li key={s.chunk_id} className={`hair grid grid-cols-[4.5rem_1fr] gap-x-3 py-2.5 ${s.relevant ? "" : "text-muted"}`}>
                <span>
                  <CiteChip id={s.chunk_id} />
                </span>
                <span className="text-[15px]">
                  {s.summary || <em>empty</em>}
                  {s.error && <span className="ml-2 font-mono text-[11px] text-accent">{s.error}</span>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
