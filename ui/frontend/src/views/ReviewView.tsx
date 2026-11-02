import { Link } from "react-router-dom";
import type { Artefact } from "../api/types";
import { RevisionLine } from "../components/DiffView";
import { RegenerateButton } from "../components/ReviewControls";
import SignOffForm from "../components/SignOffForm";
import { SectionHead, Tag, Waiting } from "../components/ui";
import { useReview } from "../hooks/useReview";
import { secs, usd, when } from "../lib/format";
import { ARTEFACT_LABEL, stageOf, totalCost } from "../lib/revisions";

const ARTEFACTS: Artefact[] = ["requirements", "problem", "solution", "risks"];
const TAB: Record<Artefact, string> = { requirements: "requirements", problem: "problem", solution: "solution", risks: "risks" };

// The Review tab (ST12e): sign-off, where each artefact stands, and the whole history of
// the human loop with every diff.
export default function ReviewView({ drafted }: { drafted: boolean }) {
  const review = useReview();
  if (!review) return <Waiting what="Sample runs have no review." />;
  const { runId, status, log } = review;
  const rs = status.review;
  if (!drafted)
    return (
      <Waiting
        what={
          status.status === "awaiting_checkpoint"
            ? "Nothing is drafted yet: confirm the checkpoint first."
            : "The review opens once the solution and risks are drafted."
        }
      />
    );
  const cp = rs.checkpoint;

  return (
    <div className="space-y-16">
      <section>
        <SectionHead n="00" title="Sign-off" aside={rs.sign_off ? "frozen" : status.status === "refining" ? "a change is running" : "open"} />
        <SignOffForm />
      </section>

      <section>
        <SectionHead n="01" title="Versions" aside={rs.stale.length ? `${rs.stale.length} stale` : "all current"} />
        <ul className="rule">
          {ARTEFACTS.map((a) => {
            const v = rs.versions.artefacts[a];
            return (
              <li key={a} className="hair grid grid-cols-12 items-start gap-x-4 gap-y-2 py-3">
                <Link to={`/runs/${runId}/${TAB[a]}`} className="col-span-6 font-display text-xl font-semibold tracking-tight hover:text-accent md:col-span-3">
                  {ARTEFACT_LABEL[a]}
                </Link>
                <span className="col-span-6 font-mono text-sm md:col-span-2">
                  v{v?.version ?? 1}
                  {v?.updated_at && <span className="block text-[11px] text-muted">{when(v.updated_at)}</span>}
                </span>
                <span className="col-span-12 text-[15px] md:col-span-4">
                  {v?.stale ? (
                    <>
                      <Tag tone="accent">stale</Tag> <span className="text-muted">{v.stale_because}</span>
                    </>
                  ) : (
                    <Tag>current</Tag>
                  )}
                </span>
                <span className="col-span-12 md:col-span-3 md:text-right">
                  {stageOf(a) && !rs.sign_off && <RegenerateButton artefact={a} accent={!!v?.stale} />}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section>
        <SectionHead n="02" title="History" aside={`${log.length} record${log.length === 1 ? "" : "s"} · ${usd(totalCost(log))}`} />
        <ol className="rule">
          {[...log].reverse().map((r) => (
            <RevisionLine key={r.id} r={r} open={log.length <= 8} />
          ))}
          <li className="hair space-y-1 py-2.5">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="font-mono text-xs">CP</span>
              <Tag tone="ink">{cp ? "checkpoint" : "drafted"}</Tag>
              <span className="font-mono text-[11px] text-muted">
                {cp
                  ? `${cp.reviewer} · ${when(cp.confirmed_at)} · waited ${secs(cp.waited_s)} · ${cp.decisions.length} decisions · ${cp.brief?.chunks.length ?? 0} brief paragraphs`
                  : "unattended: no checkpoint, no brief"}
              </span>
            </div>
            {cp?.note && <p className="text-[15px]">{cp.note}</p>}
            {cp && (
              <Link to={`/runs/${runId}/checkpoint`} className="kicker hover:text-accent">
                the checkpoint record →
              </Link>
            )}
          </li>
        </ol>
      </section>
    </div>
  );
}
