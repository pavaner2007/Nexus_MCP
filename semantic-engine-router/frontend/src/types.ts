// frontend/src/types.ts
// Shared TypeScript types for the Semantic Engine Router demo UI.

export type RouteMode = 'single' | 'dual' | 'fallback';

export interface EngineResult {
  title:     string;
  snippet:   string | null;
  link:      string;
  thumbnail: string | null;
  metadata:  Record<string, unknown>;
}

export interface EngineResponse {
  success:       boolean;
  engine:        string;
  result_count:  number;
  error:         string | null;
  classified_as: string | null;
  confidence:    number | null;
  route_detail:  Record<string, unknown> | null;
  results:       EngineResult[];
}

export interface Scores {
  shopping: number;
  scholar:  number;
  local:    number;
  patents:  number;
  search:   number;
}

export interface Thresholds {
  min_confidence: number;
  dual_route_gap: number;
}

export interface Route {
  mode:       RouteMode;
  categories: string[];
}

export interface Timings {
  classification: number;
  engine_calls:   number;
  total:          number;
}

export interface DemoResult {
  query:       string;
  scores:      Scores;
  thresholds:  Thresholds;
  route:       Route;
  response:    EngineResponse;
  timings_ms:  Timings;
}

export interface ExampleQuery {
  label: string;
  query: string;
}

// ── Phase 14: Benchmark types ────────────────────────────────────────────

export interface TokenBreakdownEntry {
  name:   string;
  tokens: number;
}

export interface TokenBenchmark {
  tokens_20_tools:   number;
  tokens_1_tool:     number;
  tokens_saved:      number;
  percent_reduction: number;
  tool_count_20:     number;
  breakdown:         TokenBreakdownEntry[];
  generated_at:      string;
}

export interface PerCategoryAccuracy {
  total:    number;
  correct:  number;
  wrong:    number;
  accuracy: number;
}

export interface MissEntry {
  query:             string;
  expected_mode:     string;
  expected_category: string | null;
  actual_mode:       string;
  actual_category:   string | null;
}

export interface AccuracyBenchmark {
  overall_accuracy: number;
  per_category:     Record<string, PerCategoryAccuracy>;
  misses:           MissEntry[];
  total:            number;
  total_correct:    number;
  meta:             Record<string, unknown>;
  generated_at:     string;
}

export interface LatencyStats {
  min:    number;
  mean:   number;
  median: number;
  max:    number;
  count:  number;
}

export interface LatencyBenchmark {
  available:                  boolean;
  message?:                   string;
  classification_overhead_ms?: LatencyStats;
  single?:                    LatencyStats;
  dual?:                      LatencyStats;
  fallback?:                  LatencyStats;
  meta?:                      Record<string, unknown>;
  generated_at?:              string;
}

export interface ToolSchema {
  name:        string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface ToolSchemasResult {
  twenty_schemas:   ToolSchema[];
  universal_schema: ToolSchema;
  count:            number;
}
