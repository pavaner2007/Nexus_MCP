// frontend/src/components/ScoreBars.tsx
// Confidence bar chart for all 5 categories with MIN_CONFIDENCE threshold marker.

import type { Scores, Thresholds, Route } from '../types';

const CATEGORIES: Array<keyof Scores> = ['shopping', 'scholar', 'local', 'patents', 'search'];

const CATEGORY_COLOR: Record<keyof Scores, string> = {
  shopping: 'bg-rose-500',
  scholar:  'bg-violet-500',
  local:    'bg-emerald-500',
  patents:  'bg-amber-500',
  search:   'bg-brand-500',
};

const CATEGORY_LABEL: Record<keyof Scores, string> = {
  shopping: 'Shopping',
  scholar:  'Scholar',
  local:    'Local',
  patents:  'Patents',
  search:   'Search',
};

interface Props {
  scores:     Scores;
  thresholds: Thresholds;
  route:      Route;
}

export function ScoreBars({ scores, thresholds, route }: Props) {
  const minPct = thresholds.min_confidence * 100;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400">
          Confidence Scores
        </h3>
        <span className="text-xs text-slate-500">
          min threshold:{' '}
          <span className="text-amber-400 font-mono">{thresholds.min_confidence.toFixed(2)}</span>
          {' | '}dual gap:{' '}
          <span className="text-violet-400 font-mono">{thresholds.dual_route_gap.toFixed(2)}</span>
        </span>
      </div>

      {CATEGORIES.map((cat) => {
        const score = scores[cat];
        const pct   = Math.max(0, Math.min(100, score * 100));
        const isActive = route.categories.includes(cat);

        return (
          <div key={cat} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className={`font-medium ${isActive ? 'text-white' : 'text-slate-400'}`}>
                {CATEGORY_LABEL[cat]}
                {isActive && (
                  <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-brand-600/30 text-brand-400 rounded border border-brand-500/30">
                    ACTIVE
                  </span>
                )}
              </span>
              <span className={`font-mono tabular-nums ${score >= thresholds.min_confidence ? 'text-white' : 'text-slate-500'}`}>
                {score.toFixed(4)}
              </span>
            </div>

            {/* Bar track with threshold marker */}
            <div className="relative h-2.5 bg-surface-600 rounded-full overflow-visible">
              {/* Score fill */}
              <div
                id={`bar-${cat}`}
                className={`h-full rounded-full transition-all duration-700 ease-out ${
                  isActive ? CATEGORY_COLOR[cat] : 'bg-slate-600'
                }`}
                style={{ width: `${pct}%` }}
              />

              {/* MIN_CONFIDENCE threshold marker — absolute vertical line */}
              <div
                id="threshold-marker"
                className="absolute top-[-3px] bottom-[-3px] w-[2px] bg-amber-400/80 rounded-full z-10"
                style={{ left: `${minPct}%` }}
                title={`Min confidence: ${thresholds.min_confidence}`}
              >
                {/* Small label on first bar only */}
                {cat === 'shopping' && (
                  <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[9px] text-amber-400 whitespace-nowrap font-mono">
                    min
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
