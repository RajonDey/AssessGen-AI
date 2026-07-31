import { clearToken, getToken } from "./auth";
import type {
  GenerationRun,
  ItemSummary,
  PassageSourceMode,
  PassageSummary,
  ReviewQueueItem,
  TokenResponse,
  UserMe,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (response.status === 401) {
    clearToken();
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const problem = (await response.json()) as { detail?: string; title?: string };
      detail = problem.detail ?? problem.title ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function login(email: string, password: string) {
  return request<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function fetchMe() {
  return request<UserMe>("/api/v1/auth/me");
}

export function createReadingRun(input: {
  topic: string;
  questionCount: number;
  targetBand: number;
  sourceMode?: PassageSourceMode;
  sourceText?: string;
  licenseLabel?: string;
  adaptationLevel?: "none" | "light" | "deep";
  idempotencyKey: string;
}) {
  const spec: Record<string, unknown> = {
    topic: input.topic,
    question_count: input.questionCount,
    target_band: input.targetBand,
    passage_count: 1,
    source_mode: input.sourceMode ?? "generated",
  };
  if (input.sourceText) {
    spec.source_text = input.sourceText;
  }
  if (input.licenseLabel) {
    spec.license_label = input.licenseLabel;
  }
  if (input.adaptationLevel) {
    spec.adaptation_level = input.adaptationLevel;
  }
  return request<GenerationRun>("/api/v1/generation/runs", {
    method: "POST",
    headers: {
      "Idempotency-Key": input.idempotencyKey,
    },
    body: JSON.stringify({
      module: "reading",
      exam: "ielts",
      variant: "academic",
      spec,
    }),
  });
}

export function fetchRun(runId: string) {
  return request<GenerationRun>(`/api/v1/generation/runs/${runId}`);
}

export function fetchReviewQueue() {
  return request<{ items: ReviewQueueItem[] }>("/api/v1/review/queue");
}

export function resumeRun(
  runId: string,
  body: { decision: "approve" | "reject"; notes?: string },
) {
  return request<GenerationRun>(`/api/v1/generation/runs/${runId}/resume`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchPassages() {
  return request<{ items: PassageSummary[] }>("/api/v1/passages");
}

export function fetchItems() {
  return request<{ items: ItemSummary[] }>("/api/v1/items");
}

export function fetchPassage(id: string) {
  return request<PassageSummary & { body?: string | null }>(`/api/v1/passages/${id}`);
}
