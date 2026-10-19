import axios from 'axios';
import type { DemoResult, ExampleQuery, TokenBenchmark, AccuracyBenchmark, LatencyBenchmark, ToolSchemasResult } from './types';

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const client = axios.create({ baseURL: BASE, timeout: 60_000 });

export async function searchDemo(query: string): Promise<DemoResult> {
  const { data } = await client.post<DemoResult>('/demo/search', { query });
  return data;
}

export async function fetchExamples(): Promise<ExampleQuery[]> {
  const { data } = await client.get<ExampleQuery[]>('/demo/examples');
  return data;
}

// ── Phase 14: Benchmark API ──────────────────────────────────────────────

export async function fetchTokenBenchmark(refresh = false): Promise<TokenBenchmark> {
  const { data } = await client.get<TokenBenchmark>('/demo/benchmarks/tokens', { params: { refresh } });
  return data;
}

export async function fetchAccuracyBenchmark(refresh = false): Promise<AccuracyBenchmark> {
  const { data } = await client.get<AccuracyBenchmark>('/demo/benchmarks/accuracy', { params: { refresh } });
  return data;
}

export async function fetchLatencyBenchmark(refresh = false): Promise<LatencyBenchmark> {
  const { data } = await client.get<LatencyBenchmark>('/demo/benchmarks/latency', { params: { refresh } });
  return data;
}

export async function fetchToolSchemas(): Promise<ToolSchemasResult> {
  const { data } = await client.get<ToolSchemasResult>('/demo/benchmarks/tool-schemas');
  return data;
}
