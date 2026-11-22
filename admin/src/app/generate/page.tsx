"use client";

import { FormEvent, useMemo, useState } from "react";

import { ApiError, downloadJson, downloadText, generateContentStream } from "@/lib/api";
import {
  contentAsListeningScriptMarkdown,
  contentAsPaperMarkdown,
  contentAsTtsJson,
  exportPdfWithPrintFallback,
} from "@/lib/paperExports";
import type {
  GenerateResponse,
  ModuleName,
  ProgressEvent,
  QualityMode,
  Task1Kind,
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

const TASK1_KINDS: { value: Task1Kind; label: string }[] = [
  { value: "bar_chart", label: "Bar chart" },
  { value: "line_graph", label: "Line graph" },
  { value: "pie_chart", label: "Pie chart" },
  { value: "table", label: "Table" },
  { value: "process", label: "Process" },
  { value: "map", label: "Map" },
  { value: "mixed", label: "Mixed visuals" },
  { value: "letter_formal", label: "Letter (formal)" },
  { value: "letter_semi_formal", label: "Letter (semi-formal)" },
  { value: "letter_informal", label: "Letter (informal)" },
];

const DEFAULT_TOPICS: Record<ModuleName, string[]> = {
  reading: [
    "urban green spaces",
    "history of photography",
    "marine biodiversity",
  ],
  listening: [
    "hostel booking enquiry",
    "community centre renovation",
    "student project meeting",
    "lecture on sleep research",
  ],
  writing: ["household energy use 2000–2020", "remote work and cities"],
};

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
  const [topics, setTopics] = useState<string[]>([...DEFAULT_TOPICS.reading]);
  const [band, setBand] = useState(6.5);
  const [partCount, setPartCount] = useState(1);
  const [writingType, setWritingType] = useState<WritingType>("opinion");
  const [task1Kind, setTask1Kind] = useState<Task1Kind>("bar_chart");
  const [qualityMode, setQualityMode] = useState<QualityMode>("standard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [reasoning, setReasoning] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [stage, setStage] = useState<ProgressEvent["stage"] | null>(null);
  const [statusLine, setStatusLine] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [downloadTab, setDownloadTab] = useState<"pdf" | "md">("pdf");

  const moduleMeta = useMemo(
    () => MODULES.find((m) => m.id === module) ?? MODULES[0],
    [module],
  );

  const primaryTopic = topics[0]?.trim() || "practice topic";

  function resizeTopics(nextModule: ModuleName, nextParts: number) {
    const defaults = DEFAULT_TOPICS[nextModule];
    setTopics((prev) => {
      const next = Array.from({ length: nextParts }, (_, i) => {
        if (prev[i]?.trim()) return prev[i];
        return defaults[i] ?? defaults[0] ?? "practice topic";
      });
      return next;
    });
  }

  function selectModule(id: ModuleName) {
    setModule(id);
    const meta = MODULES.find((m) => m.id === id)!;
    const nextParts = Math.min(partCount, meta.maxParts);
    setPartCount(nextParts);
    resizeTopics(id, nextParts);
  }

  function onPartCount(n: number) {
    setPartCount(n);
    resizeTopics(module, n);
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

    const partTopics = topics.slice(0, partCount).map((t) => t.trim());
    if (partTopics.some((t) => t.length < 2)) {
      setError("Each part needs its own topic (at least 2 characters).");
      setLoading(false);
      setStage("error");
      return;
    }

    try {
      const data = await generateContentStream(
        {
          module,
          topic: partTopics[0],
          topics: partTopics,
          target_band: band,
          question_count:
            module === "reading"
              ? partCount === 3
                ? 40
                : partCount * 13
              : partCount * 10,
          part_count: partCount,
          writing_type: writingType,
          task2_kind: writingType,
          task1_kind: task1Kind,
          topic_t1: module === "writing" ? partTopics[0] : undefined,
          topic_t2:
            module === "writing" && partCount >= 2 ? partTopics[1] : undefined,
          full_paper: partCount === moduleMeta.maxParts,
          quality_mode: qualityMode,
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

  function fileBase(): string {
    const safe = primaryTopic.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
    return `assessgen-${module}-${safe || "paper"}`;
  }

  /** External export: questions + answers only (no illustrator briefs). */
  function paperMarkdownForPdf(): string {
    if (!result) return "";
    return contentAsPaperMarkdown(module, result.content as Record<string, unknown>, {
      includeVisualBriefs: false,
    });
  }

  /** Dev export: full paper including visual/image briefs. */
  function paperMarkdownForDev(): string {
    if (!result) return "";
    return contentAsPaperMarkdown(module, result.content as Record<string, unknown>, {
      includeVisualBriefs: true,
    });
  }

  function onDownloadFailedDraft() {
    if (!result) return;
    downloadJson(`${fileBase()}-FAILED-DRAFT.json`, {
      ...result.content,
      _meta: {
        module: result.module,
        topic: result.topic,
        topics: result.topics,
        type_plan: result.type_plan,
        target_band: result.target_band,
        part_count: result.part_count,
        session_id: result.session_id,
        parts_linked: result.parts_linked,
        generator_model: result.generator_model,
        reviewer_model: result.reviewer_model,
        review: result.review,
        reasoning: result.reasoning,
        download_warning: "Failed review — not TTS-ready",
      },
    });
  }

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast((cur) => (cur === message ? null : cur)), 6000);
  }

  function onDownloadPaperMd() {
    if (!result) return;
    downloadText(`${fileBase()}-paper.md`, paperMarkdownForDev());
  }

  function onDownloadPaperPdf() {
    if (!result) return;
    try {
      const tip = exportPdfWithPrintFallback(
        `${fileBase()}-paper.pdf`,
        `${fileBase()}-paper`,
        paperMarkdownForPdf(),
      );
      showToast(tip);
    } catch (err) {
      setError(err instanceof Error ? err.message : "PDF export failed");
    }
  }

  function onDownloadTtsJson() {
    if (!result || module !== "listening") return;
    if (jsonDownloadBlocked) return;
    const tts = contentAsTtsJson(result.content as Record<string, unknown>);
    downloadJson(`${fileBase()}-tts.json`, tts);
  }

  function onDownloadScriptMd() {
    if (!result || module !== "listening") return;
    downloadText(
      `${fileBase()}-script.md`,
      contentAsListeningScriptMarkdown(result.content as Record<string, unknown>),
    );
  }

  function onDownloadScriptPdf() {
    if (!result || module !== "listening") return;
    try {
      const tip = exportPdfWithPrintFallback(
        `${fileBase()}-script.pdf`,
        `${fileBase()}-script`,
        contentAsListeningScriptMarkdown(
          result.content as Record<string, unknown>,
        ),
      );
      showToast(tip);
    } catch (err) {
      setError(err instanceof Error ? err.message : "PDF export failed");
    }
  }

  const displayDoc = useMemo(() => {
    if (!result) return null;
    const content = result.content as Record<string, unknown>;
    // Preview matches MD/dev export (includes visual briefs when present)
    const paper = contentAsPaperMarkdown(module, content, {
      includeVisualBriefs: true,
    });
    if (paper.trim().length > 40) return paper;
    if (typeof content.document === "string" && content.document.trim()) {
      return String(content.document);
    }
    return null;
  }, [result, module]);
  const mustFindings = useMemo(
    () => (result?.review.findings ?? []).filter((f) => f.severity === "must"),
    [result],
  );
  // Kokoro: script/clock/length only (content.tts_ready). Answer-key musts do not block.
  const jsonDownloadBlocked =
    module === "listening" &&
    !!result &&
    ((result.content as { tts_ready?: unknown }).tts_ready === false ||
      ((result.content as { tts_ready?: unknown }).tts_ready !== true &&
        mustFindings.some((f) => {
          const code = f.code || "";
          return (
            code.startsWith("L-WC") ||
            code.startsWith("L-PAUSE") ||
            code.startsWith("L-INTRO") ||
            code.startsWith("L-SCR") ||
            code.startsWith("L-TURN") ||
            code.startsWith("L-LISTEN") ||
            code === "L-SP-CNT"
          );
        })));
  const paperMustFindings = mustFindings.filter((f) => {
    const code = f.code || "";
    return !(
      code.startsWith("L-WC") ||
      code.startsWith("L-PAUSE") ||
      code.startsWith("L-INTRO") ||
      code.startsWith("L-SCR") ||
      code.startsWith("L-TURN") ||
      code.startsWith("L-LISTEN") ||
      code === "L-SP-CNT"
    );
  });
  const contentWords =
    result && typeof (result.content as { content_word_count?: unknown }).content_word_count === "number"
      ? Number((result.content as { content_word_count: number }).content_word_count)
      : null;
  const spokenWords =
    result && typeof (result.content as { word_count?: unknown }).word_count === "number"
      ? Number((result.content as { word_count: number }).word_count)
      : null;
  const estimatedDuration =
    result &&
    typeof (result.content as { estimated_duration_seconds?: unknown }).estimated_duration_seconds ===
      "number"
      ? Number((result.content as { estimated_duration_seconds: number }).estimated_duration_seconds)
      : null;

  return (
    <div className="space-y-8">
      {toast && (
        <div
          role="status"
          className="fixed bottom-6 left-1/2 z-50 max-w-lg -translate-x-1/2 rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 shadow-lg"
        >
          {toast}
        </div>
      )}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Generate practice paper</h1>
        <p className="mt-1 max-w-2xl text-sm text-zinc-600">
          Choose a module and how many parts to create. Give each Listening/Reading part
          (and Writing Task 1 / Task 2) its own independent topic. Question types interlock
          across the paper via a BC-style type plan (defaults applied server-side). Listening
          outputs a TTS-ready script (speakers + turns) plus questions.
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

          <div className="space-y-3">
            <p className="text-sm font-medium text-zinc-700">
              {module === "writing" ? "Task topics (independent)" : "Topics per part (independent)"}
            </p>
            {Array.from({ length: partCount }, (_, i) => (
              <label key={i} className="block text-sm">
                <span className="text-zinc-600">
                  {module === "writing"
                    ? i === 0
                      ? "Task 1 topic"
                      : "Task 2 topic"
                    : `Part ${i + 1} topic`}
                </span>
                <input
                  className="mt-1.5 w-full rounded-xl border border-zinc-300 px-3 py-2.5 outline-none focus:border-zinc-900"
                  value={topics[i] ?? ""}
                  onChange={(e) => {
                    const value = e.target.value;
                    setTopics((prev) => {
                      const next = [...prev];
                      next[i] = value;
                      return next;
                    });
                  }}
                  placeholder={
                    module === "listening"
                      ? "e.g. library membership enquiry"
                      : "e.g. climate, banking, education"
                  }
                  required
                />
              </label>
            ))}
            <p className="text-xs text-zinc-500">
              British Council papers use unrelated topics across parts — not one shared theme.
            </p>
          </div>

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
                      onClick={() => onPartCount(n)}
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
                    ? "1 passage section (Questions 1–13)"
                    : partCount === 3
                      ? "Full Academic Reading (40 Qs: 1–13 / 14–26 / 27–40) — sections generated sequentially"
                      : `${partCount} passage sections — continuous numbering; later sections track question types`)}
                {module === "writing" &&
                  (partCount === 1
                    ? "Task 1 only — question + visual brief for external image vendor"
                    : "Task 1 + Task 2 — separate topics and kinds")}
                {module === "listening" &&
                  (partCount === 4
                    ? "Full Listening (4×10) — each part uses exam-clock pauses (~6–8 min audio)"
                    : partCount === 1
                      ? "1 Listening part: 10 questions, two listenings + pauses (target ~6–8 min WAV)"
                      : `${partCount} Listening parts — each 10 questions, sequential exam-clock scripts`)}
              </p>
            </div>
          </div>

          <div>
            <p className="text-sm font-medium text-zinc-700">Quality mode</p>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {(
                [
                  ["draft", "Draft (rules only)"],
                  ["standard", "Standard (+critic)"],
                  ["publish", "Publish (+originality)"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setQualityMode(id)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                    qualityMode === id
                      ? "border-zinc-900 bg-zinc-900 text-white"
                      : "border-zinc-300 bg-white text-zinc-700"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-zinc-500">
              Draft skips the LLM critic. Standard runs critic only after rules pass.
              Publish adds an 8-gram originality check when a reference corpus path is configured.
            </p>
          </div>

          {module === "writing" && (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="font-medium text-zinc-700">Task 1 kind</span>
                <select
                  className="mt-1.5 w-full rounded-xl border border-zinc-300 px-3 py-2.5"
                  value={task1Kind}
                  onChange={(e) => setTask1Kind(e.target.value as Task1Kind)}
                >
                  {TASK1_KINDS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
              {partCount >= 2 && (
                <label className="block text-sm">
                  <span className="font-medium text-zinc-700">Task 2 kind</span>
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
            </div>
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
                    {result.quality_mode ? ` · ${result.quality_mode}` : ""}
                    {result.cost
                      ? ` · ${result.cost.llm_calls} LLM calls (plan ${result.cost.planner_calls}/gen ${result.cost.generator_calls}/critic ${result.cost.critic_calls})`
                      : ""}
                  </span>
                </div>
                {module === "listening" && (
                  <p className="text-xs text-zinc-500">
                    PDF = external paper (Q+A only). MD = full paper for development
                    (includes image briefs). TTS JSON = Kokoro script only.
                  </p>
                )}
                {module !== "listening" && (
                  <p className="text-xs text-zinc-500">
                    PDF = external export (Q+A only). MD = development (includes visual
                    briefs when present).
                  </p>
                )}
                <div className="space-y-3">
                  <div className="flex gap-1 rounded-xl border border-zinc-200 bg-zinc-50 p-1">
                    {(
                      [
                        ["pdf", "PDF"],
                        ["md", "MD"],
                      ] as const
                    ).map(([id, label]) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setDownloadTab(id)}
                        className={`flex-1 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                          downloadTab === id
                            ? "bg-zinc-900 text-white"
                            : "text-zinc-600 hover:bg-zinc-100"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {downloadTab === "pdf" && (
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={onDownloadPaperPdf}
                        className="rounded-xl border border-zinc-900 bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
                      >
                        Download paper (PDF)
                      </button>
                      {module === "listening" && (
                        <button
                          type="button"
                          onClick={onDownloadScriptPdf}
                          className="rounded-xl border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
                        >
                          Download script (PDF)
                        </button>
                      )}
                    </div>
                  )}

                  {downloadTab === "md" && (
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={onDownloadPaperMd}
                        className="rounded-xl border border-zinc-900 bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
                      >
                        Download paper (MD)
                      </button>
                      {module === "listening" && (
                        <>
                          <button
                            type="button"
                            onClick={onDownloadScriptMd}
                            className="rounded-xl border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50"
                          >
                            Download script (MD)
                          </button>
                          <button
                            type="button"
                            onClick={onDownloadTtsJson}
                            disabled={jsonDownloadBlocked}
                            title={
                              jsonDownloadBlocked
                                ? "Fix must findings / re-generate before downloading TTS JSON"
                                : "speakers[] + script.turns[] for Listening Audio"
                            }
                            className="rounded-xl border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            Download TTS JSON
                          </button>
                          {jsonDownloadBlocked && (
                            <button
                              type="button"
                              onClick={onDownloadFailedDraft}
                              className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-100"
                            >
                              Download failed draft
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  )}

                  <p className="text-xs text-zinc-500">
                    {downloadTab === "pdf" &&
                      "External export: questions + answer key only (no visual briefs)."}
                    {downloadTab === "md" &&
                      (module === "listening"
                        ? "Dev paper MD includes visual briefs. TTS JSON is the only script payload for Kokoro."
                        : "Dev paper MD includes questions, answers, and visual/image briefs.")}
                  </p>
                </div>
              </div>
              {jsonDownloadBlocked && (                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
                  <p className="font-medium">Not TTS-ready — Download TTS JSON is blocked.</p>
                  <p className="mt-1 text-amber-900">
                    Script / exam-clock / length rules failed
                    {spokenWords != null ? ` (spoken words: ${spokenWords}` : ""}
                    {contentWords != null ? `, content: ${contentWords}` : ""}
                    {estimatedDuration != null
                      ? `, est. ${Math.round(estimatedDuration / 60)} min)`
                      : spokenWords != null
                        ? ")"
                        : ""}
                    . Answer keys do not block Kokoro — fix the spoken script first. Paper MD/PDF
                    downloads remain available.
                  </p>
                </div>
              )}

              {module === "listening" && !jsonDownloadBlocked && paperMustFindings.length > 0 && (
                <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950">
                  <p className="font-medium">TTS OK — paper quality still needs attention</p>
                  <p className="mt-1">
                    You can download TTS JSON for Kokoro. Fix answer keys / questions before
                    publishing the practice paper.
                  </p>
                </div>
              )}

              {module === "listening" && !jsonDownloadBlocked && (
                <p className="text-xs text-zinc-600">
                  TTS-ready
                  {spokenWords != null ? ` · ${spokenWords} spoken` : ""}
                  {contentWords != null ? ` · ${contentWords} content` : ""}
                  {estimatedDuration != null
                    ? ` · ~${Math.round(estimatedDuration / 60)} min estimated`
                    : ""}
                </p>
              )}

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
