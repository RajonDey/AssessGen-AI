"use client";

import { FormEvent, useMemo, useState } from "react";

import { ApiError, contentAsDownloadText, downloadJson, downloadText, generateContentStream } from "@/lib/api";
import type {
  GenerateResponse,
  ModuleName,
  ProgressEvent,
  WritingType,
} from "@/lib/types";

const MODULES: {
  id: ModuleName;
  label: string;
  hint: string;
  maxParts: number;
  partLabel: string;
}[] = [
  {
    id: "reading",
    label: "Reading",
    hint: "Passages + question groups",
    maxParts: 3,
    partLabel: "Sections",
  },
  {
    id: "writing",
    label: "Writing",
    hint: "Task 1 and/or Task 2",
    maxParts: 2,
    partLabel: "Parts",
  },
    {
      id: "listening",
      label: "Listening",
      hint: "JSON with speakers + script.turns (required for audio); 10 questions per part",
      maxParts: 4,
      partLabel: "Parts",
    },
  ];

const WRITING_TYPES: { value: WritingType; label: string }[] = [
  { value: "opinion", label: "Opinion" },
  { value: "discussion", label: "Discussion" },
  { value: "problem_solution", label: "Problem / solution" },
  { value: "advantages_disadvantages", label: "Advantages / disadvantages" },
  { value: "two_part", label: "Two-part" },
];

const STAGE_LABEL: Record<ProgressEvent["stage"], string> = {
  planning: "Planning",
  reasoning: "Reasoning",
  generating: "Generating",
  rules: "Rules check",
  reviewing: "Evaluating",
  revising: "Revising",
  done: "Done",
  error: "Error",
};

export default function GeneratePage() {
  const [module, setModule] = useState<ModuleName>("reading");
  const [topic, setTopic] = useState("urban green spaces");
  const [band, setBand] = useState(6.5);
  const [partCount, setPartCount] = useState(1);
  const [writingType, setWritingType] = useState<WritingType>("opinion");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [reasoning, setReasoning] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [stage, setStage] = useState<ProgressEvent["stage"] | null>(null);
  const [statusLine, setStatusLine] = useState("");

  const moduleMeta = useMemo(
    () => MODULES.find((m) => m.id === module) ?? MODULES[0],
    [module],
  );

  function selectModule(id: ModuleName) {
    setModule(id);
    const meta = MODULES.find((m) => m.id === id)!;
    setPartCount((n) => Math.min(n, meta.maxParts));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setReasoning("");
    setSteps([]);
    setStage("planning");
    setStatusLine("Starting…");

    try {
      const data = await generateContentStream(
        {
          module,
          topic,
          target_band: band,
          question_count: module === "reading" ? partCount * 13 : partCount * 10,
          part_count: partCount,
          writing_type: writingType,
          full_paper: partCount === moduleMeta.maxParts,
        },
        (event) => {
          setStage(event.stage);
          setStatusLine(event.message);
          if (event.reasoning) setReasoning(event.reasoning);
          if (event.step) {
            setSteps((prev) =>
              prev.includes(event.step!) ? prev : [...prev, event.step!],
            );
          }
        },
      );
      setResult(data);
      if (data.reasoning) setReasoning(data.reasoning);
      if (data.plan_steps?.length) setSteps(data.plan_steps);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed");
      setStage("error");
    } finally {
      setLoading(false);
    }
  }

  function onDownloadJson() {
    if (!result) return;
    const safe = topic.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
    downloadJson(`assessgen-${module}-${safe || "paper"}.json`, {
      ...result.content,
      _meta: {
        module: result.module,
        topic: result.topic,
        target_band: result.target_band,
        part_count: result.part_count,
        session_id: result.session_id,
        parts_linked: result.parts_linked,
        generator_model: result.generator_model,
        reviewer_model: result.reviewer_model,
        review: result.review,
        reasoning: result.reasoning,
      },
    });
  }

  function onDownloadDoc() {
    if (!result) return;
    const safe = topic.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
    const { text, ext } = contentAsDownloadText(
      result.content as Record<string, unknown>,
    );
    downloadText(`assessgen-${module}-${safe || "paper"}.${ext}`, text);
  }

  const displayDoc =
    result &&
    typeof (result.content as { document?: unknown }).document === "string"
      ? String((result.content as { document: string }).document)
      : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Generate practice paper</h1>
        <p className="mt-1 max-w-2xl text-sm text-zinc-600">
          Choose a module and how many parts to create. Reading and Listening multi-part
          runs generate each part in order so later parts track earlier ones. Listening
          outputs a TTS-ready script (speakers + turns) plus questions — audio synthesis
          comes later. The model plans with visible reasoning, then generates and reviews.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <form
          onSubmit={onSubmit}
          className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
        >
          <div className="grid gap-3 sm:grid-cols-3">
            {MODULES.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => selectModule(m.id)}
                className={`rounded-xl border px-3 py-3 text-left text-sm transition ${
                  module === m.id
                    ? "border-zinc-900 bg-zinc-900 text-white"
                    : "border-zinc-200 hover:border-zinc-400"
                }`}
              >
                <div className="font-medium">{m.label}</div>
                <div className={module === m.id ? "text-zinc-300" : "text-zinc-500"}>
                  {m.hint}
                </div>
              </button>
            ))}
          </div>

          <label className="block text-sm">
            <span className="font-medium text-zinc-700">Topic</span>
            <input
              className="mt-1.5 w-full rounded-xl border border-zinc-300 px-3 py-2.5 outline-none focus:border-zinc-900"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. climate, banking, education"
              required
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="font-medium text-zinc-700">Target band</span>
              <input
                type="number"
                step="0.5"
                min={4}
                max={9}
                className="mt-1.5 w-full rounded-xl border border-zinc-300 px-3 py-2.5"
                value={band}
                onChange={(e) => setBand(Number(e.target.value))}
              />
            </label>

            <div className="block text-sm">
              <span className="font-medium text-zinc-700">
                {moduleMeta.partLabel} to generate
              </span>
              <div className="mt-1.5 flex flex-wrap gap-2">
                {Array.from({ length: moduleMeta.maxParts }, (_, i) => i + 1).map(
                  (n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setPartCount(n)}
                      className={`min-w-10 rounded-lg border px-3 py-2 text-sm font-medium ${
                        partCount === n
                          ? "border-zinc-900 bg-zinc-900 text-white"
                          : "border-zinc-200 text-zinc-700 hover:border-zinc-400"
                      }`}
                    >
                      {n}
                    </button>
                  ),
                )}
              </div>
              <p className="mt-1.5 text-xs text-zinc-500">
                {module === "reading" &&
                  (partCount === 1
                    ? "1 passage section (~13 questions)"
                    : partCount === 3
                      ? "Full Academic Reading — sections generated one-by-one; each tracks the previous"
                      : `${partCount} passage sections — later sections track earlier ones`)}
                {module === "writing" &&
                  (partCount === 1
                    ? "Task 1 only (visual description)"
                    : "Task 1 + Task 2 (full Writing)")}
                {module === "listening" &&
                  (partCount === 4
                    ? "Full Listening (4×10) — each part uses exam-clock pauses (~6–8 min audio)"
                    : partCount === 1
                      ? "1 Listening part: 10 questions, two listenings + pauses (target ~6–8 min WAV)"
                      : `${partCount} Listening parts — each 10 questions, sequential exam-clock scripts`)}
              </p>
            </div>
          </div>

          {module === "writing" && partCount >= 2 && (
            <label className="block text-sm">
              <span className="font-medium text-zinc-700">Task 2 type</span>
              <select
                className="mt-1.5 w-full rounded-xl border border-zinc-300 px-3 py-2.5"
                value={writingType}
                onChange={(e) => setWritingType(e.target.value as WritingType)}
              >
                {WRITING_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-zinc-900 px-4 py-3 text-sm font-medium text-white disabled:opacity-50 sm:w-auto"
          >
            {loading ? "Generating…" : "Generate paper"}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </form>

        <aside className="space-y-4">
          {(loading || reasoning || steps.length > 0) && (
            <section className="rounded-2xl border border-zinc-200 bg-zinc-950 p-5 text-zinc-100 shadow-sm">
              <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-400">
                {loading && (
                  <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
                )}
                {stage ? STAGE_LABEL[stage] : "Ready"}
              </div>
              <p className="mt-2 text-sm text-zinc-300">{statusLine || "Waiting…"}</p>

              {reasoning && (
                <div className="mt-4">
                  <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    Model reasoning
                  </h2>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-zinc-200">
                    {reasoning}
                  </p>
                </div>
              )}

              {steps.length > 0 && (
                <ol className="mt-4 space-y-2 border-t border-zinc-800 pt-4 text-sm text-zinc-300">
                  {steps.map((step, i) => (
                    <li key={`${step}-${i}`} className="flex gap-2">
                      <span className="text-zinc-500">{i + 1}.</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              )}

              {loading && !reasoning && (
                <div className="mt-4 space-y-2">
                  <div className="h-2 animate-pulse rounded bg-zinc-800" />
                  <div className="h-2 w-5/6 animate-pulse rounded bg-zinc-800" />
                  <div className="h-2 w-2/3 animate-pulse rounded bg-zinc-800" />
                </div>
              )}
            </section>
          )}

          {result && (
            <section className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span
                    className={`rounded-full px-2.5 py-0.5 font-medium ${
                      result.review.passed
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-amber-100 text-amber-900"
                    }`}
                  >
                    {result.review.passed ? "Passed review" : "Needs attention"}
                  </span>
                  <span className="text-zinc-500">
                    {result.part_count} {moduleMeta.partLabel.toLowerCase()}
                    {result.parts_linked && result.parts_linked > 1
                      ? ` · ${result.parts_linked} linked`
                      : ""}{" "}
                    · {result.generator_model}
                  </span>
                </div>
                {module === "listening" && (
                  <p className="text-xs text-zinc-500">
                    For Kokoro audio, use Download JSON (must include speakers and
                    script.turns). Markdown-only papers cannot be synthesized.
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={onDownloadJson}
                    className="rounded-xl border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
                  >
                    Download JSON
                  </button>
                  <button
                    type="button"
                    onClick={onDownloadDoc}
                    className="rounded-xl border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
                  >
                    Download MD/TXT
                  </button>
                </div>
              </div>

              {result.review.summary && (
                <p className="text-sm text-zinc-700">{result.review.summary}</p>
              )}
              {result.review.findings.length > 0 && (
                <ul className="max-h-40 list-disc space-y-1 overflow-auto pl-5 text-sm text-zinc-700">
                  {result.review.findings.map((f, i) => (
                    <li key={`${f.message}-${i}`}>
                      <span className="font-medium uppercase text-zinc-500">
                        {f.severity}
                      </span>{" "}
                      {f.message}
                    </li>
                  ))}
                </ul>
              )}

              {displayDoc ? (
                <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-xl bg-zinc-950 p-4 text-sm leading-relaxed text-zinc-100">
                  {displayDoc}
                </pre>
              ) : (
                <pre className="max-h-[28rem] overflow-auto rounded-xl bg-zinc-950 p-4 text-xs text-zinc-100">
                  {JSON.stringify(result.content, null, 2)}
                </pre>
              )}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
