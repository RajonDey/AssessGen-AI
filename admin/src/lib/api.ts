import type { GenerateRequest, GenerateResponse, ProgressEvent } from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.trim() || "http://127.0.0.1:8080";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function formatDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return fallback;
}

export async function generateContentStream(
  body: GenerateRequest,
  onEvent: (event: ProgressEvent) => void,
): Promise<GenerateResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/generate/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Network request failed";
    throw new ApiError(
      `Cannot reach API at ${API_URL} (${message}). Is uvicorn running on :8080?`,
      0,
    );
  }

  if (!response.ok || !response.body) {
    let detail = response.statusText || "Request failed";
    try {
      const problem = (await response.json()) as { detail?: unknown };
      detail = formatDetail(problem.detail, detail);
    } catch {
      // ignore
    }
    throw new ApiError(detail, response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: GenerateResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const event = JSON.parse(trimmed) as ProgressEvent;
      onEvent(event);
      if (event.stage === "error") {
        throw new ApiError(event.message, 502);
      }
      if (event.stage === "done" && event.result) {
        finalResult = event.result;
      }
    }
  }

  if (!finalResult) {
    throw new ApiError("Stream ended without a result", 502);
  }
  return finalResult;
}

function triggerDownload(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadJson(filename: string, data: unknown) {
  triggerDownload(
    filename,
    new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    }),
  );
}

export function downloadText(filename: string, text: string) {
  const isMd = filename.endsWith(".md");
  triggerDownload(
    filename,
    new Blob([text], {
      type: isMd ? "text/markdown;charset=utf-8" : "text/plain;charset=utf-8",
    }),
  );
}

/** Prefer document field; otherwise pretty JSON. */
export function contentAsDownloadText(content: Record<string, unknown>): {
  text: string;
  ext: "md" | "txt" | "json";
} {
  const doc = content.document;
  if (typeof doc === "string" && doc.trim()) {
    const format = String(content.format || "markdown");
    return {
      text: doc,
      ext: format === "text" ? "txt" : "md",
    };
  }
  return {
    text: JSON.stringify(content, null, 2),
    ext: "json",
  };
}

export async function getTtsStatus(): Promise<{
  available: boolean;
  engine?: string;
  hint?: string;
  sample_rate?: number;
}> {
  const response = await fetch(`${API_URL}/api/v1/listening/tts-status`);
  if (!response.ok) {
    throw new ApiError("Failed to check TTS status", response.status);
  }
  return (await response.json()) as {
    available: boolean;
    engine?: string;
    hint?: string;
    sample_rate?: number;
  };
}

export async function synthesizeListeningAudio(file: File): Promise<{
  blob: Blob;
  durationSeconds?: string;
  turns?: string;
}> {
  const form = new FormData();
  form.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/listening/synthesize`, {
      method: "POST",
      body: form,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Network request failed";
    throw new ApiError(
      `Cannot reach API at ${API_URL} (${message}). Is uvicorn running on :8080?`,
      0,
    );
  }

  if (!response.ok) {
    let detail = response.statusText || "Synthesis failed";
    try {
      const problem = (await response.json()) as { detail?: unknown };
      detail = formatDetail(problem.detail, detail);
    } catch {
      // ignore
    }
    throw new ApiError(detail, response.status);
  }

  const blob = await response.blob();
  return {
    blob,
    durationSeconds: response.headers.get("X-Audio-Duration-Seconds") || undefined,
    turns: response.headers.get("X-Audio-Turns") || undefined,
  };
}
