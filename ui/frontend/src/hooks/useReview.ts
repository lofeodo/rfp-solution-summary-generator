import { createContext, useContext, useEffect, useState } from "react";
import { api, VERSION_FILE } from "../api/client";
import type { ArtifactMap, Artefact, RevisionRecord, RunStatus } from "../api/types";
import { isResting } from "../api/types";
import { REVIEWER_KEY, load, save } from "../lib/storage";

// What the refine and sign-off controls share on a run page (ST12e): the run, its status,
// the revision log and the reviewer's name.
export interface ReviewCtx {
  runId: string;
  status: RunStatus;
  refresh: () => void;
  log: RevisionRecord[];
  reviewer: string;
  setReviewer: (name: string) => void;
}

export const ReviewContext = createContext<ReviewCtx | null>(null);

// Null outside a run page, or on a sample run, which cannot be reviewed.
export function useReview(): ReviewCtx | null {
  return useContext(ReviewContext);
}

// The reviewer's name, remembered across runs (the checkpoint form uses the same key).
export function useReviewer(): [string, (name: string) => void] {
  const [name, setName] = useState(() => load<string>(REVIEWER_KEY, ""));
  useEffect(() => save(REVIEWER_KEY, name.trim() || null), [name]);
  return [name, setName];
}

// The revision log, reread whenever a record is added and the run is at rest again.
export function useRevisionLog(runId: string, status: RunStatus | null): RevisionRecord[] {
  const [log, setLog] = useState<RevisionRecord[]>([]);
  const count = status?.review?.revisions ?? 0;
  const resting = isResting(status?.status);
  useEffect(() => setLog([]), [runId]);
  useEffect(() => {
    if (!resting || count === 0) return;
    let alive = true;
    api.revisions(runId).then(
      (l) => alive && setLog(l.revisions),
      () => undefined,
    );
    return () => {
      alive = false;
    };
  }, [runId, count, resting]);
  return log;
}

type VersionData<A extends Artefact> = ArtifactMap[(typeof VERSION_FILE)[A]];

// One stored version of an artefact, fetched while `n` is set (a read-only look back).
export function useVersion<A extends Artefact>(runId: string, artefact: A, n: number | null) {
  const key = `${runId}/${artefact}/${n}`;
  const [got, setGot] = useState<{ key: string; data: VersionData<A> | null; error: string | null } | null>(null);
  useEffect(() => {
    if (n === null) return;
    let alive = true;
    api.version(runId, artefact, n).then(
      (data) => alive && setGot({ key, data: data as VersionData<A>, error: null }),
      (err: Error) => alive && setGot({ key, data: null, error: err.message }),
    );
    return () => {
      alive = false;
    };
  }, [runId, artefact, n, key]);
  if (n === null) return { data: null, error: null, loading: false };
  if (!got || got.key !== key) return { data: null, error: null, loading: true };
  return { data: got.data, error: got.error, loading: false };
}
