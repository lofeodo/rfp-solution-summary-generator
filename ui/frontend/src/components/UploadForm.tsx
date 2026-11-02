import { useState, type DragEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type RunOptions } from "../api/client";

export default function UploadForm({ defaultModel }: { defaultModel: string | null }) {
  const nav = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [over, setOver] = useState(false);
  const [opts, setOpts] = useState<RunOptions>({
    model: "",
    fullTextProblem: false,
    singleCallExtraction: false,
    maxIterations: null,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const run = await api.createRun(file, opts);
      nav(`/runs/${run.run_id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        className={`flex min-h-44 cursor-pointer flex-col justify-between border-2 border-dashed p-4 transition-colors ${
          over ? "border-accent bg-accentsoft" : "border-ink hover:bg-white/50"
        }`}
      >
        <span className="kicker">Drop an RFP (PDF, up to 50 MB)</span>
        <span className="font-display text-3xl font-semibold leading-tight tracking-tight">
          {file ? file.name : "Choose a PDF…"}
        </span>
        <span className="font-mono text-xs text-muted">
          {file ? `${(file.size / 1024).toFixed(0)} KB` : "or drag it here"}
        </span>
        <input
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>

      <fieldset className="space-y-3">
        <legend className="kicker mb-2">Options</legend>
        <label className="block">
          <span className="font-mono text-xs">Model</span>
          <input
            type="text"
            value={opts.model}
            placeholder={defaultModel ?? "provider:model"}
            onChange={(e) => setOpts({ ...opts, model: e.target.value })}
            className="mt-1 block w-full border-b-2 border-ink bg-transparent py-1 font-mono text-sm placeholder:text-muted focus:border-accent focus:outline-none"
          />
        </label>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={opts.fullTextProblem}
            onChange={(e) => setOpts({ ...opts, fullTextProblem: e.target.checked })}
            className="mt-1 accent-accent"
          />
          <span>
            <span className="font-mono text-xs">full_text_problem</span>
            <span className="block text-muted">Problem statement from the whole text, not chunk summaries</span>
          </span>
        </label>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={opts.singleCallExtraction}
            onChange={(e) => setOpts({ ...opts, singleCallExtraction: e.target.checked })}
            className="mt-1 accent-accent"
          />
          <span>
            <span className="font-mono text-xs">single_call_extraction</span>
            <span className="block text-muted">Requirements in one call instead of per chunk</span>
          </span>
        </label>
        <label className="flex items-baseline gap-3 text-sm">
          <span className="font-mono text-xs">max_iterations</span>
          <input
            type="number"
            min={1}
            max={10}
            value={opts.maxIterations ?? ""}
            placeholder="default"
            onChange={(e) => setOpts({ ...opts, maxIterations: e.target.value ? Number(e.target.value) : null })}
            className="w-24 border-b-2 border-ink bg-transparent py-0.5 font-mono text-sm placeholder:text-muted focus:border-accent focus:outline-none"
          />
          <span className="text-muted">coverage rounds</span>
        </label>
      </fieldset>

      {error && (
        <p role="alert" className="border-l-4 border-accent bg-accentsoft px-3 py-2 font-mono text-xs">
          {error}
        </p>
      )}

      <button type="submit" disabled={!file || busy} className="btn btn-accent w-full justify-center py-3 text-sm">
        {busy ? "Uploading…" : "Run the pipeline →"}
      </button>
    </form>
  );
}
