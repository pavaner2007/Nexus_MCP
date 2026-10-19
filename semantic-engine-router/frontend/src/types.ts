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
