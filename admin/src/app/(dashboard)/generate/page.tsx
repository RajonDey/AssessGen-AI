"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  cancelRun,
  createListeningRun,
  createReadingRun,
  createSpeakingRun,
  createWritingRun,
  fetchRun,
} from "@/lib/api";
import { buildSamplePassageText } from "@/lib/sample-passage";
import type {
  GenerationModule,
  GenerationRun,
  PassageSourceMode,
  WritingQuestionType,
} from "@/lib/types";

const PASSAGE_WORD_MIN = 700;
const PASSAGE_WORD_MAX = 1000;

const MODULES: { id: GenerationModule; label: string; description: string }[] = [
  {
    id: "reading",
    label: "Reading",
    description: "Passage + questions with full quality gates.",
  },
  {
    id: "listening",
    label: "Listening",
    description: "Section 1–2 script + completion items (text review, no audio).",
  },
  {
    id: "writing",
    label: "Writing",
    description: "Task 2 essay prompt for one of five question types.",
  },
  {
    id: "speaking",
    label: "Speaking",
    description: "Part 1 topics + Part 2 cue card (text review).",
  },
];

const WRITING_TYPES: { value: WritingQuestionType; label: string }[] = [
  { value: "opinion", label: "Opinion / agree-disagree" },
  { value: "discussion", label: "Discussion (both views)" },
  { value: "problem_solution", label: "Problem & solution" },
  { value: "advantages_disadvantages", label: "Advantages & disadvantages" },
  { value: "two_part", label: "Two-part question" },
];

const DEV_MODE_STORAGE_KEY = "assessgen-dev-mode";

const SOURCE_MODE_HELP: Record<PassageSourceMode, string> = {
  generated: "AI writes the passage from scratch (needs a capable local model).",
  ingested:
    "Paste your licensed text as-is. Paragraphs are split on blank lines and labelled A, B, C…",
  adapted:
    "Paste licensed source text; the model lightly reformats it into IELTS passage shape.",
};

function RunStatusPanel({
  activeRun,
  onCancel,
  cancelling,
}: {
  activeRun: GenerationRun;
  onCancel: () => void;
  cancelling: boolean;
}) {
  const canCancel = activeRun.status === "queued" || activeRun.status === "running";

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-6">
      <h2 className="text-lg font-medium text-zinc-900">Run status</h2>
      <dl className="mt-4 grid gap-2 text-sm">
        <div className="flex gap-2">
          <dt className="w-28 text-zinc-500">Run ID</dt>
          <dd className="font-mono text-xs">{activeRun.run_id}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="w-28 text-zinc-500">Module</dt>
          <dd className="capitalize">{activeRun.module}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="w-28 text-zinc-500">Status</dt>
          <dd className="font-medium capitalize">{activeRun.status.replaceAll("_", " ")}</dd>
        </div>
        {activeRun.status === "queued" && activeRun.queue_ahead != null ? (
          <div className="flex gap-2">
            <dt className="w-28 text-zinc-500">Queue</dt>
            <dd className="text-amber-800">
              {activeRun.queue_ahead === 0
                ? "Next in line — worker will start shortly"
                : `${activeRun.queue_ahead} run(s) ahead (single worker)`}
            </dd>
          </div>
        ) : null}
        {activeRun.failure_reason ? (
          <div className="flex gap-2">
            <dt className="w-28 text-zinc-500">Failure</dt>
            <dd className="text-red-600">{activeRun.failure_reason}</dd>
          </div>
        ) : null}
      </dl>
      {canCancel ? (
        <button
          type="button"
          disabled={cancelling}
          onClick={onCancel}
          className="mt-4 rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-60"
        >
          {cancelling ? "Cancelling…" : "Cancel run"}
        </button>
      ) : null}
      {activeRun.status === "awaiting_review" ? (
        <p className="mt-4 text-sm text-amber-700">
          Run paused for human review — open Review to approve, then check Bank (refresh the page).
        </p>
      ) : null}
    </section>
  );
}

export default function GeneratePage() {
  const [module, setModule] = useState<GenerationModule>("reading");
  const [devMode, setDevMode] = useState(true);

  const [topic, setTopic] = useState("Urban vertical farming");
  const [questionCount, setQuestionCount] = useState(1);
  const [targetBand, setTargetBand] = useState(7);
  const [sourceMode, setSourceMode] = useState<PassageSourceMode>("ingested");
  const [sourceText, setSourceText] = useState("");
  const [licenseLabel, setLicenseLabel] = useState("Original — internal use");
  const [adaptationLevel, setAdaptationLevel] = useState<"light" | "none" | "deep">("light");

  const [listeningSection, setListeningSection] = useState<1 | 2>(1);
  const [listeningQuestions, setListeningQuestions] = useState(10);
  const [accent, setAccent] = useState("british");

  const [writingType, setWritingType] = useState<WritingQuestionType>("opinion");

  const [topicDomain, setTopicDomain] = useState("Learning and skills");

  const [activeRun, setActiveRun] = useState<GenerationRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(DEV_MODE_STORAGE_KEY);
    if (stored !== null) {
      setDevMode(stored === "true");
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(DEV_MODE_STORAGE_KEY, String(devMode));
    if (devMode) {
      setQuestionCount(1);
      setListeningQuestions(1);
    }
  }, [devMode]);

  const effectiveQuestionCount = devMode ? 1 : questionCount;
  const effectiveListeningQuestions = devMode ? 1 : listeningQuestions;

  const needsSourceText = module === "reading" && sourceMode !== "generated";
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
      const idempotencyKey = crypto.randomUUID();
      let run: GenerationRun;
      if (module === "reading") {
        run = await createReadingRun({
          topic,
          questionCount: effectiveQuestionCount,
          targetBand,
          sourceMode,
          sourceText: needsSourceText ? sourceText : undefined,
          licenseLabel: sourceMode === "adapted" ? licenseLabel : undefined,
          adaptationLevel: sourceMode === "adapted" ? adaptationLevel : undefined,
          devMode,
          idempotencyKey,
        });
      } else if (module === "listening") {
        run = await createListeningRun({
          topic,
          section: listeningSection,
          questionCount: effectiveListeningQuestions,
          targetBand,
          accent,
          devMode,
          idempotencyKey,
        });
      } else if (module === "writing") {
        run = await createWritingRun({
          topic,
          questionType: writingType,
          targetBand,
          devMode,
          idempotencyKey,
        });
      } else {
        run = await createSpeakingRun({
          topicDomain,
          targetBand,
          devMode,
          idempotencyKey,
        });
      }
      setActiveRun(run);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start run");
    } finally {
      setSubmitting(false);
    }
  }

  async function onCancelRun() {
    if (!activeRun) return;
    setCancelling(true);
    setError(null);
    try {
      const updated = await cancelRun(activeRun.run_id);
      setActiveRun(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to cancel run");
    } finally {
      setCancelling(false);
    }
  }

  const selectedModule = MODULES.find((entry) => entry.id === module);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Generate content</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Choose a module, configure the run, and queue generation through the quality gates.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {MODULES.map((entry) => (
          <button
            key={entry.id}
            type="button"
            onClick={() => setModule(entry.id)}
            className={`rounded-md px-4 py-2 text-sm ${
              module === entry.id
                ? "bg-zinc-900 text-white"
                : "border border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50"
            }`}
          >
            {entry.label}
          </button>
        ))}
      </div>

      {selectedModule ? (
        <p className="text-sm text-zinc-600">{selectedModule.description}</p>
      ) : null}

      <section className="max-w-3xl rounded-xl border border-amber-200 bg-amber-50 p-4">
        <label className="flex cursor-pointer items-start gap-3 text-sm">
          <input
            type="checkbox"
            checked={devMode}
            onChange={(event) => setDevMode(event.target.checked)}
            className="mt-1"
          />
          <span>
            <span className="font-medium text-amber-950">Dev mode (recommended for local testing)</span>
            <span className="mt-1 block text-amber-900/80">
              Uses 1 question for Reading/Listening, skips originality, dedup, and critic/reviser
              loops. Set <code className="rounded bg-amber-100 px-1">LLM_PROFILE=fast</code> in{" "}
              <code className="rounded bg-amber-100 px-1">backend/.env</code> and restart the worker
              for the fastest runs. Turn off for full quality-path validation.
            </span>
          </span>
        </label>
      </section>

      <form
        onSubmit={onSubmit}
        className="grid max-w-3xl gap-4 rounded-xl border border-zinc-200 bg-white p-6"
      >
        {module === "reading" ? (
          <>
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
              <span className="mt-1 block text-xs text-zinc-500">
                {SOURCE_MODE_HELP[sourceMode]}
              </span>
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
                    {wordCount} words — IELTS requires {PASSAGE_WORD_MIN}–{PASSAGE_WORD_MAX}.
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
                  value={effectiveQuestionCount}
                  onChange={(event) => setQuestionCount(Number(event.target.value))}
                  disabled={devMode}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 disabled:bg-zinc-100"
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
          </>
        ) : null}

        {module === "listening" ? (
          <>
            <label className="text-sm">
              <span className="mb-1 block text-zinc-700">Topic / scenario</span>
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                className="w-full rounded-md border border-zinc-300 px-3 py-2"
                required
              />
            </label>
            <div className="grid grid-cols-2 gap-4">
              <label className="text-sm">
                <span className="mb-1 block text-zinc-700">Section</span>
                <select
                  value={listeningSection}
                  onChange={(event) => setListeningSection(Number(event.target.value) as 1 | 2)}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2"
                >
                  <option value={1}>Section 1 — conversation</option>
                  <option value={2}>Section 2 — monologue</option>
                </select>
              </label>
              <label className="text-sm">
                <span className="mb-1 block text-zinc-700">Accent</span>
                <select
                  value={accent}
                  onChange={(event) => setAccent(event.target.value)}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2"
                >
                  <option value="british">British</option>
                  <option value="australian">Australian</option>
                  <option value="north_american">North American</option>
                </select>
              </label>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <label className="text-sm">
                <span className="mb-1 block text-zinc-700">Questions</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={effectiveListeningQuestions}
                  onChange={(event) => setListeningQuestions(Number(event.target.value))}
                  disabled={devMode}
                  className="w-full rounded-md border border-zinc-300 px-3 py-2 disabled:bg-zinc-100"
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
          </>
        ) : null}

        {module === "writing" ? (
          <>
            <label className="text-sm">
              <span className="mb-1 block text-zinc-700">Topic</span>
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                className="w-full rounded-md border border-zinc-300 px-3 py-2"
                required
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-zinc-700">Question type</span>
              <select
                value={writingType}
                onChange={(event) => setWritingType(event.target.value as WritingQuestionType)}
                className="w-full rounded-md border border-zinc-300 px-3 py-2"
              >
                {WRITING_TYPES.map((entry) => (
                  <option key={entry.value} value={entry.value}>
                    {entry.label}
                  </option>
                ))}
              </select>
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
          </>
        ) : null}

        {module === "speaking" ? (
          <>
            <label className="text-sm">
              <span className="mb-1 block text-zinc-700">Topic domain</span>
              <input
                value={topicDomain}
                onChange={(event) => setTopicDomain(event.target.value)}
                className="w-full rounded-md border border-zinc-300 px-3 py-2"
                placeholder="e.g. Learning and skills"
                required
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
          </>
        ) : null}

        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button
          type="submit"
          disabled={submitting || (needsSourceText && !wordCountOk)}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-60"
        >
          {submitting ? "Starting…" : `Start ${selectedModule?.label ?? "generation"}`}
        </button>
      </form>

      {activeRun ? (
        <RunStatusPanel
          activeRun={activeRun}
          onCancel={() => void onCancelRun()}
          cancelling={cancelling}
        />
      ) : null}
    </div>
  );
}
