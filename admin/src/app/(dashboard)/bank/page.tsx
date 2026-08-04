"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, fetchItems, fetchPassage, fetchPassages } from "@/lib/api";
import type { GenerationModule, ItemSummary, PassageSummary } from "@/lib/types";

type Tab = "passages" | "items";

const MODULE_FILTER_OPTIONS: { value: "all" | GenerationModule; label: string }[] = [
  { value: "all", label: "All modules" },
  { value: "reading", label: "Reading" },
  { value: "listening", label: "Listening" },
  { value: "writing", label: "Writing" },
  { value: "speaking", label: "Speaking" },
];

function moduleLabel(module: string): string {
  const match = MODULE_FILTER_OPTIONS.find((entry) => entry.value === module);
  return match?.label ?? module;
}

export default function BankPage() {
  const [tab, setTab] = useState<Tab>("passages");
  const [moduleFilter, setModuleFilter] = useState<"all" | GenerationModule>("all");
  const [passages, setPassages] = useState<PassageSummary[]>([]);
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [selectedPassageId, setSelectedPassageId] = useState<string | null>(null);
  const [passageBody, setPassageBody] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [passageResponse, itemResponse] = await Promise.all([
        fetchPassages(),
        fetchItems(),
      ]);
      setPassages(passageResponse.items);
      setItems(itemResponse.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load bank");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredPassages = useMemo(
    () =>
      moduleFilter === "all"
        ? passages
        : passages.filter((passage) => passage.module === moduleFilter),
    [moduleFilter, passages],
  );

  const filteredItems = useMemo(
    () =>
      moduleFilter === "all" ? items : items.filter((item) => item.module === moduleFilter),
    [moduleFilter, items],
  );

  async function inspectPassage(id: string) {
    setSelectedPassageId(id);
    setPassageBody(null);
    try {
      const detail = await fetchPassage(id);
      setPassageBody(detail.body ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load passage");
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Content bank</h1>
          <p className="mt-1 text-sm text-zinc-600">Browse generated passages and items.</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="rounded-md border border-zinc-300 bg-white px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-50 disabled:opacity-60"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-2">
          {(["passages", "items"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setTab(value)}
              className={`rounded-md px-4 py-2 text-sm ${
                tab === value
                  ? "bg-zinc-900 text-white"
                  : "border border-zinc-300 bg-white text-zinc-700"
              }`}
            >
              {value === "passages" ? "Passages" : "Items"}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm text-zinc-700">
          <span>Module</span>
          <select
            value={moduleFilter}
            onChange={(event) =>
              setModuleFilter(event.target.value as "all" | GenerationModule)
            }
            className="rounded-md border border-zinc-300 px-3 py-2"
          >
            {MODULE_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {tab === "passages" ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
            <table className="min-w-full text-sm">
              <thead className="bg-zinc-50 text-left text-zinc-600">
                <tr>
                  <th className="px-4 py-3">Module</th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Words</th>
                </tr>
              </thead>
              <tbody>
                {filteredPassages.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-zinc-500">
                      No passages yet. Complete a generation run and approve it on Review.
                    </td>
                  </tr>
                ) : (
                  filteredPassages.map((passage) => (
                    <tr
                      key={passage.id}
                      className="cursor-pointer border-t border-zinc-100 hover:bg-zinc-50"
                      onClick={() => void inspectPassage(passage.id)}
                    >
                      <td className="px-4 py-3 capitalize">{moduleLabel(passage.module)}</td>
                      <td className="px-4 py-3">{passage.title ?? "Untitled"}</td>
                      <td className="px-4 py-3 capitalize">
                        {passage.status.replaceAll("_", " ")}
                      </td>
                      <td className="px-4 py-3">{passage.word_count ?? "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div className="rounded-xl border border-zinc-200 bg-white p-6">
            <h2 className="text-lg font-medium text-zinc-900">Passage preview</h2>
            {selectedPassageId ? (
              <pre className="mt-4 max-h-[480px] overflow-auto whitespace-pre-wrap text-sm text-zinc-700">
                {passageBody ?? "Loading…"}
              </pre>
            ) : (
              <p className="mt-4 text-sm text-zinc-500">Select a passage to preview.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-50 text-left text-zinc-600">
              <tr>
                <th className="px-4 py-3">Module</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Stem</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-zinc-500">
                    No items yet.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr key={item.id} className="border-t border-zinc-100">
                    <td className="px-4 py-3 capitalize">{moduleLabel(item.module)}</td>
                    <td className="px-4 py-3">{item.item_type}</td>
                    <td className="px-4 py-3">{item.stem ?? "—"}</td>
                    <td className="px-4 py-3 capitalize">{item.status.replaceAll("_", " ")}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
