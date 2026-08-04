"use client";

import { useEffect, useState } from "react";

import { ApiError, fetchReviewQueue, resumeRun } from "@/lib/api";
import type { GenerationModule, ReviewQueueItem } from "@/lib/types";

const MODULE_LABELS: Record<GenerationModule, string> = {
  reading: "Reading",
  listening: "Listening",
  writing: "Writing",
  speaking: "Speaking",
};

function moduleLabel(module: string): string {
  return MODULE_LABELS[module as GenerationModule] ?? module;
}

function formatPreviewBody(module: string, body: string): string {
  if (module === "speaking") {
    try {
      return JSON.stringify(JSON.parse(body), null, 2);
    } catch {
      return body;
    }
  }
  return body;
}

function previewHeading(item: ReviewQueueItem): string {
  const payload = item.interrupt_payload;
  if (payload?.passage_title) {
    return payload.passage_title;
  }
  return item.topic ?? `${moduleLabel(item.module)} run`;
}

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadQueue() {
    setError(null);
    try {
      const response = await fetchReviewQueue();
      setItems(response.items);
      if (response.items.length && !selectedId) {
        setSelectedId(response.items[0].run_id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load queue");
    }
  }

  useEffect(() => {
    void loadQueue();
  }, []);

  const selected = items.find((item) => item.run_id === selectedId) ?? null;
  const preview = selected?.interrupt_payload;

  async function submit(decision: "approve" | "reject") {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await resumeRun(selected.run_id, { decision, notes: notes || undefined });
      setMessage(decision === "approve" ? "Approved and run completed." : "Rejected.");
      setNotes("");
      setSelectedId(null);
      await loadQueue();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Review action failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Review queue</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Approve or reject runs paused after generation.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <section className="rounded-xl border border-zinc-200 bg-white">
          <div className="border-b border-zinc-200 px-4 py-3 text-sm font-medium">
            Awaiting review ({items.length})
          </div>
          <ul className="divide-y divide-zinc-100">
            {items.length === 0 ? (
              <li className="px-4 py-6 text-sm text-zinc-500">Queue is empty.</li>
            ) : (
              items.map((item) => (
                <li key={item.run_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(item.run_id)}
                    className={`block w-full px-4 py-3 text-left text-sm hover:bg-zinc-50 ${
                      selectedId === item.run_id ? "bg-zinc-100" : ""
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-zinc-200 px-1.5 py-0.5 text-xs font-medium capitalize text-zinc-700">
                        {moduleLabel(item.module)}
                      </span>
                      <span className="font-medium">{item.topic ?? "Untitled run"}</span>
                    </div>
                    <div className="mt-1 font-mono text-xs text-zinc-500">{item.run_id}</div>
                  </button>
                </li>
              ))
            )}
          </ul>
        </section>

        <section className="space-y-6">
          <div className="rounded-xl border border-zinc-200 bg-white p-6">
            {selected ? (
              <div className="space-y-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded bg-zinc-900 px-2 py-0.5 text-xs font-medium text-white capitalize">
                      {moduleLabel(selected.module)}
                    </span>
                    <h2 className="text-lg font-medium text-zinc-900">{previewHeading(selected)}</h2>
                  </div>
                  <p className="mt-1 font-mono text-xs text-zinc-500">{selected.run_id}</p>
                </div>

                {preview?.passage_body ? (
                  <div>
                    <h3 className="text-sm font-medium text-zinc-800">
                      {selected.module === "listening"
                        ? "Script transcript"
                        : selected.module === "writing"
                          ? "Task 2 prompt"
                          : selected.module === "speaking"
                            ? "Part 1 + Part 2 content"
                            : "Passage"}
                    </h3>
                    <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-50 p-4 text-sm text-zinc-700">
                      {formatPreviewBody(selected.module, preview.passage_body)}
                    </pre>
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">No preview content loaded for this run.</p>
                )}

                {preview?.items && preview.items.length > 0 ? (
                  <div>
                    <h3 className="text-sm font-medium text-zinc-800">
                      Items ({preview.item_count ?? preview.items.length})
                    </h3>
                    <ul className="mt-2 space-y-2 text-sm">
                      {preview.items.map((item) => (
                        <li
                          key={item.id}
                          className="rounded-md border border-zinc-100 bg-zinc-50 px-3 py-2"
                        >
                          <span className="font-medium">{item.item_type}</span>
                          {item.sequence_no ? (
                            <span className="text-zinc-500"> · Q{item.sequence_no}</span>
                          ) : null}
                          <p className="mt-1 text-zinc-700">{item.stem ?? "—"}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <label className="block text-sm">
                  <span className="mb-1 block text-zinc-700">Notes (optional)</span>
                  <textarea
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    rows={3}
                    className="w-full rounded-md border border-zinc-300 px-3 py-2"
                  />
                </label>
                <div className="flex gap-3">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void submit("approve")}
                    className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-60"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void submit("reject")}
                    className="rounded-md bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-60"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-zinc-500">Select a run from the queue.</p>
            )}
            {error ? <p className="text-sm text-red-600">{error}</p> : null}
            {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
          </div>
        </section>
      </div>
    </div>
  );
}
