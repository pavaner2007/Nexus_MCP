// frontend/src/components/RouteBadge.tsx
import type { RouteMode } from '../types';

const CONFIG: Record<RouteMode, { label: string; classes: string; explanation: string }> = {
  single: {
    label: 'SINGLE',
    classes: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    explanation: 'One engine scored well above the confidence threshold with a clear lead. Routing to a single specialist engine.',
  },
  dual: {
    label: 'DUAL',
    classes: 'bg-violet-500/15 text-violet-400 border-violet-500/30',
    explanation: 'Two engines scored closely together (gap ≤ dual threshold). Running both concurrently and merging results.',
  },
  fallback: {
    label: 'FALLBACK',
    classes: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    explanation: 'No engine scored above the minimum confidence threshold. Falling back to base Google Search.',
  },
};

interface Props {
  mode: RouteMode;
  categories: string[];
}

export function RouteBadge({ mode, categories }: Props) {
  const cfg = CONFIG[mode];
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <span
          id="route-badge"
          className={`inline-flex items-center px-3 py-1 rounded-lg border text-xs font-bold tracking-widest ${cfg.classes}`}
        >
          {cfg.label}
        </span>
        <span className="text-slate-400 text-xs">
          {categories.map((c) => (
            <span
              key={c}
              className="inline-block px-2 py-0.5 bg-surface-600 rounded text-brand-400 font-mono mr-1"
            >
              {c}
            </span>
          ))}
        </span>
      </div>
      <p className="text-slate-400 text-xs leading-relaxed">{cfg.explanation}</p>
    </div>
  );
}
