// frontend/src/api.ts
// Axios client + typed API helpers.

import axios from 'axios';
import type { DemoResult, ExampleQuery } from './types';

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
