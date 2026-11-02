import { useState } from 'react';
import { streamContent } from '../services/api';
import { renderMarkdown, parseFlashcards } from '../utils/markdown';
import SourceBadge from '../components/SourceBadge';
import UseNotes from '../components/UseNotes';
import NoteSources from '../components/NoteSources';

const MATERIAL_TYPES = [
  { value: 'notes', label: 'Detailed Notes' },
  { value: 'summary', label: 'Summary' },
  { value: 'flashcards', label: 'Flashcards' },
  { value: 'revision', label: 'Revision Sheet' },
];
const LEVELS = ['beginner', 'intermediate', 'advanced'];

export default function StudyMaterial() {
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [materialType, setMaterialType] = useState('notes');
  const [level, setLevel] = useState('intermediate');
  const [useNotes, setUseNotes] = useState(false);
  const [noteSources, setNoteSources] = useState([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState('');
  const [source, setSource] = useState('');
  const [elapsed, setElapsed] = useState(null);
  const [flipped, setFlipped] = useState({});

  async function handleGenerate(e) {
    e.preventDefault();
    if (!subject.trim() || !topic.trim()) return;
    setError('');
    setLoading(true);
    setStreaming(true);
    setContent('');
    setSource('');
    setFlipped({});
    setNoteSources([]);
    const t0 = performance.now();
    let first = true;
    try {
      await streamContent({ subject, topic, material_type: materialType, level, use_notes: useNotes }, {
        onMeta: (m) => setNoteSources(m.note_sources || []),
        onToken: (t) => {
          if (first) {                       // show the page as soon as the first words arrive
            first = false;
            setLoading(false);
            setElapsed(((performance.now() - t0) / 1000).toFixed(1));
          }
          setContent((c) => c + t);
        },
        onDone: (d) => setSource(d.source),
      });
    } catch (err) {
      setError(err.message || 'Failed to generate content. Check your Gemini API key in backend/.env');
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  }

  const cards = materialType === 'flashcards' ? parseFlashcards(content) : [];

  function handleCopy() {
    navigator.clipboard.writeText(content);
  }

  return (
    <div>
      <div className="page-header">
        <h1>Study Material Generator</h1>
        <p>Generate personalized notes, summaries, flashcards, and revision sheets.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card" style={{ marginBottom: 24 }}>
        <form onSubmit={handleGenerate}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Subject</label>
              <input className="form-input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="e.g. Operating Systems" required />
            </div>
            <div className="form-group">
              <label className="form-label">Topic</label>
              <input className="form-input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Deadlocks" required />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Material type</label>
            <div className="select-row">
              {MATERIAL_TYPES.map((mt) => (
                <div
                  key={mt.value}
                  className={`chip${materialType === mt.value ? ' active' : ''}`}
                  onClick={() => setMaterialType(mt.value)}
                >
                  {mt.label}
                </div>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Level</label>
            <div className="select-row">
              {LEVELS.map((l) => (
                <div key={l} className={`chip${level === l ? ' active' : ''}`} onClick={() => setLevel(l)}>
                  {l[0].toUpperCase() + l.slice(1)}
                </div>
              ))}
            </div>
          </div>

          <UseNotes checked={useNotes} onChange={setUseNotes} what="material" />

          <button className="btn btn-primary" type="submit" disabled={loading || streaming}>
            {loading ? 'Starting…' : streaming ? 'Writing…' : 'Generate'}
          </button>
        </form>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="loading-spinner" />
          <p style={{ marginTop: 12, color: 'var(--color-text-muted)' }}>Generating your study material...</p>
        </div>
      )}

      {content && !loading && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div className="section-title" style={{ marginBottom: 0 }}>
              {MATERIAL_TYPES.find((m) => m.value === materialType)?.label} — {topic}
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {streaming && <span className="rag-detail" aria-live="polite">Writing…</span>}
              {source && <SourceBadge source={source} seconds={elapsed} />}
              <button className="btn btn-outline btn-sm" onClick={handleCopy} disabled={streaming}>Copy</button>
            </div>
          </div>
          {materialType === 'flashcards' && cards.length > 0 ? (
            <>
              <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginTop: 0 }}>Tap a card to flip it.</p>
              <div className="flashcard-grid">
                {cards.map((c, i) => (
                  <div key={i} className={`flashcard${flipped[i] ? ' flipped' : ''}`}
                    onClick={() => setFlipped((f) => ({ ...f, [i]: !f[i] }))}>
                    <div className="flashcard-inner">
                      <div className="flashcard-face front"><span className="fc-tag">Q{i + 1}</span>{c.q}</div>
                      <div className="flashcard-face back"><span className="fc-tag">Answer</span>{c.a}</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="markdown-content" dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} />
          )}
          {noteSources.length > 0 && (
            <div style={{ marginTop: 18, paddingTop: 14, borderTop: '1px solid var(--color-border)' }}>
              <NoteSources sources={noteSources} label="Built from your notes" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
