export type ModuleName = "reading" | "writing" | "listening";

export type WritingType =
  | "opinion"
  | "discussion"
  | "problem_solution"
  | "advantages_disadvantages"
  | "two_part";

export type Task1Kind =
  | "line_graph"
  | "bar_chart"
  | "pie_chart"
  | "table"
  | "process"
  | "map"
  | "mixed"
  | "letter_formal"
  | "letter_semi_formal"
  | "letter_informal";

export type ReviewFinding = {
  severity: "must" | "should" | "info";
  message: string;
  code?: string | null;
};

export type QualityMode = "draft" | "standard" | "publish";

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
  quality_mode?: QualityMode;
  topics?: string[] | null;
  type_plan?: string[][] | null;
  topic_t1?: string | null;
  topic_t2?: string | null;
  task1_kind?: string | null;
  task2_kind?: string | null;
  cost?: {
    llm_calls: number;
    planner_calls: number;
    generator_calls: number;
    critic_calls: number;
    quality_mode: QualityMode;
    prompt_hash?: string | null;
  };
};

export type GenerateRequest = {
  module: ModuleName;
  topic: string;
  target_band: number;
  question_count: number;
  part_count: number;
  writing_type?: WritingType;
  full_paper?: boolean;
  quality_mode?: QualityMode;
  session_id?: string | null;
  current_part?: number;
  total_parts?: number;
  previous_content?: Record<string, unknown> | null;
  topics?: string[];
  type_plan?: string[][];
  topic_t1?: string;
  topic_t2?: string;
  task1_kind?: Task1Kind;
  task2_kind?: WritingType;
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
