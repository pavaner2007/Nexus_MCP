// frontend/src/components/TimingsStrip.tsx
import type { Timings } from '../types';
import { Zap, Globe, Clock } from 'lucide-react';

interface Props {
  timings: Timings;
}

export function TimingsStrip({ timings }: Props) {
  const items = [
    { label: 'Classification', value: timings.classification, icon: Zap,   color: 'text-brand-400',   bg: 'bg-brand-500/10'   },
    { label: 'Engine calls',   value: timings.engine_calls,   icon: Globe,  color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { label: 'Total',          value: timings.total,          icon: Clock,  color: 'text-violet-400',  bg: 'bg-violet-500/10'  },
  ];

  return (
    <div className="flex gap-3 flex-wrap">
      {items.map(({ label, value, icon: Icon, color, bg }) => (
        <div
          key={label}
          id={`timing-${label.toLowerCase().replace(' ', '-')}`}
          className={`flex items-center gap-2 px-4 py-2 ${bg} rounded-lg border border-surface-600`}
        >
          <Icon className={`w-3.5 h-3.5 ${color}`} />
          <span className="text-xs text-slate-400">{label}</span>
          <span className={`text-xs font-mono font-semibold ${color}`}>
            {value.toFixed(1)} ms
          </span>
        </div>
      ))}
    </div>
  );
}
