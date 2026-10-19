// frontend/src/components/ResultCard.tsx
// Renders one EngineResult with engine-specific metadata fields.

import { ExternalLink } from 'lucide-react';
import type { EngineResult } from '../types';

const ENGINE_BADGE: Record<string, string> = {
  shopping: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  scholar:  'bg-violet-500/20 text-violet-400 border-violet-500/30',
  local:    'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  patents:  'bg-amber-500/20 text-amber-400 border-amber-500/30',
  search:   'bg-brand-500/20 text-brand-400 border-brand-500/30',
};

interface Props {
  result:        EngineResult;
  engine:        string;       // e.g. "shopping", "dual:local+shopping"
  showEngineBadge?: boolean;
}

function SourceBadge({ engine }: { engine: string }) {
  const base = engine.replace(/^dual:/, '').split('+')[0];
  const cls  = ENGINE_BADGE[base] ?? 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  return (
    <span className={`inline-block px-1.5 py-0.5 text-[10px] font-mono border rounded uppercase tracking-wide ${cls}`}>
      {base}
    </span>
  );
}

function MetaRow({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined || value === '') return null;
  const display = Array.isArray(value) ? (value as string[]).slice(0, 3).join(', ') : String(value);
  return (
    <div className="flex gap-2 text-xs">
      <span className="text-slate-500 shrink-0">{label}:</span>
      <span className="text-slate-300 truncate">{display}</span>
    </div>
  );
}

export function ResultCard({ result, engine, showEngineBadge }: Props) {
  const m = result.metadata ?? {};
  const isDual = engine.startsWith('dual:');

  // Determine source engine for dual-mode badge
  const sourceEngine = (m['source_engine'] as string) ?? engine;

  return (
    <div className="bg-surface-700 border border-surface-600 rounded-xl p-4 space-y-2 hover:border-surface-500 transition-colors duration-150 animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {(showEngineBadge || isDual) && <SourceBadge engine={sourceEngine} />}
            {result.thumbnail && (
              <img
                src={result.thumbnail}
                alt=""
                className="w-8 h-8 rounded object-cover bg-surface-600"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
            )}
          </div>
          <h4 className="text-sm font-semibold text-white leading-snug line-clamp-2">
            {result.title}
          </h4>
        </div>
        {result.link && (
          <a
            href={result.link}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 text-slate-500 hover:text-brand-400 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>

      {result.snippet && (
        <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">{result.snippet}</p>
      )}

      {/* Engine-specific metadata */}
      <div className="space-y-0.5 pt-1 border-t border-surface-600">
        {/* Shopping */}
        <MetaRow label="Price"   value={m['price']} />
        <MetaRow label="Source"  value={m['source']} />
        <MetaRow label="Rating"  value={m['rating'] != null ? `${m['rating']} ⭐` : null} />
        {/* Scholar */}
        <MetaRow label="Authors" value={m['authors']} />
        <MetaRow label="Year"    value={m['year']} />
        <MetaRow label="Cited"   value={m['cited_by_count'] != null ? `${m['cited_by_count']} citations` : null} />
        {/* Local */}
        <MetaRow label="Address" value={m['address']} />
        <MetaRow label="Hours"   value={m['hours']} />
        {/* Patents */}
        <MetaRow label="Inventor"  value={m['inventor']} />
        <MetaRow label="Assignee"  value={m['assignee']} />
        <MetaRow label="Filed"     value={m['filing_date']} />
        <MetaRow label="Status"    value={m['status']} />
      </div>
    </div>
  );
}
