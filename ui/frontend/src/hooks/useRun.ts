import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ArtifactMap, ArtifactName, RunStatus, StageEvent } from "../api/types";
import { fromList, reduceStage, type StageMap } from "../lib/stages";

export interface RunHandle {
  status: RunStatus | null;
  stages: StageMap;
  error: string | null;
}

// Status from GET /runs/{id}; while queued or running, stage events from the SSE stream.
// The stream replays from the start on every (re)connect and the reducer keeps the latest
// event per stage, so EventSource's automatic reconnect is harmless.
export function useRun(id: string): RunHandle {
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [stages, setStages] = useState<StageMap>({});
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.getRun(id).then(setStatus, (e: Error) => setError(e.message));
  }, [id]);

  useEffect(() => {
    let alive = true;
    let es: EventSource | null = null;
    setStatus(null);
    setStages({});
    setError(null);
    api.getRun(id).then(
      (s) => {
        if (!alive) return;
        setStatus(s);
        setStages(fromList(s.stages));
        if (s.status !== "queued" && s.status !== "running") return;
        es = new EventSource(api.eventsUrl(id));
        es.addEventListener("stage", (m) => {
          const ev = JSON.parse((m as MessageEvent).data) as StageEvent;
          setStages((prev) => reduceStage(prev, ev));
          refresh();
        });
        es.addEventListener("done", () => {
          es?.close();
          refresh();
        });
      },
      (e: Error) => alive && setError(e.message),
    );
    return () => {
      alive = false;
      es?.close();
    };
  }, [id, refresh]);

  return { status, stages, error };
}

// Fetch an artifact once it is on disk. `version` lets a caller refetch a file a later
// stage rewrites (parse_quality rewrites parsed.json).
export function useArtifact<N extends ArtifactName>(
  runId: string,
  name: N,
  status: RunStatus | null,
  version = 0,
): ArtifactMap[N] | null {
  const [data, setData] = useState<ArtifactMap[N] | null>(null);
  const available = status?.artifacts.includes(name) ?? false;
  useEffect(() => {
    setData(null);
  }, [runId]);
  useEffect(() => {
    if (!available) return;
    let alive = true;
    api.artifact(runId, name).then(
      (d) => alive && setData(d),
      () => undefined,
    );
    return () => {
      alive = false;
    };
  }, [runId, name, available, version]);
  return data;
}
