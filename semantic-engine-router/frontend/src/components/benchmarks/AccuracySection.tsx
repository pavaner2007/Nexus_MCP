// frontend/src/components/benchmarks/AccuracySection.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts';
import { ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import { fetchAccuracyBenchmark } from '../../api';
import type { MissEntry } from '../../types';

const CAT_COLOR: Record<string, string> = {
  shopping: '#f87171',
  scholar:  '#a78bfa',
  local:    '#34d399',
  patents:  '#fbbf24',
  search:   '#38bdf8',
};

function GeneratedAt({ ts }: { ts: string }) {
  return <p className="text-[10px] text-slate-600 mt-1">Generated: {new Date(ts).toLocaleString()}</p>;
}

function MissCard({ miss }: { miss: MissEntry }) {
  return (
    <div className="text-xs border border-surface-600 rounded-lg p-3 space-y-1 bg-surface-700">
      <p className="text-white font-medium line-clamp-2">"{miss.query}"</p>
      <div className="flex gap-4 text-slate-500">
        <span>
          Expected:{' '}
          <span className="text-emerald-400">{miss.expected_mode}
            {miss.expected_category ? ` / ${miss.expected_category}` : ''}
          </span>
        </span>
        <span>
          Got:{' '}
          <span className="text-red-400">{miss.actual_mode}
            {miss.actual_category ? ` / ${miss.actual_category}` : ''}
          </span>
        </span>
      </div>
    </div>
  );
}

export function AccuracySection() {
  const [missesOpen, setMissesOpen] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['benchmark-accuracy'],
    queryFn: () => fetchAccuracyBenchmark(),
    staleTime: Infinity,
  });

  if (isLoading) return <SectionSkeleton />;
  if (isError || !data) return <SectionError />;

  const chartData = Object.entries(data.per_category).map(([cat, v]) => ({
    name: cat.charAt(0).toUpperCase() + cat.slice(1),
    cat,
    accuracy: Math.round(v.accuracy),
    correct: v.correct,
    total: v.total,
  }));

  return (
    <div className="space-y-6">
      {/* Headline */}
      <div className="flex flex-col sm:flex-row gap-6">
        <div className="flex-1 bg-surface-700 rounded-xl p-5 border border-surface-600 text-center">
          <div className="text-5xl font-bold text-brand-400 tabular-nums">
            {data.overall_accuracy.toFixed(1)}%
          </div>
          <p className="text-slate-400 text-sm mt-1">Overall accuracy</p>
          <p className="text-xs text-slate-600 mt-1">
            {data.total_correct} / {data.total} queries correct
          </p>
        </div>
        <div className="flex-1 grid grid-cols-2 gap-3">
          {[
            { label: 'Eval set size', value: String(data.total) },
            { label: 'Correct',       value: String(data.total_correct), color: 'text-emerald-400' },
            { label: 'Misses',        value: String(data.misses.length),  color: 'text-red-400' },
            { label: 'Min confidence', value: String((data.meta as Record<string,unknown>)['MIN_CONFIDENCE_THRESHOLD'] ?? '0.20') },
          ].map(({ label, value, color = 'text-slate-200' }) => (
            <div key={label} className="bg-surface-700 rounded-lg p-3 border border-surface-600">
              <p className={`text-lg font-bold font-mono ${color}`}>{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Per-category bar chart */}
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, bottom: 4 }}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} unit="%" />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
              formatter={(v: unknown, _: unknown, props: { payload?: { correct: number; total: number } }) =>
                [`${v as number}% (${props.payload?.correct}/${props.payload?.total})`, 'Accuracy']
              }
            />
            <ReferenceLine y={80} stroke="#fbbf24" strokeDasharray="4 4" strokeWidth={1} />
            <Bar dataKey="accuracy" radius={[4, 4, 0, 0]} barSize={40} fill="#38bdf8">
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={CAT_COLOR[entry.cat] ?? '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Misses collapsible */}
      {data.misses.length > 0 && (
        <div className="border border-surface-600 rounded-xl overflow-hidden">
          <button
            id="accuracy-misses-toggle"
            onClick={() => setMissesOpen((o) => !o)}
            className="w-full flex items-center gap-2 px-4 py-3 bg-surface-700 hover:bg-surface-600 text-slate-400 hover:text-white text-xs font-medium transition-colors"
          >
            {missesOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            {data.misses.length} Misclassifications
          </button>
          {missesOpen && (
            <div className="p-4 bg-surface-800 space-y-2 max-h-80 overflow-y-auto">
              {data.misses.map((m, i) => <MissCard key={i} miss={m} />)}
            </div>
          )}
        </div>
      )}

      <GeneratedAt ts={data.generated_at} />
    </div>
  );
}

function SectionSkeleton() {
  return (
    <div className="space-y-4 animate-pulse-slow">
      <div className="h-24 bg-surface-700 rounded-xl" />
      <div className="h-52 bg-surface-700 rounded-xl" />
    </div>
  );
}

function SectionError() {
  return (
    <p className="text-red-400 text-sm p-4 border border-red-500/30 rounded-xl bg-red-500/10">
      Failed to load accuracy benchmark data.
    </p>
  );
}
