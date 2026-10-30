import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Health, RunListItem } from "../api/types";
import Masthead from "../components/Masthead";
import RunList from "../components/RunList";
import UploadForm from "../components/UploadForm";

export default function Home() {
  const [runs, setRuns] = useState<RunListItem[] | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(setHealth, () => setError("The backend is not reachable. Start it with python -m ui.backend."));
  }, []);

  // Poll while something is queued or running so the list shows progress.
  useEffect(() => {
    let timer: number | undefined;
    let alive = true;
    const load = () =>
      api.listRuns().then(
        (r) => {
          if (!alive) return;
          setRuns(r);
          if (r.some((x) => x.status === "queued" || x.status === "running")) timer = window.setTimeout(load, 3000);
        },
        () => undefined,
      );
    load();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, []);

  const own = runs?.filter((r) => !r.sample) ?? [];
  const samples = runs?.filter((r) => r.sample) ?? [];

  return (
    <main className="mx-auto max-w-screen-2xl px-4 pb-24 pt-6 md:px-10">
      <Masthead />
      {error && <p className="mt-6 border-l-4 border-accent bg-accentsoft px-3 py-2 font-mono text-xs">{error}</p>}
      <div className="mt-10 grid grid-cols-12 lg:gap-x-10 gap-y-14">
        <section className="col-span-12 lg:col-span-4">
          <div className="rule mb-6 flex items-baseline gap-4 pt-3">
            <span className="font-mono text-sm text-accent">01</span>
            <h2 className="display text-4xl">New run</h2>
          </div>
          <UploadForm defaultModel={health?.model ?? null} />
          <p className="mt-4 text-sm text-muted">
            About 80–110 s and $0.05–0.10 per RFP on the default model. One run at a time; later uploads queue.
          </p>
        </section>
        <section className="col-span-12 lg:col-span-8">
          <div className="rule mb-6 flex items-baseline gap-4 pt-3">
            <span className="font-mono text-sm text-accent">02</span>
            <h2 className="display text-4xl">Runs</h2>
          </div>
          {runs === null ? (
            <p className="kicker">Loading…</p>
          ) : (
            <div className="space-y-12">
              {own.length > 0 && <RunList runs={own} />}
              <div>
                <p className="kicker mb-3">Committed samples · no API key needed</p>
                <RunList runs={samples} />
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
