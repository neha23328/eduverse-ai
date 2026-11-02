import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { streamChatMessage, getChatHistory, clearChatHistory, listDocs } from '../services/api';
import { renderMarkdown } from '../utils/markdown';
import SourceBadge from '../components/SourceBadge';
import NoteSources from '../components/NoteSources';
import Icon from '../components/Icon';

const SUBJECTS = ['', 'Mathematics', 'Programming', 'Physics', 'Chemistry', 'Data Structures', 'Other'];
const LEVELS = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
];
const SUGGESTIONS = [
  'Explain how a hash table handles collisions',
  'What is overfitting and how do I prevent it?',
  'Explain deadlock and the four necessary conditions',
];

const SpeechRecognition = typeof window !== 'undefined'
  ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

export default function Mentor() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [subject, setSubject] = useState('');
  const [level, setLevel] = useState('intermediate');
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState('');
  const [listening, setListening] = useState(false);
  const [speakingId, setSpeakingId] = useState(null);
  const [notesMode, setNotesMode] = useState(() => {
    try { return localStorage.getItem('ev_notes_mode') || 'auto'; } catch (e) { return 'auto'; }
  });
  const [docs, setDocs] = useState([]);
  const messagesEndRef = useRef(null);
  const recogRef = useRef(null);

  useEffect(() => {
    getChatHistory()
      .then((history) => setMessages(history))
      .catch((err) => setError(err.message))
      .finally(() => setLoadingHistory(false));
    listDocs().then(setDocs).catch(() => {});
    return () => { window.speechSynthesis?.cancel(); recogRef.current?.stop(); };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  async function send(text) {
    text = text.trim();
    if (!text || sending) return;
    setError('');
    const userMsg = { id: `u-${Date.now()}`, role: 'user', content: text, subject };
    const botId = `a-${Date.now()}`;
    // Placeholder assistant bubble that fills in token by token.
    setMessages((prev) => [...prev, userMsg, { id: botId, role: 'assistant', content: '', subject, streaming: true }]);
    setInput('');
    setSending(true);

    const patch = (fn) => setMessages((prev) => prev.map((m) => (m.id === botId ? fn(m) : m)));
    try {
      await streamChatMessage({ message: text, subject, level, notes_mode: notesMode }, {
        onSources: (src, meta) => patch((m) => ({ ...m, sources: src, rag: meta.rag, grounded: meta.grounded })),
        onToken: (t) => patch((m) => ({ ...m, content: m.content + t })),
        onFirstToken: (s) => patch((m) => ({ ...m, firstToken: s })),
        onDone: (d) => patch((m) => ({ ...m, streaming: false, source: d.source, totalSeconds: d.total_s, cited: d.cited })),
      });
    } catch (err) {
      setError(err.message || 'Failed to get a response. Check your Gemini API key in backend/.env');
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id && m.id !== botId));
      setInput(text);
    } finally {
      setSending(false);
    }
  }

  function chooseMode(mode) {
    setNotesMode(mode);
    try { localStorage.setItem('ev_notes_mode', mode); } catch (e) { /* storage unavailable */ }
  }

  function handleSubmit(e) { e.preventDefault(); send(input); }

  async function handleClear() {
    if (!window.confirm('Clear all chat history?')) return;
    try { await clearChatHistory(); setMessages([]); } catch (err) { setError(err.message); }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); }
  }

  function toggleMic() {
    if (!SpeechRecognition) return;
    if (listening) { recogRef.current?.stop(); return; }
    const r = new SpeechRecognition();
    r.lang = 'en-IN';
    r.interimResults = true;
    r.onresult = (e) => setInput(Array.from(e.results).map((x) => x[0].transcript).join(''));
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    recogRef.current = r;
    setListening(true);
    r.start();
  }

  function toggleSpeak(m) {
    const synth = window.speechSynthesis;
    if (!synth) return;
    if (speakingId === m.id) { synth.cancel(); setSpeakingId(null); return; }
    synth.cancel();
    const u = new SpeechSynthesisUtterance(m.content.replace(/[#*`>_]/g, ''));
    u.onend = () => setSpeakingId(null);
    setSpeakingId(m.id);
    synth.speak(u);
  }

  return (
    <div>
      <div className="page-header">
        <h1>AI Mentor</h1>
        <p>Ask a question and get an explanation that fits your level and your course.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {notesMode !== 'off' && docs.length === 0 && (
        <div className="info-banner">You haven't uploaded any notes yet. <Link to="/notes">Upload a PDF or text file</Link> and the mentor will search it before answering.</div>
      )}

      <div className="chat-container">
        <div className="chat-toolbar">
          <select className="form-select" style={{ width: 180 }} value={subject} onChange={(e) => setSubject(e.target.value)}>
            {SUBJECTS.map((s) => <option key={s} value={s}>{s || 'General'}</option>)}
          </select>
          <select className="form-select" style={{ width: 160 }} value={level} onChange={(e) => setLevel(e.target.value)}>
            {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
          <div className="mode-switch" role="radiogroup" aria-label="Use my notes">
            <span className="mode-switch-label"><Icon name="folder" size={14} /> Notes{docs.length ? ` (${docs.length})` : ''}</span>
            {[['auto', 'Auto', 'Search my notes first and cite them when they help'],
              ['only', 'Only my notes', 'Answer strictly from my notes; say so when they do not cover it'],
              ['off', 'Off', 'Ignore my notes']].map(([val, name, tip]) => (
              <button key={val} type="button" role="radio" aria-checked={notesMode === val} title={tip}
                className={`mode-opt${notesMode === val ? ' on' : ''}`} onClick={() => chooseMode(val)}>{name}</button>
            ))}
          </div>
          <button className="btn btn-outline btn-sm" style={{ marginLeft: 'auto' }} onClick={handleClear}>
            Clear chat
          </button>
        </div>

        <div className="chat-messages">
          {loadingHistory ? (
            <div className="loading-spinner" style={{ margin: 'auto' }} />
          ) : messages.length === 0 ? (
            <div className="chat-empty">
              <h2 className="empty-title">What are you working on today?</h2>
              <p>Ask about any concept, problem or exam topic. I'll explain it at the level you choose, and you can speak instead of typing.</p>
              <div className="suggestion-row">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className={`chat-bubble ${m.role}`}>
                {m.role === 'assistant' ? (
                  <>
                    {m.content
                      ? <div className="markdown-content chat-md" dangerouslySetInnerHTML={{ __html: renderMarkdown(m.content) }} />
                      : <div className="typing-indicator inline"><div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" /></div>}
                    {m.rag?.searched && (
                      m.grounded
                        ? <NoteSources sources={m.sources} cited={m.streaming ? null : m.cited} />
                        : (
                          <div className="rag-note">
                            <Icon name="folder" size={13} />{' '}
                            {m.rag.mode === 'only'
                              ? 'Your notes had nothing relevant to this question.'
                              : 'Checked your notes and found nothing relevant, so this is a general answer.'}
                          </div>
                        )
                    )}
                    {m.rag?.searched && !m.streaming && (
                      <div className="rag-detail">
                        {m.rag.query && <>Searched for “{m.rag.query}” · </>}
                        {m.rag.retrieval === 'hybrid' ? 'semantic + keyword search' : 'keyword search'}
                        {m.rag.retrieval === 'keyword' && m.rag.embeddingError ? ' (semantic search unavailable)' : ''}
                        {' · '}{m.rag.ms} ms
                      </div>
                    )}
                    {!m.streaming && m.content && (
                      <div className="bubble-meta">
                        <button className="link-btn" onClick={() => toggleSpeak(m)}>
                          {speakingId === m.id ? <><Icon name="stop" size={13} /> Stop</> : <><Icon name="speaker" size={14} /> Read aloud</>}
                        </button>
                        {m.source && <SourceBadge source={m.source} seconds={m.firstToken} />}
                      </div>
                    )}
                  </>
                ) : m.content}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-row" onSubmit={handleSubmit}>
          {SpeechRecognition && (
            <button type="button" className={`btn btn-outline mic-btn${listening ? ' listening' : ''}`}
              onClick={toggleMic} title="Speak your question">
              <Icon name="mic" size={18} />
            </button>
          )}
          <textarea
            rows={1}
            placeholder="Ask a question. Press Enter to send."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className="btn btn-primary" type="submit" disabled={sending || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
