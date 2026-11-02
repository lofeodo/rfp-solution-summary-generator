import { CiteChip } from "../components/source";
import { SectionHead, SubHead, Tag, Waiting } from "../components/ui";
import type { RunData } from "../hooks/useRunData";
import { cleanTitle, pages } from "../lib/format";

export default function ParseView({ data }: { data: RunData }) {
  const { parsed, quality, split } = data;
  if (!parsed) return <Waiting what="The parse stage has not finished." loading={data.has("parsed")} />;
  const flagsByPage = new Map<number, string[]>();
  for (const f of parsed.flags) flagsByPage.set(f.page, [...(flagsByPage.get(f.page) ?? []), f.reason]);
  const maxWords = Math.max(1, ...parsed.pages.map((p) => p.word_count));

  return (
    <div className="space-y-16">
      <section>
        <SectionHead
          n="07"
          title="Parse"
          aside={`${parsed.pages.length} pages · ${parsed.tables.length} tables · ${parsed.images.length} images · ${parsed.outline.length ? "outline" : "no outline"}`}
        />
        <div className="grid gap-x-10 gap-y-10 xl:grid-cols-2">
          <div>
            <p className="kicker mb-2">Words per page · flagged pages in accent</p>
            <ul className="space-y-1">
              {parsed.pages.map((p) => {
                const flags = flagsByPage.get(p.number);
                const j = quality?.judgements[String(p.number)];
                return (
                  <li key={p.number} className="grid grid-cols-[2.5rem_1fr] items-center gap-x-2 font-mono text-[11px]">
                    <span className="text-right text-muted">p{p.number}</span>
                    <span className="flex min-w-0 items-center gap-2" title={`${p.word_count} words`}>
                      <span
                        className={`h-2.5 shrink-0 rounded-r ${flags ? "bg-accent" : "bg-ink"}`}
                        style={{ width: `${Math.max(1, (p.word_count / maxWords) * 55)}%` }}
                      />
                      <span className="shrink-0">{p.word_count}</span>
                      {flags && <span className="truncate text-accent">{flags.join(", ")}</span>}
                      {j && <span className="truncate text-muted">→ {j.page_kind}{j.content_missing ? ", content missing" : ""}</span>}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
          <div className="space-y-8">
            {quality && quality.judged_pages.length > 0 && (
              <div>
                <div className="hair mb-3 pt-2">
                  <SubHead>Quality pass</SubHead>
                </div>
                <ul className="space-y-2 text-[15px]">
                  {quality.judged_pages.map((n) => {
                    const j = quality.judgements[String(n)];
                    return (
                      <li key={n}>
                        <span className="mr-2 font-mono text-xs">p{n}</span>
                        {j && (
                          <>
                            <Tag tone={j.text_usable ? "muted" : "accent"}>{j.text_usable ? "usable" : "not usable"}</Tag> {j.reason}
                          </>
                        )}
                      </li>
                    );
                  })}
                </ul>
                {quality.escalations.length > 0 && (
                  <p className="mt-3 font-mono text-[11px] text-muted">
                    Escalations: {quality.escalations.map((e) => `p${e.page} ${e.action.split(":")[0]}`).join(" · ")}
                  </p>
                )}
              </div>
            )}
            <div>
              <div className="hair mb-3 pt-2">
                <SubHead>Referenced documents</SubHead>
              </div>
              {parsed.referenced_documents.length === 0 && <p className="text-muted">None found.</p>}
              <ul className="space-y-1.5 text-[15px]">
                {parsed.referenced_documents.map((d, i) => (
                  <li key={i} className="flex flex-wrap items-baseline gap-x-2">
                    <Tag tone={d.present ? "muted" : "accent"}>{d.present ? "present" : "absent"}</Tag>
                    {d.url ? (
                      <a className="underline decoration-hair underline-offset-2 hover:decoration-accent [overflow-wrap:anywhere]" href={d.url} target="_blank" rel="noreferrer">
                        {d.name}
                      </a>
                    ) : (
                      <span>{d.name}</span>
                    )}
                    <span className="font-mono text-[11px] text-muted">
                      {d.kind}, p. {d.page}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section>
        <SectionHead n="08" title="Sections & chunks" aside={split ? `${split.sections.length} sections` : undefined} />
        {!split ? (
          <Waiting what="The split stage has not finished." loading={data.has("split")} />
        ) : (
          <ol>
            {split.sections.map((s) => (
              <li key={s.id} className="hair grid grid-cols-12 gap-x-4 py-2">
                <span className="col-span-2 font-mono text-[11px] text-muted md:col-span-1">{s.id}</span>
                <span className="col-span-10 md:col-span-7" style={{ paddingLeft: `${Math.min(s.level - 1, 3) * 1}rem` }}>
                  {cleanTitle(s.title)}
                  {s.kind === "requirement_bearing" && <span className="ml-2 align-middle"><Tag>requirements</Tag></span>}
                </span>
                <span className="col-span-12 flex flex-wrap items-baseline gap-1 md:col-span-4 md:justify-end">
                  <span className="mr-1 font-mono text-[11px] text-muted">{pages(s.page_start, s.page_end)}</span>
                  {s.chunks.map((c) => (
                    <CiteChip key={c.id} id={c.id} />
                  ))}
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
