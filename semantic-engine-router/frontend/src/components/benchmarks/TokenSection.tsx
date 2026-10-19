// frontend/src/components/benchmarks/TokenSection.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { ChevronDown, ChevronRight, Layers } from 'lucide-react';
import { fetchTokenBenchmark, fetchToolSchemas } from '../../api';

function GeneratedAt({ ts }: { ts: string }) {
  return (
    <p className="text-[10px] text-slate-600 mt-1">
      Generated: {new Date(ts).toLocaleString()}
    </p>
  );
}

export function TokenSection() {
  const [schemasOpen, setSchemasOpen] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['benchmark-tokens'],
    queryFn: () => fetchTokenBenchmark(),
    staleTime: Infinity,
  });

  const { data: schemas } = useQuery({
    queryKey: ['tool-schemas'],
    queryFn: fetchToolSchemas,
    staleTime: Infinity,
    enabled: schemasOpen,
  });

  if (isLoading) return <SectionSkeleton />;
  if (isError || !data) return <SectionError />;

  const chartData = [
    { name: '20 Engines', tokens: data.tokens_20_tools, fill: '#ef4444' },
    { name: 'Universal_Search', tokens: data.tokens_1_tool, fill: '#22c55e' },
  ];

  return (
    <div className="space-y-6">
      {/* Headline stat */}
      <div className="flex flex-col sm:flex-row gap-6">
        <div className="flex-1 bg-surface-700 rounded-xl p-5 border border-surface-600 text-center">
          <div className="text-5xl font-bold text-emerald-400 tabular-nums">
            {data.percent_reduction.toFixed(1)}%
          </div>
          <p className="text-slate-400 text-sm mt-1">Token reduction</p>
          <p className="text-xs text-slate-600 mt-1">cl100k_base (GPT-4 / Claude)</p>
        </div>
        <div className="flex-1 grid grid-cols-2 gap-3">
          {[
            { label: '20 engine schemas', value: data.tokens_20_tools.toLocaleString(), color: 'text-red-400' },
            { label: 'Universal_Search',   value: data.tokens_1_tool.toLocaleString(),   color: 'text-emerald-400' },
            { label: 'Tokens saved',       value: data.tokens_saved.toLocaleString(),    color: 'text-brand-400' },
            { label: 'Tool schemas',       value: String(data.tool_count_20),            color: 'text-slate-300' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-surface-700 rounded-lg p-3 border border-surface-600">
              <p className={`text-lg font-bold font-mono tabular-nums ${color}`}>{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Bar chart */}
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 40 }}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} width={120} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
              formatter={(v: unknown) => [`${(v as number).toLocaleString()} tokens`]}
            />
            <Bar dataKey="tokens" radius={[0, 4, 4, 0]} barSize={28}>
              {chartData.map((entry) => <Cell key={entry.name} fill={entry.fill} fillOpacity={0.85} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-slate-500 italic">
        Counts use cl100k_base tokenizer. Schemas are representative mock definitions.
      </p>

      {/* Expandable schema list */}
      <div className="border border-surface-600 rounded-xl overflow-hidden">
        <button
          id="token-schemas-toggle"
          onClick={() => setSchemasOpen((o) => !o)}
          className="w-full flex items-center gap-2 px-4 py-3 bg-surface-700 hover:bg-surface-600 text-slate-400 hover:text-white text-xs font-medium transition-colors"
        >
          {schemasOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <Layers className="w-3.5 h-3.5" />
          Show what was counted
        </button>
        {schemasOpen && schemas && (
          <div className="p-4 bg-surface-800 space-y-3 max-h-80 overflow-y-auto">
            <p className="text-xs text-slate-500 mb-2">
              <span className="text-red-400 font-semibold">20 engine schemas</span> vs{' '}
              <span className="text-emerald-400 font-semibold">1 Universal_Search schema</span>
            </p>
            {schemas.twenty_schemas.map((s) => (
              <div key={s.name} className="flex items-start gap-2">
                <span className="text-[10px] font-mono text-red-400/70 shrink-0 mt-0.5">tool</span>
                <div>
                  <p className="text-xs font-mono text-slate-300">{s.name}</p>
                  <p className="text-[10px] text-slate-500 line-clamp-1">{s.description}</p>
                </div>
              </div>
            ))}
            <div className="border-t border-surface-600 pt-3 flex items-start gap-2">
              <span className="text-[10px] font-mono text-emerald-400/70 shrink-0 mt-0.5">unified</span>
              <div>
                <p className="text-xs font-mono text-emerald-300">{schemas.universal_schema.name}</p>
                <p className="text-[10px] text-slate-500">{schemas.universal_schema.description}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <GeneratedAt ts={data.generated_at} />
    </div>
  );
}

function SectionSkeleton() {
  return (
    <div className="space-y-4 animate-pulse-slow">
      <div className="h-24 bg-surface-700 rounded-xl" />
      <div className="h-40 bg-surface-700 rounded-xl" />
    </div>
  );
}

function SectionError() {
  return (
    <p className="text-red-400 text-sm p-4 border border-red-500/30 rounded-xl bg-red-500/10">
      Failed to load token benchmark data.
    </p>
  );
}
