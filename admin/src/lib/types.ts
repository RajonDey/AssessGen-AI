export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type UserMe = {
  id: string;
  email: string;
  role: string;
  organization_id: string;
};

export type GenerationModule = "reading" | "listening" | "writing" | "speaking";

export type PassageSourceMode = "generated" | "ingested" | "adapted";

export type WritingQuestionType =
  | "opinion"
  | "discussion"
  | "problem_solution"
  | "advantages_disadvantages"
  | "two_part";

export type GenerationRun = {
  run_id: string;
  status: string;
  module: string;
  created_at: string;
  failure_reason: string | null;
  queue_ahead?: number | null;
  started_at?: string | null;
};

export type ReviewPreviewItem = {
  id: string;
  item_type: string;
  stem: string | null;
  sequence_no: number | null;
};

export type ReviewQueueItem = {
  run_id: string;
  module: string;
  topic: string | null;
  created_at: string;
  interrupt_payload?: {
    passage_id?: string;
    passage_title?: string;
    passage_body?: string;
    item_count?: number;
    items?: ReviewPreviewItem[];
  } | null;
};

export type PassageSummary = {
  id: string;
  module: string;
  status: string;
  title: string | null;
  word_count: number | null;
  target_band: number | null;
  created_at: string;
};

export type ItemSummary = {
  id: string;
  module: string;
  status: string;
  item_type: string;
  stem: string | null;
  passage_id: string | null;
  sequence_no: number | null;
  created_at: string;
};
