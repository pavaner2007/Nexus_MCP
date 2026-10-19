// frontend/src/App.tsx
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { AlertCircle, Layers, BarChart2 } from 'lucide-react';
import { fetchExamples, searchDemo } from './api';
import { QueryBar }      from './components/QueryBar';
import { ScoreBars }     from './components/ScoreBars';
import { RouteBadge }    from './components/RouteBadge';
import { TimingsStrip }  from './components/TimingsStrip';
import { ResultCard }    from './components/ResultCard';
import { RawJson }       from './components/RawJson';
import { BenchmarksView } from './pages/BenchmarksView';
import type { DemoResult } from './types';

// ── Skeleton loader ─────────────────────────────────────────────────────────
function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`bg-surface-700 rounded-lg animate-pulse-slow ${className}`} />;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="bg-surface-800 border border-surface-600 rounded-2xl p-6 space-y-4">
        <Skeleton className="h-4 w-40" />
        {[...Array(5)].map((_, i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex justify-between">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-2.5 w-full" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-surface-700 border border-surface-600 rounded-xl p-4 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-sm text-red-400 animate-fade-in">
      <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
      <div>
        <p className="font-semibold">Search failed</p>
        <p className="text-xs text-red-400/70 mt-0.5">{message}</p>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-16 space-y-3 animate-fade-in">
      <Layers className="w-12 h-12 text-slate-600 mx-auto" />
      <p className="text-slate-500 text-sm">Enter a query to see the router in action.</p>
      <p className="text-slate-600 text-xs">Try one of the example chips above.</p>
    </div>
  );
}

// ── Tab navigation ───────────────────────────────────────────────────────────
type Tab = 'router' | 'benchmarks';

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  id: string;
}

function TabButton({ active, onClick, icon, label, id }: TabButtonProps) {
  return (
    <button
      id={id}
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
        active
          ? 'bg-brand-600/20 text-brand-400 border border-brand-500/30'
          : 'text-slate-400 hover:text-white hover:bg-surface-700'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

// ── Main app ────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState<Tab>('router');
  const [result, setResult] = useState<DemoResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: examples = [] } = useQuery({
    queryKey: ['examples'],
    queryFn: fetchExamples,
    staleTime: Infinity,
  });

  const mutation = useMutation({
    mutationFn: searchDemo,
    onSuccess: (data) => { setResult(data); setErrorMsg(null); },
    onError:   (err: Error) => { setErrorMsg(err.message); setResult(null); },
  });

  const handleSearch = (query: string) => {
    setTab('router');
    setErrorMsg(null);
    mutation.mutate(query);
  };

  const isDualMode = result?.route.mode === 'dual';

  return (
    <div className="min-h-screen bg-surface-900 text-white">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="border-b border-surface-700 bg-surface-800/60 backdrop-blur sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-violet-600 rounded-lg flex items-center justify-center">
            <Layers className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight">Semantic Engine Router</h1>
            <p className="text-xs text-slate-400">One tool. Every SerpApi engine.</p>
          </div>
          {/* Tab nav */}
          <div className="ml-auto flex items-center gap-2">
            <TabButton
              id="tab-router"
              active={tab === 'router'}
              onClick={() => setTab('router')}
              icon={<Layers className="w-4 h-4" />}
              label="Live Router"
            />
            <TabButton
              id="tab-benchmarks"
              active={tab === 'benchmarks'}
              onClick={() => setTab('benchmarks')}
              icon={<BarChart2 className="w-4 h-4" />}
              label="Benchmarks"
            />
          </div>
        </div>
      </header>

      {/* ── Main content ────────────────────────────────────────── */}
      <main className="max-w-5xl mx-auto px-6 py-10 space-y-8">
        {/* ── Live Router tab ─────────────────────────────────── */}
        {tab === 'router' && (
          <>
            <QueryBar
              onSubmit={handleSearch}
              examples={examples}
              isLoading={mutation.isPending}
            />

            {mutation.isPending && <LoadingSkeleton />}
            {errorMsg && !mutation.isPending && <ErrorState message={errorMsg} />}
            {!mutation.isPending && !errorMsg && !result && <EmptyState />}

            {result && !mutation.isPending && (
              <div className="space-y-6 animate-fade-in">
                {/* Router Decision */}
                <section
                  id="router-decision-panel"
                  className="bg-surface-800 border border-surface-600 rounded-2xl p-6 space-y-6"
                >
                  <div className="flex items-center justify-between flex-wrap gap-4">
                    <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
                      Router Decision
                    </h2>
                    <RouteBadge mode={result.route.mode} categories={result.route.categories} />
                  </div>
                  <ScoreBars
                    scores={result.scores}
                    thresholds={result.thresholds}
                    route={result.route}
                  />
                  <div className="pt-3 border-t border-surface-600">
                    <p className="text-xs text-slate-500 mb-2 uppercase tracking-widest">Timings</p>
                    <TimingsStrip timings={result.timings_ms} />
                  </div>
                </section>

                {/* Results */}
                <section id="results-panel">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
                      Results
                    </h2>
                    <span className="text-xs text-slate-500 font-mono">
                      {result.response.result_count} result{result.response.result_count !== 1 ? 's' : ''} ·{' '}
                      <span className="text-brand-400">{result.response.engine}</span>
                    </span>
                  </div>

                  {result.response.results.length === 0 && (
                    <div className="text-center py-8 text-slate-500 text-sm border border-surface-600 rounded-xl">
                      {result.response.success
                        ? 'No results returned for this query.'
                        : `Engine error: ${result.response.error ?? 'unknown'}`}
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {result.response.results.map((r, i) => (
                      <ResultCard
                        key={`${r.link}-${i}`}
                        result={r}
                        engine={result.response.engine}
                        showEngineBadge={isDualMode}
                      />
                    ))}
                  </div>
                </section>

                <RawJson data={result} />
              </div>
            )}
          </>
        )}

        {/* ── Benchmarks tab ──────────────────────────────────── */}
        {tab === 'benchmarks' && <BenchmarksView />}
      </main>
    </div>
  );
}
