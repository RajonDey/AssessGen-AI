export type ModuleName = "reading" | "writing" | "listening";

export type WritingType =
  | "opinion"
  | "discussion"
  | "problem_solution"
  | "advantages_disadvantages"
  | "two_part";

export type ReviewFinding = {
  severity: "must" | "should" | "info";
  message: string;
  code?: string | null;
};

export type GenerateResponse = {
  module: ModuleName;
  topic: string;
  target_band: number;
  part_count: number;
  content: Record<string, unknown>;
  review: {
    passed: boolean;
    findings: ReviewFinding[];
    summary: string;
    source?: string;
  };
  revision_attempts: number;
  provider: string;
  generator_model: string;
  reviewer_model: string;
  reasoning: string;
  plan_steps: string[];
  session_id?: string | null;
  parts_linked?: number;
};

export type GenerateRequest = {
  module: ModuleName;
  topic: string;
  target_band: number;
  question_count: number;
  part_count: number;
  writing_type?: WritingType;
  full_paper?: boolean;
  session_id?: string | null;
  current_part?: number;
  total_parts?: number;
  previous_content?: Record<string, unknown> | null;
};

export type ProgressEvent = {
  stage:
    | "planning"
    | "reasoning"
    | "generating"
    | "rules"
    | "reviewing"
    | "revising"
    | "done"
    | "error";
  message: string;
  reasoning?: string | null;
  step?: string | null;
  result?: GenerateResponse | null;
};
