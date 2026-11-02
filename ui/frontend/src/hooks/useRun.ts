import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { isResting, type ArtifactMap, type ArtifactName, type RunStatus, type StageEvent } from "../api/types";
import { fromList, reduceStage, type StageMap } from "../lib/stages";

export interface RunHandle {
  status: RunStatus | null;
  stages: StageMap;
  error: string | null;
  // Re-read the status, e.g. after posting a job: the run reads busy at once, which
  // reopens the stream.
  refresh: () => void;
}

// Status from GET /runs/{id}; while a job is in flight (queued, running, drafting,
// refining), stage and state events from the SSE stream. The stream replays from the start
// on every (re)connect and the reducer keeps the latest event per stage, so EventSource's
// automatic reconnect is harmless. Once the run rests, the stages come from the status,
// which reads them from the run log and is exact.
export function useRun(id: string): RunHandle {
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [stages, setStages] = useState<StageMap>({});
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.getRun(id).then(
      (s) => {
        setStatus(s);
        if (isResting(s.status)) setStages(fromList(s.stages));
      },
      (e: Error) => setError(e.message),
    );
  }, [id]);

  useEffect(() => {
    let alive = true;
    setStatus(null);
    setStages({});
    setError(null);
    api.getRun(id).then(
      (s) => {
        if (!alive) return;
        setStatus(s);
        setStages(fromList(s.stages));
      },
      (e: Error) => alive && setError(e.message),
    );
    return () => {
      alive = false;
    };
  }, [id]);

  const live = status !== null && !isResting(status.status);
  useEffect(() => {
    if (!live) return;
    const es = new EventSource(api.eventsUrl(id));
    es.addEventListener("stage", (m) => {
      const ev = JSON.parse((m as MessageEvent).data) as StageEvent;
      setStages((prev) => reduceStage(prev, ev));
      refresh();
    });
    es.addEventListener("state", () => refresh());
    es.addEventListener("done", () => {
      es.close();
      refresh();
    });
    return () => es.close();
  }, [id, live, refresh]);

  return { status, stages, error, refresh };
}

// Fetch an artifact once it is on disk. `version` lets a caller refetch a file that is
// rewritten in place (parse_quality rewrites parsed.json; a revision rewrites its artefact).
export function useArtifact<N extends ArtifactName>(
  runId: string,
  name: N,
  status: RunStatus | null,
  version: number | string = 0,
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
