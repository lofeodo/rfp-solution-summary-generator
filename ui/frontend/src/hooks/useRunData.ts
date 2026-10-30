import { useMemo } from "react";
import type { RunStatus } from "../api/types";
import { buildIndex } from "../lib/ids";
import { useArtifact } from "./useRun";

// Every intermediate output of a run, each null until its stage has written it.
export function useRunData(runId: string, status: RunStatus | null) {
  const qualityDone = status?.artifacts.includes("quality") ? 1 : 0;
  const parsed = useArtifact(runId, "parsed", status, qualityDone);
  const quality = useArtifact(runId, "quality", status);
  const split = useArtifact(runId, "split", status);
  const requirements = useArtifact(runId, "requirements", status);
  const report = useArtifact(runId, "requirements_report", status);
  const problem = useArtifact(runId, "problem", status);
  const solution = useArtifact(runId, "solution", status);
  const risks = useArtifact(runId, "risks", status);
  const index = useMemo(
    () => buildIndex({ split, requirements, solution, risks }),
    [split, requirements, solution, risks],
  );
  // A view whose artifact is on disk but not fetched yet shows "Loading", not "Not yet".
  const has = (name: string) => status?.artifacts.includes(name) ?? false;
  return { parsed, quality, split, requirements, report, problem, solution, risks, index, has };
}

export type RunData = ReturnType<typeof useRunData>;
