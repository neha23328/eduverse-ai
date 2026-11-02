import { useState } from 'react';
import Icon from './Icon';

/**
 * The passages of the student's notes that an answer / quiz / study sheet was built from.
 * Click a chip to read the exact passage. `cited` (optional) lists the [n] the answer really used;
 * the others are shown as "retrieved but not used" so nothing looks more grounded than it is.
 */
export default function NoteSources({ sources = [], cited = null, label = 'From your notes' }) {
  const [open, setOpen] = useState(null);
  if (!sources.length) return null;
  const isUsed = (n) => (cited ? cited.includes(n) : true);
  const active = sources.find((s) => s.n === open);
  return (
    <div className="note-sources">
      <div className="sources-row">
        <span className="sources-label"><Icon name="folder" size={13} /> {label}:</span>
        {sources.map((s) => (
          <button
            key={s.n}
            type="button"
            className={`source-chip${isUsed(s.n) ? ' used' : ''}${open === s.n ? ' open' : ''}`}
            aria-expanded={open === s.n}
            onClick={() => setOpen(open === s.n ? null : s.n)}
            title={isUsed(s.n) ? 'Click to read this passage' : 'Found in your notes, but the answer did not use it'}
          >
            [{s.n}] {s.title} · p.{s.page}
          </button>
        ))}
      </div>
      {active && (
        <blockquote className="source-passage">
          {active.snippet}{active.snippet.length >= 400 ? '…' : ''}
          <footer>
            {active.title}, page {active.page}
            {cited && !cited.includes(active.n) ? ' · retrieved, not used in the answer' : ''}
          </footer>
        </blockquote>
      )}
    </div>
  );
}
