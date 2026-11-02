import { useMemo } from "react";
import type { Artefact, RunStatus } from "../api/types";
import { buildIndex } from "../lib/ids";
import { useArtifact } from "./useRun";

// Every intermediate output of a run, each null until its stage has written it. Revised
// artefacts are refetched when their version (current.json) moves.
export function useRunData(runId: string, status: RunStatus | null) {
  const v = (a: Artefact) => status?.review?.versions.artefacts[a]?.version ?? 1;
  const qualityDone = status?.artifacts.includes("quality") ? 1 : 0;
  const parsed = useArtifact(runId, "parsed", status, qualityDone);
  const quality = useArtifact(runId, "quality", status);
  const split = useArtifact(runId, "split", status);
  const extracted = useArtifact(runId, "requirements", status);
  const confirmed = useArtifact(runId, "requirements_confirmed", status, v("requirements"));
  const report = useArtifact(runId, "requirements_report", status);
  const problem = useArtifact(runId, "problem", status, v("problem"));
  const checkpoint = useArtifact(runId, "checkpoint", status);
  const solution = useArtifact(runId, "solution", status, v("solution"));
  const risks = useArtifact(runId, "risks", status, v("risks"));
  const has = (name: string) => status?.artifacts.includes(name) ?? false;
  // The live list: the confirmed one once it exists (checkpoint, or a revision at the
  // checkpoint), else the extractor's. Never the extracted list while the confirmed one loads.
  const requirements = has("requirements_confirmed") ? confirmed : extracted;
  const index = useMemo(
    () => buildIndex({ split, requirements, solution, risks }),
    [split, requirements, solution, risks],
  );
  // A view whose artifact is on disk but not fetched yet shows "Loading", not "Not yet".
  return { parsed, quality, split, requirements, extracted, report, problem, checkpoint, solution, risks, index, has };
}

export type RunData = ReturnType<typeof useRunData>;
