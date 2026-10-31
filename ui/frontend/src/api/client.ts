import type {
  ArtifactMap,
  ArtifactName,
  Chunk,
  Health,
  RunCreated,
  RunListItem,
  RunStatus,
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
  artifact: <N extends ArtifactName>(id: string, name: N) =>
    getJson<ArtifactMap[N]>(`/runs/${enc(id)}/artifacts/${name}`),
  chunk: (id: string, chunkId: string) => getJson<Chunk>(`/runs/${enc(id)}/chunks/${enc(chunkId)}`),

  async createRun(file: File, opts: RunOptions): Promise<RunCreated> {
    const form = new FormData();
    form.append("file", file);
    if (opts.model.trim()) form.append("model", opts.model.trim());
    // Unset fields keep the server's settings defaults, so only send the flags when on.
    if (opts.fullTextProblem) form.append("full_text_problem", "true");
    if (opts.singleCallExtraction) form.append("single_call_extraction", "true");
    if (opts.maxIterations !== null) form.append("max_iterations", String(opts.maxIterations));
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

export interface RunOptions {
  model: string;
  fullTextProblem: boolean;
  singleCallExtraction: boolean;
  maxIterations: number | null;
}
