import { useMemo, useState, type ReactNode } from "react";
import type { Requirement } from "../api/types";
import { Chips, CiteChip } from "../components/source";
import { Tag } from "../components/ui";
import { effective, type CheckpointDraft, type RowDraft } from "../lib/checkpoint";
import { EMPTY_FILTER, STRICTNESS, TYPE_LABELS, TYPES, countBy, filterRequirements, toggle, type RequirementFilter } from "../lib/requirements";

function FilterToggle({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
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

const SELECT =
  "w-full border-b border-hair bg-transparent py-0.5 font-mono text-[11px] focus:border-accent focus:outline-none disabled:opacity-50";

// The checkpoint's requirement table: filter, then per row reject, strictness and type.
// Changes stay in the draft until the reviewer confirms.
export default function CheckpointRows({
  reqs,
  draft,
  onChange,
  onReset,
  disabled,
}: {
  reqs: Requirement[];
  draft: CheckpointDraft;
  onChange: (req: Requirement, patch: RowDraft) => void;
  onReset: () => void;
  disabled: boolean;
}) {
  const [f, setF] = useState<RequirementFilter>(EMPTY_FILTER);
  const [changedOnly, setChangedOnly] = useState(false);
  const shown = useMemo(
    () => filterRequirements(reqs, f).filter((r) => !changedOnly || draft[r.id]),
    [reqs, f, changedOnly, draft],
  );
  const byType = useMemo(() => countBy(reqs, (r) => r.type), [reqs]);
  const byStrict = useMemo(() => countBy(reqs, (r) => r.strictness), [reqs]);
  const changed = Object.keys(draft).length;
  const filtered = f.types.length > 0 || f.strictness.length > 0 || f.query || changedOnly;

  return (
    <div>
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="kicker mr-2 w-20">Type</span>
          {TYPES.filter((t) => byType[t]).map((t) => (
            <FilterToggle key={t} on={f.types.includes(t)} onClick={() => setF({ ...f, types: toggle(f.types, t) })}>
              {TYPE_LABELS[t]} <span className="opacity-60">{byType[t]}</span>
            </FilterToggle>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="kicker mr-2 w-20">Strictness</span>
          {STRICTNESS.map((s) => (
            <FilterToggle key={s} on={f.strictness.includes(s)} onClick={() => setF({ ...f, strictness: toggle(f.strictness, s) })}>
              {s} <span className="opacity-60">{byStrict[s] ?? 0}</span>
            </FilterToggle>
          ))}
          <FilterToggle on={changedOnly} onClick={() => setChangedOnly(!changedOnly)}>
            changed <span className="opacity-60">{changed}</span>
          </FilterToggle>
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
          {filtered && (
            <button
              type="button"
              className="kicker hover:text-accent"
              onClick={() => {
                setF(EMPTY_FILTER);
                setChangedOnly(false);
              }}
            >
              clear ×
            </button>
          )}
          {changed > 0 && (
            <button type="button" className="kicker ml-auto hover:text-accent" onClick={onReset} disabled={disabled}>
              undo all {changed} changes
            </button>
          )}
        </div>
      </div>

      <table className="mt-6 w-full border-collapse text-left">
        <thead className="hidden md:table-header-group">
          <tr className="border-b-2 border-ink">
            <th className="kicker w-16 py-1.5 font-normal">ID</th>
            <th className="kicker py-1.5 font-normal">Requirement</th>
            <th className="kicker w-44 py-1.5 font-normal">Type</th>
            <th className="kicker w-28 py-1.5 font-normal">Strictness</th>
            <th className="kicker w-24 py-1.5 text-right font-normal">Keep</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((r) => {
            const row = draft[r.id];
            const eff = effective(r, row);
            const rejected = !!row?.reject;
            return (
              <tr
                key={r.id}
                data-req={r.id}
                className={`block border-b border-hair py-2 align-top md:table-row md:py-0 ${
                  row ? "border-l-4 border-l-accent bg-accentsoft/40" : ""
                }`}
              >
                <td className="block py-1 pl-1 pr-3 md:table-cell md:py-2.5">
                  <CiteChip id={r.id} />
                </td>
                <td className="block py-1 pr-4 md:table-cell md:py-2.5">
                  <span className={rejected ? "text-muted line-through" : eff.strictness === "mandatory" ? "" : "text-muted"}>
                    {r.text}
                  </span>
                  <span className="mt-1 flex flex-wrap items-center gap-1.5">
                    {rejected && <Tag tone="accent">rejected</Tag>}
                    {!rejected && row && <Tag tone="accent">edited</Tag>}
                    {r.origin === "reviewed" && <Tag tone="ink">reviewed</Tag>}
                    {!r.quote_verified && <Tag tone="accent">quote unverified</Tag>}
                    {r.merged_from.length > 0 && <Tag>merged ×{r.merged_from.length}</Tag>}
                    {r.conflicts_with.length > 0 && <Chips label="conflicts" ids={r.conflicts_with} />}
                    <Chips ids={r.chunk_ids} />
                  </span>
                </td>
                <td className="inline-block w-1/2 py-1 pr-3 md:table-cell md:w-auto md:py-2.5">
                  <select
                    aria-label={`Type of ${r.id}`}
                    className={SELECT}
                    value={eff.type}
                    disabled={disabled || rejected}
                    onChange={(e) => onChange(r, { type: e.target.value as Requirement["type"] })}
                  >
                    {TYPES.map((t) => (
                      <option key={t} value={t}>
                        {TYPE_LABELS[t]}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="inline-block w-1/4 py-1 pr-3 md:table-cell md:w-auto md:py-2.5">
                  <select
                    aria-label={`Strictness of ${r.id}`}
                    className={SELECT}
                    value={eff.strictness}
                    disabled={disabled || rejected}
                    onChange={(e) => onChange(r, { strictness: e.target.value as Requirement["strictness"] })}
                  >
                    {STRICTNESS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="inline-block w-1/4 py-1 text-right md:table-cell md:w-auto md:py-2.5">
                  <button
                    type="button"
                    aria-pressed={rejected}
                    aria-label={rejected ? `Keep ${r.id}` : `Reject ${r.id}`}
                    disabled={disabled}
                    onClick={() => onChange(r, rejected ? { reject: false } : { reject: true, strictness: undefined, type: undefined })}
                    className={`whitespace-nowrap border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider transition-colors disabled:opacity-40 ${
                      rejected ? "border-accent bg-accent text-paper" : "border-hair hover:border-accent hover:text-accent"
                    }`}
                  >
                    {rejected ? "rejected" : "reject"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {shown.length === 0 && <p className="py-6 text-muted">No requirement matches these filters.</p>}
    </div>
  );
}
