import type {
  ArtifactMap,
  ArtifactName,
  CheckpointBody,
  Chunk,
  Health,
  Artefact,
  JobAccepted,
  RegenerateBody,
  ReviseBody,
  RevisionLog,
  RunCreated,
  RunListItem,
  RunStatus,
  SignOffBody,
} from "./types";

const API = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(API + path);
  if (!res.ok) throw new ApiError(res.status, await errorText(res));
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await errorText(res));
  return (await res.json()) as T;
}

// FastAPI errors are {"detail": "..."}; 422s are {"detail": [{msg}, ...]}.
async function errorText(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join("; ");
  } catch {
    // not JSON
  }
  return `${res.status} ${res.statusText}`;
}

const enc = encodeURIComponent;

export const api = {
  health: () => getJson<Health>("/health"),
  listRuns: () => getJson<RunListItem[]>("/runs"),
  getRun: (id: string) => getJson<RunStatus>(`/runs/${enc(id)}`),
  async deleteRun(id: string): Promise<void> {
    const res = await fetch(`${API}/runs/${enc(id)}`, { method: "DELETE" });
    if (!res.ok) throw new ApiError(res.status, await errorText(res));
  },
  artifact: <N extends ArtifactName>(id: string, name: N) =>
    getJson<ArtifactMap[N]>(`/runs/${enc(id)}/artifacts/${name}`),
  chunk: (id: string, chunkId: string) => getJson<Chunk>(`/runs/${enc(id)}/chunks/${enc(chunkId)}`),
  revisions: (id: string) => getJson<RevisionLog>(`/runs/${enc(id)}/revisions`),
  checkpoint: (id: string, body: CheckpointBody) => postJson<JobAccepted>(`/runs/${enc(id)}/checkpoint`, body),
  revise: (id: string, body: ReviseBody) => postJson<JobAccepted>(`/runs/${enc(id)}/revise`, body),
  regenerate: (id: string, body: RegenerateBody) => postJson<JobAccepted>(`/runs/${enc(id)}/regenerate`, body),
  signOff: (id: string, body: SignOffBody) => postJson<RunStatus>(`/runs/${enc(id)}/sign-off`, body),
  // One stored version of an artefact: the whole stage result, the same shape as its live artifact.
  version: <A extends Artefact>(id: string, artefact: A, n: number) =>
    getJson<ArtifactMap[VersionFile[A]]>(`/runs/${enc(id)}/versions/${artefact}/${n}`),

  async createRun(file: File, opts: RunOptions): Promise<RunCreated> {
    const form = new FormData();
    form.append("file", file);
    if (opts.model.trim()) form.append("model", opts.model.trim());
    // Unset fields keep the server's settings defaults, so only send the flags when on.
    if (opts.fullTextProblem) form.append("full_text_problem", "true");
    if (opts.singleCallExtraction) form.append("single_call_extraction", "true");
    if (opts.maxIterations !== null) form.append("max_iterations", String(opts.maxIterations));
    if (opts.unattended) form.append("unattended", "true");
    if (opts.vlm) {
      form.append("vlm", "true");
      form.append("vlm_scope", opts.vlmScope);
    }
    const res = await fetch(`${API}/runs`, { method: "POST", body: form });
    if (!res.ok) throw new ApiError(res.status, await errorText(res));
    return (await res.json()) as RunCreated;
  },

  eventsUrl: (id: string) => `${API}/runs/${enc(id)}/events`,
  pdfUrl: (id: string, page?: number) =>
    `${API}/runs/${enc(id)}/source.pdf${page ? `#page=${page}` : ""}`,
  downloadUrl: (id: string, file: "summary.json" | "summary.md") =>
    `${API}/runs/${enc(id)}/download/${file}`,
};

// The live artifact each revisable artefact is stored as.
export const VERSION_FILE = {
  requirements: "requirements_confirmed",
  problem: "problem",
  solution: "solution",
  risks: "risks",
} as const satisfies Record<Artefact, ArtifactName>;
type VersionFile = typeof VERSION_FILE;
export type VlmScope = "judged" | "flagged";

export interface RunOptions {
  model: string;
  fullTextProblem: boolean;
  singleCallExtraction: boolean;
  maxIterations: number | null;
  unattended: boolean; // run to the end without pausing at the checkpoint
  /** Re-render pages the parse-quality pass escalates with a vision model (ST2). */
  vlm: boolean;
  /** judged: the LLM judge gates the VLM; flagged: every heuristically flagged page goes. */
  vlmScope: VlmScope;
}
