import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listDocs } from '../services/api';

/** "Build this from my notes" checkbox for the quiz and study-material forms. */
export default function UseNotes({ checked, onChange, what = 'questions' }) {
  const [count, setCount] = useState(null);
  useEffect(() => { listDocs().then((d) => setCount(d.length)).catch(() => setCount(0)); }, []);
  if (count === null) return null;
  if (count === 0) {
    return (
      <div className="use-notes empty">
        Want {what} from your own notes? <Link to="/notes">Upload them first</Link>.
      </div>
    );
  }
  return (
    <label className={`use-notes${checked ? ' on' : ''}`}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>
        <strong>Use my notes</strong> ({count} document{count > 1 ? 's' : ''})
        <small>{checked ? `The ${what} will come only from your notes, with the source of each.` : `Otherwise the ${what} come from general knowledge.`}</small>
      </span>
    </label>
  );
}
