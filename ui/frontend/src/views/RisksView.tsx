import { useMemo } from "react";
import { Chips, CiteChip, useSource } from "../components/source";
import { LevelBadge, SectionHead, SubHead, Tag, Waiting } from "../components/ui";
import type { RunData } from "../hooks/useRunData";
import { countBySeverity, sortRisks } from "../lib/risks";

export default function RisksView({ data }: { data: RunData }) {
  const { open } = useSource();
  const risks = useMemo(() => sortRisks(data.risks?.assessment.risks ?? []), [data.risks]);
  if (!data.risks) return <Waiting what="The risk stage has not finished." loading={data.has("risks")} />;
  const counts = countBySeverity(risks);
  const fnd = data.risks.findings;

  return (
    <div className="space-y-16">
      <section>
        <SectionHead
          n="04"
          title="Risks"
          aside={`${counts.high} high · ${counts.medium} medium · ${counts.low} low`}
        />
        <ol className="space-y-0">
          {risks.map((k) => (
            <li key={k.id} className="hair grid grid-cols-12 md:gap-x-6 gap-y-2 py-5">
              <div className="col-span-12 flex flex-wrap items-start gap-1.5 md:col-span-2 md:flex-col">
                <span className="font-mono text-sm text-accent">{k.id}</span>
                <LevelBadge level={k.severity} label="sev" />
                <LevelBadge level={k.likelihood} label="lik" />
                <Tag>{k.source === "rfp" ? "from RFP" : "from solution"}</Tag>
              </div>
              <div className="col-span-12 md:col-span-10">
                <button type="button" onClick={() => open(k.id)} className="text-left">
                  <h3 className="font-display text-2xl font-semibold leading-tight tracking-tight hover:text-accent">
                    {k.title}
                  </h3>
                </button>
                <p className="mt-2">{k.description}</p>
                <p className="mt-2 text-[15px] text-muted">
                  <span className="kicker mr-2">Why</span>
                  {k.justification}
                </p>
                {k.mitigation && (
                  <p className="mt-2 border-l-4 border-accent pl-3 text-[15px]">
                    <span className="kicker mr-2 text-accent">Mitigation</span>
                    {k.mitigation}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
                  <Chips label="Requirements" ids={k.requirement_ids} />
                  <Chips label="Source" ids={k.chunk_ids} />
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <div className="rule mb-4 pt-2">
          <SubHead>Code-computed findings the assessor was given</SubHead>
        </div>
        <dl className="grid gap-x-10 gap-y-6 md:grid-cols-2">
          <div>
            <dt className="kicker mb-1">Conflicting requirements</dt>
            <dd className="flex flex-wrap gap-2">
              {fnd.conflicts.length === 0 && <span className="text-muted">none</span>}
              {fnd.conflicts.map(([a, b]) => (
                <span key={a + b} className="inline-flex items-center gap-1">
                  <CiteChip id={a} />
                  <span className="text-muted">↔</span>
                  <CiteChip id={b} />
                </span>
              ))}
            </dd>
          </div>
          <div>
            <dt className="kicker mb-1">Uncovered mandatory requirements</dt>
            <dd>
              {fnd.uncovered_requirement_ids.length ? <Chips ids={fnd.uncovered_requirement_ids} /> : <span className="text-muted">none</span>}
            </dd>
          </div>
          <div>
            <dt className="kicker mb-1">Referenced documents not provided</dt>
            <dd>
              {fnd.absent_documents.length === 0 && <span className="text-muted">none</span>}
              <ul className="space-y-1 text-[15px]">
                {fnd.absent_documents.map((d, i) => (
                  <li key={i}>
                    {d.name} <span className="font-mono text-[11px] text-muted">({d.kind}, p. {d.page})</span>
                  </li>
                ))}
              </ul>
            </dd>
          </div>
          <div>
            <dt className="kicker mb-1">Budget requirements · parse flags</dt>
            <dd className="font-mono text-sm">
              {fnd.budget_requirement_count} · {fnd.flags.length}
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
