import { useEffect, useState, type ReactNode } from "react";
import type { Artefact } from "../api/types";
import type { RunData } from "../hooks/useRunData";
import { useReview, useVersion } from "../hooks/useReview";
import ArtefactBar from "./ArtefactBar";
import ReviseBox from "./ReviseBox";

// Wraps an artefact tab once the run has a draft (ST12e): the version bar above, the
// "Suggest edits" panel below, and an older version swapped in read-only when picked.
// The views themselves stay unaware of review.
export default function Refinable({
  artefact,
  data,
  children,
}: {
  artefact: Artefact;
  data: RunData;
  children: (shown: RunData) => ReactNode;
}) {
  const review = useReview();
  const [viewing, setViewing] = useState<number | null>(null);
  const current = review?.status.review.versions.artefacts[artefact]?.version ?? 1;
  // A new version (a revision, a regeneration) brings the reader back to the current one.
  useEffect(() => setViewing(null), [current]);
  const old = useVersion(review?.runId ?? "", artefact, review ? viewing : null);

  if (!review || !data.has("solution")) return <>{children(data)}</>;
  const shown: RunData = viewing !== null && old.data ? { ...data, [artefact]: old.data } : data;
  return (
    <>
      <ArtefactBar artefact={artefact} viewing={viewing} onView={setViewing} loading={old.loading} error={old.error} />
      <div className={viewing !== null ? "opacity-90" : ""}>{children(shown)}</div>
      {viewing === null && <ReviseBox artefact={artefact} />}
    </>
  );
}
