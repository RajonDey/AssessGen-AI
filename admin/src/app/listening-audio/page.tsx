"use client";

import { FormEvent, useEffect, useState } from "react";

import { ApiError, getTtsStatus, synthesizeListeningAudio } from "@/lib/api";

export default function ListeningAudioPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ duration?: string; turns?: string } | null>(
    null,
  );
  const [ttsAvailable, setTtsAvailable] = useState<boolean | null>(null);
  const [ttsHint, setTtsHint] = useState<string>("");

  useEffect(() => {
    getTtsStatus()
      .then((s) => {
        setTtsAvailable(s.available);
        setTtsHint(s.hint || "");
      })
      .catch(() => {
        setTtsAvailable(false);
        setTtsHint("Cannot reach API — is uvicorn running on :8080?");
      });
  }, []);

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Choose a Listening JSON or .md file first");
      return;
    }
    setLoading(true);
    setError(null);
    setStatus("Synthesizing with Kokoro (may take a minute on CPU)…");
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setMeta(null);

    try {
      const { blob, durationSeconds, turns } = await synthesizeListeningAudio(file);
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      setMeta({ duration: durationSeconds, turns });
      setStatus("Audio ready — play below or download.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Synthesis failed");
      setStatus("");
    } finally {
      setLoading(false);
    }
  }

  function onDownload() {
    if (!audioUrl || !file) return;
    const base = file.name.replace(/\.(json|md|txt)$/i, "") || "listening";
    const a = document.createElement("a");
    a.href = audioUrl;
    a.download = `${base}.wav`;
    a.click();
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Listening audio</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Upload Generate&apos;s <strong>JSON</strong> download (
          <code className="text-xs">speakers</code> +{" "}
          <code className="text-xs">script.turns</code>) and create a multi-speaker WAV with
          Kokoro. Markdown papers without JSON turns will be rejected. Unload Ollama first if RAM
          is tight (<code className="text-xs">ollama stop …</code>).
        </p>
      </div>

      {ttsAvailable === false && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Kokoro is not available on the API yet.
          {ttsHint ? (
            <>
              {" "}
              Hint: <code className="text-xs">{ttsHint}</code>
            </>
          ) : null}
        </div>
      )}
      {ttsAvailable === true && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          Kokoro TTS is available.
        </div>
      )}

      <form
        onSubmit={onSubmit}
        className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
      >
        <label className="block text-sm">
          <span className="font-medium text-zinc-700">Listening script file</span>
          <input
            type="file"
            accept=".json,.md,.txt,application/json,text/markdown,text/plain"
            className="mt-1.5 block w-full text-sm text-zinc-700 file:mr-3 file:rounded-lg file:border-0 file:bg-zinc-900 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <p className="mt-1.5 text-xs text-zinc-500">
            Use <strong>Download JSON</strong> from Generate. A Markdown file only works if it
            contains a JSON object with script.turns.
          </p>
        </label>

        <button
          type="submit"
          disabled={loading || !file}
          className="w-full rounded-xl bg-zinc-900 px-4 py-3 text-sm font-medium text-white disabled:opacity-50 sm:w-auto"
        >
          {loading ? "Creating audio…" : "Create audio"}
        </button>

        {status && <p className="text-sm text-zinc-600">{status}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>

      {audioUrl && (
        <section className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-zinc-600">
              {meta?.turns ? `${meta.turns} turns` : "Audio"}
              {meta?.duration ? ` · ${meta.duration}s` : ""}
            </div>
            <button
              type="button"
              onClick={onDownload}
              className="rounded-xl border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
            >
              Download WAV
            </button>
          </div>
          <audio controls src={audioUrl} className="w-full" />
        </section>
      )}
    </div>
  );
}
