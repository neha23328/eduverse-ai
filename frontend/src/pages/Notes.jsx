import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { listDocs, uploadDoc, deleteDoc, searchDocs, getRagStatus, reindexDocs } from '../services/api';

function fmtDate(iso) {
  try { return new Date(iso + 'Z').toLocaleDateString(); } catch (e) { return ''; }
}

export default function Notes() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [subject, setSubject] = useState('');
  const [drag, setDrag] = useState(false);
  const [q, setQ] = useState('');
  const [result, setResult] = useState(null);       // { hits, info }
  const [searching, setSearching] = useState(false);
  const [status, setStatus] = useState(null);       // semantic search status (live probe)
  const [checking, setChecking] = useState(false);
  const fileRef = useRef(null);

  function refresh() {
    return listDocs().then(setDocs).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }

  async function checkStatus() {
    setChecking(true);
    try { setStatus(await getRagStatus(true)); } catch (e) { setStatus(null); } finally { setChecking(false); }
  }

  useEffect(() => { refresh(); checkStatus(); }, []);

  async function handleFiles(files) {
    if (!files || !files.length) return;
    setError('');
    setUploading(true);
    try {
      for (const f of files) await uploadDoc(f, { subject });
      await refresh();
      await checkStatus();
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Remove this document from your knowledge base?')) return;
    setDocs((d) => d.filter((x) => x.id !== id));
    try { await deleteDoc(id); await checkStatus(); } catch (e) { setError(e.message); refresh(); }
  }

  async function handleReindex() {
    setChecking(true);
    setError('');
    try {
      await reindexDocs();
      await refresh();
      await checkStatus();
    } catch (e) { setError(e.message); setChecking(false); }
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!q.trim()) return;
    setSearching(true);
    setError('');
    try { setResult(await searchDocs(q.trim())); } catch (err) { setError(err.message); } finally { setSearching(false); }
  }

  const semanticOk = status && status.probeOk;
  const pending = status ? status.pendingDocuments : 0;

  return (
    <div>
      <div className="page-header">
        <h1>My Notes</h1>
        <p>Add your own notes, slides or textbook chapters. The mentor searches them before answering, quizzes and study sheets can be built from them, and every answer shows which passages it used.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {docs.length > 0 && (
        <div className={`rag-status ${semanticOk ? 'ok' : 'warn'}`}>
          <div>
            <strong>{checking && !status ? 'Checking search…' : semanticOk ? 'Semantic search is working' : 'Keyword search only'}</strong>
            <div className="rag-status-sub">
              {semanticOk
                ? pending > 0
                  ? `${pending} document${pending > 1 ? 's were' : ' was'} added before it was working. Re-index to include ${pending > 1 ? 'them' : 'it'}.`
                  : 'Questions are matched by meaning as well as by words, so "why does the system hang?" can find a passage about deadlock.'
                : status && status.lastError
                  ? `Meaning-based matching is off: ${status.lastError}. Questions are matched by words only.`
                  : 'Meaning-based matching is off. Questions are matched by words only.'}
            </div>
          </div>
          <div className="rag-status-actions">
            {semanticOk && pending > 0 && <button className="btn btn-primary btn-sm" onClick={handleReindex} disabled={checking}>Re-index notes</button>}
            <button className="btn btn-outline btn-sm" onClick={checkStatus} disabled={checking}>{checking ? 'Checking…' : 'Check again'}</button>
          </div>
        </div>
      )}

      <div className="card" style={{ marginBottom: 24 }}>
        <div
          className={`dropzone${drag ? ' drag' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(Array.from(e.dataTransfer.files)); }}
          onClick={() => fileRef.current?.click()}
        >
          <Icon name="file" size={34} strokeWidth={1.4} />
          <div style={{ fontWeight: 600, marginTop: 6 }}>{uploading ? 'Reading your notes…' : 'Drop your notes here, or click to choose files'}</div>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>PDF, text or Markdown, up to 10 MB each. Scanned images can't be read.</div>
          <input ref={fileRef} type="file" accept=".pdf,.txt,.md,.markdown" multiple hidden
            onChange={(e) => handleFiles(Array.from(e.target.files))} />
        </div>
        <div className="form-group" style={{ marginTop: 14, maxWidth: 320 }}>
          <label className="form-label">Subject tag (optional)</label>
          <input className="form-input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="e.g. Operating Systems" />
        </div>
      </div>

      <div className="two-col-grid">
        <div className="card">
          <div className="section-title">Your notes</div>
          {loading ? <div className="loading-spinner" /> : docs.length === 0 ? (
            <div className="empty-state">Nothing here yet. Add your first set of notes above and the mentor can start using it.</div>
          ) : docs.map((d) => (
            <div className="task-row" key={d.id}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.title}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                  {d.chunks} passages · {fmtDate(d.createdAt)}{d.subject ? ` · ${d.subject}` : ''}
                </div>
              </div>
              <span className={`badge ${d.semantic ? 'badge-success' : 'badge-primary'}`} title={d.semantic ? 'Matched by meaning and by words' : 'Matched by words only'}>
                {d.semantic ? 'semantic' : 'keyword'}
              </span>
              <button className="task-delete-btn" aria-label={`Remove ${d.title}`} onClick={() => handleDelete(d.id)}>✕</button>
            </div>
          ))}
          {docs.length > 0 && (
            <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Link className="btn btn-primary btn-sm" to="/mentor">Ask the mentor</Link>
              <Link className="btn btn-outline btn-sm" to="/quiz">Quiz me from my notes</Link>
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-title">Check what the mentor finds</div>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginTop: 0 }}>
            Type a question to see which passages the mentor would read before answering, and why each one matched.
          </p>
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input className="form-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. conditions for deadlock" />
            <button className="btn btn-secondary btn-sm" type="submit" disabled={searching || docs.length === 0}>{searching ? '…' : 'Search'}</button>
          </form>
          {result && (
            <div className="rag-detail" style={{ marginBottom: 10 }}>
              {result.info.mode === 'hybrid' ? 'Semantic + keyword search' : 'Keyword search'} · {result.info.considered} passages checked · {result.hits.length} relevant
            </div>
          )}
          {result && (result.hits.length === 0 ? (
            <div className="empty-state">Your notes don't seem to cover this. The mentor would answer from general knowledge instead.</div>
          ) : result.hits.map((h, i) => (
            <div key={i} className="hit-card">
              <div className="hit-head">
                <strong>{h.title}</strong> · p.{h.page}
                <span className="badge badge-primary" style={{ marginLeft: 8 }}>{Math.round(h.score * 100)}% relevant</span>
                <span className="hit-why">
                  {Math.round(h.coverage * 100)}% of your words found{h.cosine != null ? ` · meaning match ${h.cosine.toFixed(2)}` : ''}
                </span>
              </div>
              <div className="hit-text">{h.text.length > 320 ? h.text.slice(0, 320) + '…' : h.text}</div>
            </div>
          )))}
        </div>
      </div>
    </div>
  );
}
