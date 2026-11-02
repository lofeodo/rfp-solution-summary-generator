import type { Claim, ProblemStatement } from "../api/types";
import { Chips, CiteChip, useSource } from "../components/source";
import { SectionHead, SubHead, Tag, Waiting } from "../components/ui";
import type { RunData } from "../hooks/useRunData";

export function ClaimList({ claims }: { claims: Claim[] }) {
  return (
    <ul className="space-y-2.5">
      {claims.map((c, i) => (
        <li key={i} className="grid grid-cols-[1.25rem_1fr] gap-x-1">
          <span className="pt-0.5 font-mono text-[11px] text-muted">{c.kind === "inference" ? "≈" : "—"}</span>
          <span>
            {c.kind === "inference" && <span className="mr-1.5 align-middle"><Tag>inference</Tag></span>}
            {c.text} <Chips ids={c.chunk_ids} />
          </span>
        </li>
      ))}
    </ul>
  );
}

const PROBLEM_PARTS: { key: keyof ProblemStatement; title: string }[] = [
  { key: "client_situation", title: "Client situation" },
  { key: "goal", title: "Goal" },
  { key: "success_criteria", title: "Success criteria" },
  { key: "constraints", title: "Constraints" },
];

export function ProblemStatementBlock({ statement }: { statement: ProblemStatement }) {
  return (
    <div className="grid gap-x-10 gap-y-8 xl:grid-cols-2">
      {PROBLEM_PARTS.map((p) => (
        <div key={p.key}>
          <div className="hair mb-3 flex items-baseline justify-between pt-2">
            <SubHead>{p.title}</SubHead>
            <span className="font-mono text-[11px] text-muted">{statement[p.key].length}</span>
          </div>
          <ClaimList claims={statement[p.key]} />
        </div>
      ))}
    </div>
  );
}

export default function SolutionView({ data }: { data: RunData }) {
  const { open } = useSource();
  const sol = data.solution?.solution;
  return (
    <div className="space-y-16">
      <section>
        <SectionHead n="01" title="Proposed solution" aside={sol ? `${sol.components.length} components` : undefined} />
        {!sol ? (
          <Waiting what="The solution stage has not finished." loading={data.has("solution")} />
        ) : (
          <>
            <div className="grid grid-cols-12 lg:gap-x-10 gap-y-6">
              <p className="col-span-12 max-w-[62ch] text-lg leading-relaxed first-letter:float-left first-letter:mr-1 first-letter:mt-1 first-letter:font-display first-letter:text-[3.4em] first-letter:font-extrabold first-letter:leading-[0.8] first-letter:text-accent md:text-xl xl:col-span-8">
                {sol.summary}
              </p>
              <Coverage data={data} />
            </div>

            <ol className="mt-12 grid gap-x-10 gap-y-10 xl:grid-cols-2">
              {sol.components.map((c) => (
                <li key={c.id} className="rule pt-3">
                  <button type="button" onClick={() => open(c.id)} className="group text-left">
                    <span className="font-mono text-sm text-accent">{c.id}</span>
                    <h3 className="mt-1 font-display text-2xl font-semibold leading-tight tracking-tight group-hover:text-accent">
                      {c.title}
                    </h3>
                  </button>
                  <p className="mt-3">{c.description}</p>
                  <div className="mt-3">
                    <Chips label="Addresses" ids={c.requirement_ids} />
                  </div>
                  {c.claims.length > 0 && (
                    <div className="mt-4 text-[15px]">
                      <ClaimList claims={c.claims} />
                    </div>
                  )}
                </li>
              ))}
            </ol>

            <div className="mt-12">
              <div className="hair mb-3 pt-2">
                <SubHead>Assumptions</SubHead>
              </div>
              <ClaimList claims={sol.assumptions} />
            </div>
          </>
        )}
      </section>

      <section>
        <SectionHead n="02" title="Problem statement" aside={data.problem ? `mode: ${data.problem.mode}` : undefined} />
        {data.problem ? <ProblemStatementBlock statement={data.problem.statement} /> : <Waiting what="The problem stage has not finished." loading={data.has("problem")} />}
      </section>
    </div>
  );
}

function Coverage({ data }: { data: RunData }) {
  const s = data.solution!;
  const cov = s.solution.coverage;
  const pct = cov.mandatory_total ? cov.mandatory_covered / cov.mandatory_total : 1;
  return (
    <div className="col-span-12 xl:col-span-4">
      <p className="kicker">Mandatory coverage</p>
      <p className="display mt-1 text-6xl">
        {cov.mandatory_covered}
        <span className="text-muted">/{cov.mandatory_total}</span>
      </p>
      <div className="mt-2 h-2 w-full bg-hair" role="img" aria-label={`${Math.round(pct * 100)}% covered`}>
        <div className="h-2 bg-ink" style={{ width: `${pct * 100}%` }} />
      </div>
      {s.rounds.length > 0 && (
        <p className="mt-2 font-mono text-[11px] text-muted">
          {s.rounds.map((r) => `round ${r.iteration}: ${r.coverage.mandatory_covered}/${r.coverage.mandatory_total}`).join(" → ")}
        </p>
      )}
      {cov.uncovered_requirement_ids.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          <span className="kicker mr-1 text-accent">Uncovered</span>
          {cov.uncovered_requirement_ids.map((id) => (
            <CiteChip key={id} id={id} />
          ))}
        </div>
      )}
    </div>
  );
}
