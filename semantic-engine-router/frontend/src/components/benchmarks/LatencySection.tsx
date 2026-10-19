// frontend/src/components/benchmarks/LatencySection.tsx
import { useQuery } from '@tanstack/react-query';
import { Terminal, Zap } from 'lucide-react';
import { fetchLatencyBenchmark } from '../../api';
import type { LatencyStats } from '../../types';

function GeneratedAt({ ts }: { ts: string }) {
  return <p className="text-[10px] text-slate-600 mt-1">Generated: {new Date(ts).toLocaleString()}</p>;
}

function StatCell({ value }: { value: number | undefined }) {
  if (value === undefined) return <td className="px-4 py-3 text-slate-600 text-xs text-center">—</td>;
  return (
    <td className="px-4 py-3 text-center font-mono tabular-nums text-slate-200 text-sm">
      {value.toFixed(1)}
    </td>
  );
}

function LatencyRow({ label, stats, highlight }: { label: string; stats: LatencyStats | undefined; highlight?: boolean }) {
  return (
    <tr className={`border-t border-surface-600 ${highlight ? 'bg-brand-500/5' : ''}`}>
      <td className={`px-4 py-3 text-xs font-medium ${highlight ? 'text-brand-400' : 'text-slate-300'}`}>
        {label}
        {highlight && <span className="ml-2 text-[10px] text-brand-500/70">(local only)</span>}
      </td>
      <StatCell value={stats?.min} />
      <StatCell value={stats?.mean} />
      <StatCell value={stats?.median} />
      <StatCell value={stats?.max} />
    </tr>
  );
}

export function LatencySection() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['benchmark-latency'],
    queryFn: () => fetchLatencyBenchmark(),
    staleTime: Infinity,
  });

  if (isLoading) return <SectionSkeleton />;
  if (isError) return <SectionError />;
  if (!data) return null;

  // Empty state: benchmark not run yet
  if (!data.available) {
    return (
      <div className="space-y-4">
        <div className="p-6 border border-surface-600 rounded-xl bg-surface-700/50 text-center space-y-3">
          <Terminal className="w-10 h-10 text-slate-600 mx-auto" />
          <p className="text-slate-400 text-sm font-medium">Latency benchmark not run yet</p>
          <p className="text-slate-500 text-xs max-w-md mx-auto">
            {data.message ?? 'Run the latency benchmark to populate this section.'}
          </p>
          <div className="mt-4 p-3 bg-surface-800 rounded-lg border border-surface-600 text-left">
            <p className="text-[10px] text-slate-500 mb-1 uppercase tracking-widest">Command</p>
            <code className="text-xs font-mono text-brand-400">
              python -m app.testing.benchmark_latency
            </code>
          </div>
          <p className="text-[10px] text-slate-600">
            Warning: This makes real SerpApi calls and consumes API quota.
          </p>
        </div>
      </div>
    );
  }

  const co = data.classification_overhead_ms;

  return (
    <div className="space-y-6">
      {/* Classification overhead highlight */}
      {co && (
        <div className="flex items-start gap-4 p-4 bg-brand-500/10 border border-brand-500/30 rounded-xl">
          <Zap className="w-5 h-5 text-brand-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-white">
              Classification overhead:{' '}
              <span className="text-brand-400 font-mono">{co.mean.toFixed(1)} ms</span>{' '}
              <span className="text-slate-400 font-normal text-xs">mean (20 queries)</span>
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Uses local sentence embeddings — no LLM call, no network round-trip.
              This is the pure routing cost added by this project.
            </p>
          </div>
        </div>
      )}

      {/* Latency table */}
      <div className="overflow-x-auto rounded-xl border border-surface-600">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface-700">
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-slate-400">Mode</th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-widest text-slate-400">Min</th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-widest text-slate-400">Mean</th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-widest text-slate-400">Median</th>
              <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-widest text-slate-400">Max</th>
            </tr>
            <tr className="bg-surface-700 border-t border-surface-600">
              <td colSpan={5} className="px-4 pb-2 text-[10px] text-slate-600 italic">All values in milliseconds (ms)</td>
            </tr>
          </thead>
          <tbody className="bg-surface-800">
            <LatencyRow label="Classification only" stats={co} highlight />
            <LatencyRow label="Single engine (e2e)" stats={data.single} />
            <LatencyRow label="Dual engine (e2e)"   stats={data.dual} />
            <LatencyRow label="Fallback (e2e)"       stats={data.fallback} />
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500 italic">
        End-to-end times include live SerpApi network latency.
        Iterations: {String((data.meta as Record<string, unknown>)?.['iterations'] ?? '—')}
      </p>

      {data.generated_at && <GeneratedAt ts={data.generated_at} />}
    </div>
  );
}

function SectionSkeleton() {
  return (
    <div className="space-y-4 animate-pulse-slow">
      <div className="h-20 bg-surface-700 rounded-xl" />
      <div className="h-48 bg-surface-700 rounded-xl" />
    </div>
  );
}

function SectionError() {
  return (
    <p className="text-red-400 text-sm p-4 border border-red-500/30 rounded-xl bg-red-500/10">
      Failed to load latency benchmark data.
    </p>
  );
}
