// frontend/src/components/RawJson.tsx
// Collapsible raw JSON inspector for judges.

import { useState } from 'react';
import { ChevronDown, ChevronRight, Code2 } from 'lucide-react';

interface Props {
  data: unknown;
}

export function RawJson({ data }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-surface-600 rounded-xl overflow-hidden">
      <button
        id="raw-json-toggle"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-4 py-3 bg-surface-700 hover:bg-surface-600 text-slate-400 hover:text-white transition-colors text-xs font-medium"
      >
        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        <Code2 className="w-3.5 h-3.5" />
        Raw Response JSON
      </button>
      {open && (
        <pre
          id="raw-json-content"
          className="p-4 bg-surface-800 text-xs text-slate-300 font-mono overflow-auto max-h-96 leading-relaxed"
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
