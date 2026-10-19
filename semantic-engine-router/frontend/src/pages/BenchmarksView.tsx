// frontend/src/pages/BenchmarksView.tsx
// Phase 14 — Benchmarks page with three sections.

import { BarChart2, Coins, Clock } from 'lucide-react';
import { TokenSection }   from '../components/benchmarks/TokenSection';
import { AccuracySection } from '../components/benchmarks/AccuracySection';
import { LatencySection }  from '../components/benchmarks/LatencySection';

interface SectionProps {
  id:       string;
  icon:     React.ReactNode;
  title:    string;
  subtitle: string;
  children: React.ReactNode;
}

function Section({ id, icon, title, subtitle, children }: SectionProps) {
  return (
    <section
      id={id}
      className="bg-surface-800 border border-surface-600 rounded-2xl p-6 space-y-6"
    >
      <div className="flex items-start gap-3 pb-1 border-b border-surface-600">
        <div className="w-8 h-8 rounded-lg bg-surface-700 border border-surface-600 flex items-center justify-center shrink-0">
          {icon}
        </div>
        <div>
          <h2 className="text-sm font-semibold text-white">{title}</h2>
          <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

export function BenchmarksView() {
  return (
    <div className="space-y-6 animate-fade-in">
      <Section
        id="benchmark-tokens"
        icon={<Coins className="w-4 h-4 text-emerald-400" />}
        title="Token Comparison"
        subtitle="1 Universal_Search tool vs 20 individual SerpApi engine schemas — prompt token savings"
      >
        <TokenSection />
      </Section>

      <Section
        id="benchmark-accuracy"
        icon={<BarChart2 className="w-4 h-4 text-brand-400" />}
        title="Routing Accuracy"
        subtitle="53 hand-labeled test cases across single / dual / fallback routing modes"
      >
        <AccuracySection />
      </Section>

      <Section
        id="benchmark-latency"
        icon={<Clock className="w-4 h-4 text-violet-400" />}
        title="Latency"
        subtitle="Classification overhead (local embeddings) vs end-to-end engine latency"
      >
        <LatencySection />
      </Section>
    </div>
  );
}
