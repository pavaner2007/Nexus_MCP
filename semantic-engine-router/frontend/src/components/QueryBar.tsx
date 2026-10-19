// frontend/src/components/QueryBar.tsx
import { useState, type FormEvent } from 'react';
import { Search, Loader2 } from 'lucide-react';
import type { ExampleQuery } from '../types';

interface Props {
  onSubmit: (query: string) => void;
  examples: ExampleQuery[];
  isLoading: boolean;
}

export function QueryBar({ onSubmit, examples, isLoading }: Props) {
  const [value, setValue] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    if (q) onSubmit(q);
  };

  const handleChip = (q: string) => {
    setValue(q);
    onSubmit(q);
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 pointer-events-none" />
          <input
            id="query-input"
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Ask anything — the router picks the right engine…"
            className="w-full pl-12 pr-4 py-3.5 bg-surface-700 border border-surface-600
                       text-white placeholder-slate-500 rounded-xl text-sm
                       focus:outline-none focus:ring-2 focus:ring-brand-500/60
                       transition-all duration-200"
          />
        </div>
        <button
          id="query-submit"
          type="submit"
          disabled={isLoading || !value.trim()}
          className="px-6 py-3.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-40
                     text-white font-semibold rounded-xl transition-all duration-200
                     flex items-center gap-2 text-sm whitespace-nowrap"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          Search
        </button>
      </form>

      {/* Example chips */}
      {examples.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {examples.map((ex) => (
            <button
              key={ex.label}
              id={`chip-${ex.label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
              onClick={() => handleChip(ex.query)}
              className="px-3 py-1.5 bg-surface-700 hover:bg-surface-600 border border-surface-600
                         hover:border-brand-500/50 text-slate-300 hover:text-white rounded-lg
                         text-xs font-medium transition-all duration-150"
            >
              <span className="text-brand-400 mr-1">→</span>
              {ex.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
