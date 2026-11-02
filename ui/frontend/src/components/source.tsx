import { createContext, useContext } from "react";
import type { IdKind, RunIndex } from "../lib/ids";
import { idKind } from "../lib/ids";
import { cleanTitle, pages } from "../lib/format";

// Source reveal: any chip calls open(id); the panel shows that item and its source chunks.
export interface SourceCtx {
  runId: string;
  index: RunIndex;
  open: (id: string) => void;
}

export const SourceContext = createContext<SourceCtx | null>(null);

export function useSource(): SourceCtx {
  const ctx = useContext(SourceContext);
  if (!ctx) throw new Error("useSource outside SourceContext");
  return ctx;
}

const KIND_CLS: Record<IdKind, string> = {
  chunk: "border-hair text-muted hover:border-ink hover:text-ink",
  requirement: "border-accent text-accent hover:bg-accent hover:text-paper",
  component: "border-ink text-ink hover:bg-ink hover:text-paper",
  risk: "border-ink text-ink hover:bg-ink hover:text-paper",
  ambiguity: "border-hair text-muted hover:border-ink hover:text-ink",
  gap: "border-hair text-muted hover:border-ink hover:text-ink",
};

export function CiteChip({ id }: { id: string }) {
  const { index, open } = useSource();
  const kind = idKind(id);
  if (!kind) return <span className="font-mono text-[11px] text-muted">{id}</span>;
  const chunk = kind === "chunk" ? index.chunks.get(id) : undefined;
  const title = chunk
    ? `${cleanTitle(chunk.section_title)}, ${pages(chunk.page_start, chunk.page_end)}`
    : kind === "requirement"
      ? index.requirements.get(id)?.text
      : kind === "risk"
        ? index.risks.get(id)?.title
        : kind === "component"
          ? index.components.get(id)?.title
          : undefined;
  return (
    <button
      type="button"
      title={title}
      onClick={(e) => {
        e.stopPropagation();
        open(id);
      }}
      className={`inline-flex items-baseline gap-1 border px-1 py-px align-baseline font-mono text-[11px] leading-tight transition-colors ${KIND_CLS[kind]}`}
    >
      {id}
      {chunk && <span className="opacity-60">p{chunk.page_start}</span>}
    </button>
  );
}

export function Chips({ ids, label }: { ids: string[]; label?: string }) {
  if (ids.length === 0) return null;
  return (
    <span className="inline-flex flex-wrap items-baseline gap-1">
      {label && <span className="kicker mr-1">{label}</span>}
      {ids.map((id) => (
        <CiteChip key={id} id={id} />
      ))}
    </span>
  );
}
