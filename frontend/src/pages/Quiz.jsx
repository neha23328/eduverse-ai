import { useEffect, useState } from 'react';
import { generateQuiz, submitQuiz, getQuizHistory } from '../services/api';
import SourceBadge from '../components/SourceBadge';
import UseNotes from '../components/UseNotes';
import NoteSources from '../components/NoteSources';

const DIFFICULTIES = ['beginner', 'intermediate', 'advanced'];

export default function Quiz() {
  const [stage, setStage] = useState('setup'); // setup | taking | result
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [difficulty, setDifficulty] = useState('intermediate');
  const [numQuestions, setNumQuestions] = useState(5);
  const [useNotes, setUseNotes] = useState(false);

  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getQuizHistory().then(setHistory).catch(() => {});
  }, []);

  async function handleGenerate(e) {
    e.preventDefault();
    if (!subject.trim() || !topic.trim()) return;
    setError('');
    setLoading(true);
    try {
      const q = await generateQuiz({ subject, topic, difficulty, num_questions: Number(numQuestions), use_notes: useNotes });
      setQuiz(q);
      setAnswers({});
      setStage('taking');
    } catch (err) {
      setError(err.message || 'Failed to generate quiz. Check your Gemini API key in backend/.env');
    } finally {
      setLoading(false);
    }
  }

  function selectAnswer(questionIndex, optionIndex) {
    setAnswers((prev) => ({ ...prev, [questionIndex]: optionIndex }));
  }

  async function handleSubmit() {
    setError('');
    setLoading(true);
    try {
      const payload = {
        quiz_id: quiz.id,
        answers: Object.entries(answers).map(([qIdx, selIdx]) => ({
          question_index: Number(qIdx),
          selected_index: selIdx,
        })),
      };
      const res = await submitQuiz(payload);
      setResult(res);
      setStage('result');
      getQuizHistory().then(setHistory).catch(() => {});
    } catch (err) {
      setError(err.message || 'Failed to submit quiz');
    } finally {
      setLoading(false);
    }
  }

  function handleRetake() {
    setStage('setup');
    setQuiz(null);
    setResult(null);
    setAnswers({});
  }

  const allAnswered = quiz && Object.keys(answers).length === quiz.questions.length;

  return (
    <div>
      <div className="page-header">
        <h1>Quizzes</h1>
        <p>Test your understanding with AI-generated quizzes and get instant feedback.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {stage === 'setup' && (
        <div className="two-col-grid">
          <div className="card quiz-setup-card">
            <div className="section-title">Generate a quiz</div>
            <form onSubmit={handleGenerate}>
              <div className="form-group">
                <label className="form-label">Subject</label>
                <input className="form-input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="e.g. Data Structures" required />
              </div>
              <div className="form-group">
                <label className="form-label">Topic</label>
                <input className="form-input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Binary Trees" required />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Difficulty</label>
                  <select className="form-select" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                    {DIFFICULTIES.map((d) => <option key={d} value={d}>{d[0].toUpperCase() + d.slice(1)}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Questions</label>
                  <select className="form-select" value={numQuestions} onChange={(e) => setNumQuestions(e.target.value)}>
                    {[3, 5, 8, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
              </div>
              <UseNotes checked={useNotes} onChange={setUseNotes} what="questions" />
              <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
                {loading ? 'Generating...' : 'Generate Quiz'}
              </button>
            </form>
          </div>

          <div className="card">
            <div className="section-title">Recent attempts</div>
            {history.length === 0 ? (
              <div className="empty-state">No quiz attempts yet.</div>
            ) : (
              history.map((h) => (
                <div key={h.id} className="task-row">
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{h.subject}</div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                      {h.correctAnswers}/{h.totalQuestions} correct
                    </div>
                  </div>
                  <span className={`badge ${h.score >= 70 ? 'badge-success' : 'badge-warning'}`}>{h.score}%</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {stage === 'taking' && quiz && (
        <div>
          <div className="card" style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>{quiz.subject}</strong> — {quiz.topic}
              <span className="badge badge-primary" style={{ marginLeft: 10 }}>{quiz.difficulty}</span>
              <span style={{ marginLeft: 8 }}><SourceBadge source={quiz.source} /></span>
              {quiz.from_notes && <span className="badge badge-success" style={{ marginLeft: 8 }}>From your notes</span>}
            </div>
            <div style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
              {Object.keys(answers).length} / {quiz.questions.length} answered
            </div>
          </div>

          {quiz.from_notes && (
            <div className="card" style={{ marginBottom: 20 }}>
              <NoteSources sources={quiz.note_sources} label="Questions are based on" />
            </div>
          )}

          {quiz.questions.map((q, qi) => (
            <div key={qi} className="card quiz-question-card">
              <div className="quiz-question-text">{qi + 1}. {q.question}</div>
              {q.options.map((opt, oi) => (
                <div
                  key={oi}
                  className={`quiz-option${answers[qi] === oi ? ' selected' : ''}`}
                  onClick={() => selectAnswer(qi, oi)}
                >
                  {opt}
                </div>
              ))}
            </div>
          ))}

          <button className="btn btn-primary btn-block" onClick={handleSubmit} disabled={!allAnswered || loading}>
            {loading ? 'Submitting...' : allAnswered ? 'Submit Quiz' : `Answer all questions to submit (${Object.keys(answers).length}/${quiz.questions.length})`}
          </button>
        </div>
      )}

      {stage === 'result' && result && (
        <div>
          <div className="quiz-result-banner">
            <div style={{ fontSize: 14, color: 'var(--color-text-muted)', marginBottom: 6 }}>Your score</div>
            <div className="quiz-result-score">{result.score}%</div>
            <div style={{ marginTop: 6, fontSize: 14 }}>{result.correct_answers} of {result.total_questions} correct</div>
          </div>

          {result.review.map((r, i) => (
            <div key={i} className="card quiz-question-card">
              <div className="quiz-question-text">{i + 1}. {r.question}</div>
              {r.options.map((opt, oi) => {
                let cls = 'quiz-option';
                if (oi === r.correct_index) cls += ' correct';
                else if (oi === r.selected_index && !r.is_correct) cls += ' incorrect';
                return <div key={oi} className={cls}>{opt}</div>;
              })}
              <div className="explanation-box">{r.explanation}</div>
            </div>
          ))}

          <button className="btn btn-primary btn-block" onClick={handleRetake}>Take another quiz</button>
        </div>
      )}
    </div>
  );
}
