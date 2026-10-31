import { useEffect, useState } from "react";
import { api } from "../api/client";
import { highlightQuote, plainText } from "../lib/highlight";
import { cleanTitle, pages } from "../lib/format";
import { idKind, type IndexedChunk } from "../lib/ids";
import { TYPE_LABELS } from "../lib/requirements";
import { Chips, useSource } from "./source";
import { LevelBadge, Tag } from "./ui";

// Slide-over that reveals where an item comes from: the item, its cited chunks with the
// quote highlighted, and the PDF opened at the chunk's page. Chips inside push onto a
// history so Back returns to the previous item.
export default function SourcePanel({ stack, onBack, onClose }: { stack: string[]; onBack: () => void; onClose: () => void }) {
  const id = stack[stack.length - 1];
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!id) return null;
  return (
    <>
      <div className="fixed inset-0 z-30 bg-ink/20" onClick={onClose} aria-hidden />
      <aside
        role="dialog"
        aria-label={`Source of ${id}`}
        className="fixed inset-y-0 right-0 z-40 flex w-full flex-col border-l-2 border-ink bg-paper shadow-[-12px_0_0_0_rgba(22,19,15,0.08)] md:w-[min(56rem,62vw)]"
      >
        <div className="flex items-center gap-3 border-b-2 border-ink px-4 py-2 md:px-6">
          {stack.length > 1 && (
            <button type="button" onClick={onBack} className="kicker hover:text-ink">
              ← Back
            </button>
          )}
          <span className="kicker">Source of</span>
          <span className="font-mono text-sm text-accent">{id}</span>
          <button type="button" onClick={onClose} className="btn ml-auto px-2 py-0.5" aria-label="Close">
            Esc ×
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-5 md:px-6">
          <Body id={id} />
        </div>
      </aside>
    </>
  );
}

function Body({ id }: { id: string }) {
  const { index } = useSource();
  switch (idKind(id)) {
    case "requirement": {
      const r = index.requirements.get(id);
      if (!r) return <Missing id={id} />;
      return (
        <Item
          kicker={`${TYPE_LABELS[r.type]} · ${r.strictness}`}
          title={r.text}
          meta={
            <>
              {!r.quote_verified && <Tag tone="accent">quote not verified</Tag>}
              <Chips label="Merged from" ids={r.merged_from} />
              <Chips label="Conflicts with" ids={r.conflicts_with} />
              <Chips label="Addressed by" ids={index.addressedBy.get(r.id) ?? []} />
            </>
          }
          chunkIds={r.chunk_ids}
          quote={r.quote}
        />
      );
    }
    case "risk": {
      const k = index.risks.get(id);
      if (!k) return <Missing id={id} />;
      return (
        <Item
          kicker={`Risk · from the ${k.source}`}
          title={k.title}
          meta={
            <>
              <LevelBadge level={k.severity} label="sev" />
              <LevelBadge level={k.likelihood} label="lik" />
              <Chips label="Requirements" ids={k.requirement_ids} />
            </>
          }
          body={
            <>
              <p>{k.description}</p>
              <p className="mt-2 text-muted">
                <span className="kicker mr-2">Why</span>
                {k.justification}
              </p>
              {k.mitigation && (
                <p className="mt-2">
                  <span className="kicker mr-2 text-accent">Mitigation</span>
                  {k.mitigation}
                </p>
              )}
            </>
          }
          chunkIds={k.chunk_ids}
        />
      );
    }
    case "component": {
      const c = index.components.get(id);
      if (!c) return <Missing id={id} />;
      return (
        <Item
          kicker="Solution component"
          title={c.title}
          meta={<Chips label="Addresses" ids={c.requirement_ids} />}
          body={<p>{c.description}</p>}
          chunkIds={[...new Set(c.claims.flatMap((x) => x.chunk_ids))]}
        />
      );
    }
    case "ambiguity": {
      const a = index.ambiguities.get(id);
      if (!a) return <Missing id={id} />;
      return (
        <Item kicker="Ambiguity" title={a.description} meta={<Chips label="Requirements" ids={a.requirement_ids} />} chunkIds={a.chunk_ids} />
      );
    }
    case "gap": {
      const g = index.gaps.get(id);
      if (!g) return <Missing id={id} />;
      return (
        <Item
          kicker={g.referenced_document ? `Gap · ${g.referenced_document}` : "Gap"}
          title={g.description}
          chunkIds={g.chunk_ids}
        />
      );
    }
    case "chunk": {
      const c = index.chunks.get(id);
      if (!c) return <Missing id={id} />;
      return <Item kicker={`Chunk · ${pages(c.page_start, c.page_end)}`} title={cleanTitle(c.section_title)} chunkIds={[id]} />;
    }
    default:
      return <Missing id={id} />;
  }
}

function Missing({ id }: { id: string }) {
  return <p className="text-muted">{id} is not in this run's outputs (yet).</p>;
}

function Item(props: {
  kicker: string;
  title: string;
  meta?: React.ReactNode;
  body?: React.ReactNode;
  chunkIds: string[];
  quote?: string;
}) {
  return (
    <div>
      <p className="kicker">{props.kicker}</p>
      <h3
        className={`mt-1 font-display font-semibold leading-tight tracking-tight ${
          props.title.length > 90 ? "text-xl md:text-2xl" : "text-2xl md:text-3xl"
        }`}
      >
        {props.title}
      </h3>
      {props.meta && <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">{props.meta}</div>}
      {props.body && <div className="mt-4">{props.body}</div>}
      {props.quote && (
        <blockquote className="mt-5 border-l-4 border-accent pl-4 italic">“{plainText(props.quote).trim()}”</blockquote>
      )}
      <Sources chunkIds={props.chunkIds} quote={props.quote} />
    </div>
  );
}

function Sources({ chunkIds, quote }: { chunkIds: string[]; quote?: string }) {
  const { index, runId } = useSource();
  const [sel, setSel] = useState(0);
  useEffect(() => setSel(0), [chunkIds.join(",")]);
  if (chunkIds.length === 0) return <p className="mt-6 kicker">No source chunks cited.</p>;
  const chunk = index.chunks.get(chunkIds[Math.min(sel, chunkIds.length - 1)]);
  return (
    <section className="mt-6">
      <div className="rule flex flex-wrap items-baseline gap-2 pt-2">
        <span className="kicker mr-2">Source {chunkIds.length > 1 ? `(${chunkIds.length})` : ""}</span>
        {chunkIds.length > 1 &&
          chunkIds.map((c, i) => (
            <button
              type="button"
              key={c}
              onClick={() => setSel(i)}
              className={`border px-1.5 font-mono text-[11px] ${i === sel ? "border-ink bg-ink text-paper" : "border-hair text-muted hover:border-ink"}`}
            >
              {c}
            </button>
          ))}
      </div>
      {chunk ? <ChunkSource chunk={chunk} quote={quote} runId={runId} /> : <p className="mt-3 text-muted">Chunk not available.</p>}
    </section>
  );
}

function ChunkSource({ chunk, quote, runId }: { chunk: IndexedChunk; quote?: string; runId: string }) {
  const text = plainText(chunk.text);
  const h = quote ? highlightQuote(text, quote) : null;
  const pdf = api.pdfUrl(runId, chunk.page_start);
  return (
    <div>
      <p className="mt-3 font-mono text-[11px] text-muted">
        {chunk.section_path.map(cleanTitle).join(" › ")} · {pages(chunk.page_start, chunk.page_end)} · {chunk.id}
      </p>
      <div className="mt-3 max-h-[40vh] overflow-y-auto whitespace-pre-wrap border-l-2 border-hair pl-4 text-[15px] leading-relaxed">
        {h ? (
          <>
            {h.before}
            <mark
              className="bg-accentsoft text-ink decoration-accent underline decoration-2 underline-offset-2"
              ref={(el) => {
                // Scroll only the chunk box, not the panel, so the item title stays in view.
                const box = el?.parentElement;
                if (el && box) box.scrollTop = el.offsetTop - box.offsetTop - box.clientHeight / 4;
              }}
            >
              {h.match}
            </mark>
            {h.after}
          </>
        ) : (
          text
        )}
      </div>
      {quote && !h && <p className="mt-2 kicker text-accent">Quote not found verbatim in this chunk</p>}
      {h?.partial && <p className="mt-2 kicker">Opening of the quote highlighted</p>}
      <div className="mt-5 flex items-baseline justify-between">
        <span className="kicker">PDF · {pages(chunk.page_start, chunk.page_end)}</span>
        <a href={pdf} target="_blank" rel="noreferrer" className="kicker hover:text-accent">
          Open in new tab ↗
        </a>
      </div>
      <iframe key={pdf} src={pdf} title={`PDF page ${chunk.page_start}`} className="mt-2 h-[70vh] w-full border-2 border-ink bg-white" />
    </div>
  );
}
