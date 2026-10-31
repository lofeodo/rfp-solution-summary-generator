import { useMemo, useState } from "react";
import { Chips, CiteChip, useSource } from "../components/source";
import { SectionHead, SubHead, Tag, Waiting } from "../components/ui";
import type { RunData } from "../hooks/useRunData";
import {
  EMPTY_FILTER,
  STRICTNESS,
  TYPE_LABELS,
  TYPES,
  countBy,
  filterRequirements,
  toggle,
  type RequirementFilter,
} from "../lib/requirements";

function Toggle({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`whitespace-nowrap border px-2 py-0.5 font-mono text-[11px] transition-colors ${
        on ? "border-ink bg-ink text-paper" : "border-hair text-ink hover:border-ink"
      }`}
    >
      {children}
    </button>
  );
}

export default function RequirementsView({ data }: { data: RunData }) {
  const { open } = useSource();
  const [f, setF] = useState<RequirementFilter>(EMPTY_FILTER);
  const reqs = data.requirements?.requirements ?? [];
  const shown = useMemo(() => filterRequirements(reqs, f), [reqs, f]);
  const byType = useMemo(() => countBy(reqs, (r) => r.type), [reqs]);
  const byStrict = useMemo(() => countBy(reqs, (r) => r.strictness), [reqs]);
  if (!data.requirements) return <Waiting what="The requirements stage has not finished." loading={data.has("requirements")} />;
  const rep = data.report;

  return (
    <div className="space-y-16">
      <section>
        <SectionHead
          n="03"
          title="Requirements"
          aside={rep ? `${rep.pre_dedupe} extracted → ${reqs.length} after dedupe · ${rep.conflicts} conflicts` : undefined}
        />
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="kicker mr-2 w-20">Type</span>
            {TYPES.filter((t) => byType[t]).map((t) => (
              <Toggle key={t} on={f.types.includes(t)} onClick={() => setF({ ...f, types: toggle(f.types, t) })}>
                {TYPE_LABELS[t]} <span className="opacity-60">{byType[t]}</span>
              </Toggle>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="kicker mr-2 w-20">Strictness</span>
            {STRICTNESS.map((s) => (
              <Toggle key={s} on={f.strictness.includes(s)} onClick={() => setF({ ...f, strictness: toggle(f.strictness, s) })}>
                {s} <span className="opacity-60">{byStrict[s] ?? 0}</span>
              </Toggle>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="kicker mr-2 w-20">Search</span>
            <input
              type="search"
              value={f.query}
              onChange={(e) => setF({ ...f, query: e.target.value })}
              placeholder="text or R012"
              className="w-64 border-b-2 border-ink bg-transparent py-0.5 font-mono text-sm placeholder:text-muted focus:border-accent focus:outline-none"
            />
            <span className="font-mono text-xs text-muted">
              {shown.length} of {reqs.length}
            </span>
            {(f.types.length > 0 || f.strictness.length > 0 || f.query) && (
              <button type="button" className="kicker hover:text-accent" onClick={() => setF(EMPTY_FILTER)}>
                clear ×
              </button>
            )}
          </div>
        </div>

        <table className="mt-6 w-full border-collapse text-left">
          <thead className="hidden md:table-header-group">
            <tr className="border-b-2 border-ink">
              <th className="kicker w-16 py-1.5 font-normal">ID</th>
              <th className="kicker py-1.5 font-normal">Requirement</th>
              <th className="kicker w-40 py-1.5 font-normal">Type</th>
              <th className="kicker w-44 py-1.5 font-normal">Source</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr
                key={r.id}
                onClick={() => open(r.id)}
                className="block cursor-pointer border-b border-hair py-2 align-top transition-colors hover:bg-white/60 md:table-row md:py-0"
              >
                <td className="block py-1 pr-3 md:table-cell md:py-2.5">
                  <CiteChip id={r.id} />
                </td>
                <td className="block py-1 pr-4 md:table-cell md:py-2.5">
                  <span className={r.strictness === "mandatory" ? "" : "text-muted"}>{r.text}</span>
                  <span className="mt-1 flex flex-wrap gap-1.5">
                    {r.strictness !== "mandatory" && <Tag>{r.strictness}</Tag>}
                    {!r.quote_verified && <Tag tone="accent">quote unverified</Tag>}
                    {r.merged_from.length > 0 && <Tag>merged ×{r.merged_from.length}</Tag>}
                    {r.conflicts_with.length > 0 && <Chips label="conflicts" ids={r.conflicts_with} />}
                  </span>
                </td>
                <td className="block py-1 font-mono text-[11px] text-muted md:table-cell md:py-3">
                  {TYPE_LABELS[r.type]}
                  {r.strictness === "mandatory" && <span className="block text-ink">mandatory</span>}
                </td>
                <td className="block py-1 md:table-cell md:py-2.5">
                  <Chips ids={r.chunk_ids} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {shown.length === 0 && <p className="py-6 text-muted">No requirement matches these filters.</p>}
      </section>

      <section className="grid gap-x-10 gap-y-12 xl:grid-cols-2">
        <div>
          <div className="rule mb-4 flex items-baseline justify-between pt-2">
            <SubHead>Ambiguities</SubHead>
            <span className="font-mono text-[11px] text-muted">{data.requirements.ambiguities.length}</span>
          </div>
          <ul className="space-y-3">
            {data.requirements.ambiguities.map((a) => (
              <li key={a.id} className="grid grid-cols-[3rem_1fr] items-start gap-x-2">
                <CiteChip id={a.id} />
                <span className="text-[15px]">
                  {a.description} <Chips ids={[...a.requirement_ids, ...a.chunk_ids]} />
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="rule mb-4 flex items-baseline justify-between pt-2">
            <SubHead>Gaps</SubHead>
            <span className="font-mono text-[11px] text-muted">{data.requirements.gaps.length}</span>
          </div>
          <ul className="space-y-3">
            {data.requirements.gaps.map((g) => (
              <li key={g.id} className="grid grid-cols-[3rem_1fr] items-start gap-x-2">
                <CiteChip id={g.id} />
                <span className="text-[15px]">
                  {g.referenced_document && <span className="mr-1.5 font-mono text-xs">[{g.referenced_document}]</span>}
                  {g.description} <Chips ids={g.chunk_ids} />
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
