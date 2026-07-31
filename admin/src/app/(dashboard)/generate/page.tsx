"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { ApiError, createReadingRun, fetchRun } from "@/lib/api";
import { buildSamplePassageText } from "@/lib/sample-passage";
import type { GenerationRun, PassageSourceMode } from "@/lib/types";

const PASSAGE_WORD_MIN = 700;
const PASSAGE_WORD_MAX = 1000;

const SOURCE_MODE_HELP: Record<PassageSourceMode, string> = {
  generated: "AI writes the passage from scratch (needs a capable local model).",
  ingested:
    "Paste your licensed text as-is. Paragraphs are split on blank lines and labelled A, B, C…",
  adapted:
    "Paste licensed source text; the model lightly reformats it into IELTS passage shape.",
};

export default function GeneratePage() {
  const [topic, setTopic] = useState("Urban vertical farming");
  const [questionCount, setQuestionCount] = useState(1);
  const [targetBand, setTargetBand] = useState(7);
  const [sourceMode, setSourceMode] = useState<PassageSourceMode>("ingested");
  const [sourceText, setSourceText] = useState("");
  const [licenseLabel, setLicenseLabel] = useState("Original — internal use");
  const [adaptationLevel, setAdaptationLevel] = useState<"light" | "none" | "deep">("light");
  const [activeRun, setActiveRun] = useState<GenerationRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const needsSourceText = sourceMode !== "generated";
  const wordCount = useMemo(
    () => (sourceText.trim() ? sourceText.trim().split(/\s+/).length : 0),
    [sourceText],
  );

  useEffect(() => {
    if (!activeRun) return;
    if (["completed", "failed", "awaiting_review"].includes(activeRun.status)) return;

    const timer = window.setInterval(async () => {
      try {
        const latest = await fetchRun(activeRun.run_id);
        setActiveRun(latest);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to poll run");
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [activeRun]);

  const wordCountOk =
    !needsSourceText || (wordCount >= PASSAGE_WORD_MIN && wordCount <= PASSAGE_WORD_MAX);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (needsSourceText && !wordCountOk) {
      setError(
        `Passage must be ${PASSAGE_WORD_MIN}–${PASSAGE_WORD_MAX} words for IELTS rules (currently ${wordCount}).`,
      );
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const run = await createReadingRun({
        topic,
        questionCount,
        targetBand,
        sourceMode,
        sourceText: needsSourceText ? sourceText : undefined,
        licenseLabel: sourceMode === "adapted" ? licenseLabel : undefined,
        adaptationLevel: sourceMode === "adapted" ? adaptationLevel : undefined,
        idempotencyKey: crypto.randomUUID(),
      });
      setActiveRun(run);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start run");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Generate Reading content</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Choose how the passage is sourced, then generate questions and run quality gates.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="grid max-w-3xl gap-4 rounded-xl border border-zinc-200 bg-white p-6"
      >
        <label className="text-sm">
          <span className="mb-1 block text-zinc-700">Passage source</span>
          <select
            value={sourceMode}
            onChange={(event) => setSourceMode(event.target.value as PassageSourceMode)}
            className="w-full rounded-md border border-zinc-300 px-3 py-2"
          >
            <option value="ingested">Ingest my text (recommended)</option>
            <option value="adapted">Adapt my text (light reformat)</option>
            <option value="generated">Generate passage with AI</option>
          </select>
          <span className="mt-1 block text-xs text-zinc-500">{SOURCE_MODE_HELP[sourceMode]}</span>
        </label>

        <label className="text-sm">
          <span className="mb-1 block text-zinc-700">Topic / title</span>
          <input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            className="w-full rounded-md border border-zinc-300 px-3 py-2"
            required
          />
        </label>

        {needsSourceText ? (
          <>
            <label className="text-sm">
              <span className="mb-1 block text-zinc-700">Source text</span>
              <textarea
                value={sourceText}
                onChange={(event) => setSourceText(event.target.value)}
                rows={12}
                className="w-full rounded-md border border-zinc-300 px-3 py-2 font-mono text-xs leading-relaxed"
                placeholder={
                  "Paste licensed original text here.\n\nSeparate paragraphs with a blank line.\n\nAim for 700–1000 words total for IELTS passage rules."
                }
                required
              />
              <span
                className={`mt-1 block text-xs ${wordCountOk ? "text-zinc-500" : "text-amber-700"}`}
              >
                {wordCount} words — IELTS requires {PASSAGE_WORD_MIN}–{PASSAGE_WORD_MAX}. Use only
                text you own or are licensed to use.
              </span>
              <button
                type="button"
                onClick={() => setSourceText(buildSamplePassageText())}
                className="mt-2 text-xs font-medium text-zinc-700 underline"
              >
                Load sample passage (~760 words)
              </button>
            </label>
            {sourceMode === "adapted" ? (
              <>
                <label className="text-sm">
                  <span className="mb-1 block text-zinc-700">License label</span>
                  <input
                    value={licenseLabel}
                    onChange={(event) => setLicenseLabel(event.target.value)}
                    className="w-full rounded-md border border-zinc-300 px-3 py-2"
                    required
                  />
                </label>
                <label className="text-sm">
                  <span className="mb-1 block text-zinc-700">Adaptation level</span>
                  <select
                    value={adaptationLevel}
                    onChange={(event) =>
                      setAdaptationLevel(event.target.value as "light" | "none" | "deep")
                    }
                    className="w-full rounded-md border border-zinc-300 px-3 py-2"
                  >
                    <option value="light">Light</option>
                    <option value="none">None</option>
                    <option value="deep">Deep</option>
                  </select>
                </label>
              </>
            ) : null}
          </>
        ) : null}

        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm">
            <span className="mb-1 block text-zinc-700">Questions</span>
            <input
              type="number"
              min={1}
              max={14}
              value={questionCount}
              onChange={(event) => setQuestionCount(Number(event.target.value))}
              className="w-full rounded-md border border-zinc-300 px-3 py-2"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-zinc-700">Target band</span>
            <input
              type="number"
              min={5}
              max={9}
              step={0.5}
              value={targetBand}
              onChange={(event) => setTargetBand(Number(event.target.value))}
              className="w-full rounded-md border border-zinc-300 px-3 py-2"
            />
          </label>
        </div>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button
          type="submit"
          disabled={submitting || (needsSourceText && !wordCountOk)}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-60"
        >
          {submitting ? "Starting…" : "Start generation"}
        </button>
      </form>

      {activeRun ? (
        <section className="rounded-xl border border-zinc-200 bg-white p-6">
          <h2 className="text-lg font-medium text-zinc-900">Run status</h2>
          <dl className="mt-4 grid gap-2 text-sm">
            <div className="flex gap-2">
              <dt className="w-28 text-zinc-500">Run ID</dt>
              <dd className="font-mono text-xs">{activeRun.run_id}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-28 text-zinc-500">Status</dt>
              <dd className="font-medium capitalize">{activeRun.status.replaceAll("_", " ")}</dd>
            </div>
            {activeRun.failure_reason ? (
              <div className="flex gap-2">
                <dt className="w-28 text-zinc-500">Failure</dt>
                <dd className="text-red-600">{activeRun.failure_reason}</dd>
              </div>
            ) : null}
          </dl>
          {activeRun.status === "awaiting_review" ? (
            <p className="mt-4 text-sm text-amber-700">
              Run paused for human review — open Review to approve, then check Bank (refresh the
              page).
            </p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
