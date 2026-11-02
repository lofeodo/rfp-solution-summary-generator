// Per-viewer conveniences in localStorage: the reviewer's name, and a checkpoint draft so
// a reload does not lose it. Storage can be missing or throw (private windows), so every
// access is guarded and the UI works without it.

export function load<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown): void {
  try {
    if (value === null || value === undefined) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage unavailable: the value just is not remembered
  }
}

export const REVIEWER_KEY = "rfp.reviewer";
export const checkpointKey = (runId: string) => `rfp.checkpoint.${runId}`;
