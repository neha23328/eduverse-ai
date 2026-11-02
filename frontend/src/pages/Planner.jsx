import { useState } from 'react';
import { generateStudyPlan, createTask } from '../services/api';
import SourceBadge from '../components/SourceBadge';
import { useAuth } from '../context/AuthContext';

export default function Planner() {
  const { student } = useAuth();
  const [goal, setGoal] = useState('');
  const [hoursPerDay, setHoursPerDay] = useState(2);
  const [days, setDays] = useState(7);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [added, setAdded] = useState({});
  const [elapsed, setElapsed] = useState(null);

  async function handleGenerate(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    setPlan(null);
    setAdded({});
    const t0 = performance.now();
    try {
      const res = await generateStudyPlan({
        goal: goal || student?.career_goal || '',
        hours_per_day: Number(hoursPerDay),
        days: Number(days),
      });
      setPlan(res);
      setElapsed(((performance.now() - t0) / 1000).toFixed(1));
    } catch (err) {
      setError(err.message || 'Failed to generate plan. Check your Gemini API key in backend/.env');
    } finally {
      setLoading(false);
    }
  }

  async function addDayToTasks(day) {
    try {
      await Promise.all((day.tasks || []).map((t) =>
        createTask({ title: `Day ${day.day}: ${t}`, subject: day.focus_subjects?.[0] || '' })));
      setAdded((a) => ({ ...a, [day.day]: true }));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Study Planner</h1>
        <p>Get a personalized day-by-day plan based on your progress and goals.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card" style={{ marginBottom: 24, maxWidth: 560 }}>
        <form onSubmit={handleGenerate}>
          <div className="form-group">
            <label className="form-label">Goal (optional — defaults to your profile career goal)</label>
            <input
              className="form-input"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder={student?.career_goal || 'e.g. Ace upcoming semester exams'}
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Hours per day</label>
              <input
                type="number" min="0.5" max="12" step="0.5"
                className="form-input" value={hoursPerDay}
                onChange={(e) => setHoursPerDay(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Plan length (days)</label>
              <select className="form-select" value={days} onChange={(e) => setDays(e.target.value)}>
                {[3, 5, 7, 14].map((d) => <option key={d} value={d}>{d} days</option>)}
              </select>
            </div>
          </div>
          <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
            {loading ? 'Generating plan...' : 'Generate Study Plan'}
          </button>
        </form>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="loading-spinner" />
          <p style={{ marginTop: 12, color: 'var(--color-text-muted)' }}>Building your personalized plan...</p>
        </div>
      )}

      {plan && !loading && (
        <div>
          <div style={{ marginBottom: 12 }}><SourceBadge source={plan.source} seconds={elapsed} /></div>
          {plan.notes && (
            <div className="card" style={{ marginBottom: 20, background: 'var(--color-primary-light)' }}>
              <strong>Strategy: </strong>{plan.notes}
            </div>
          )}
          {plan.plan?.map((day) => (
            <div key={day.day} className="plan-day-card">
              <div className="plan-day-header">
                <span className="plan-day-title">Day {day.day}</span>
                <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <button className="btn btn-outline btn-sm" disabled={added[day.day]} onClick={() => addDayToTasks(day)}>
                    {added[day.day] ? 'Added to your tasks' : 'Add to my tasks'}
                  </button>
                  <span className="badge badge-primary">{day.estimated_hours}h</span>
                </span>
              </div>
              <div style={{ marginBottom: 10 }}>
                {day.focus_subjects?.map((s) => (
                  <span key={s} className="badge badge-success" style={{ marginRight: 6 }}>{s}</span>
                ))}
              </div>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {day.tasks?.map((t, i) => <li key={i} style={{ fontSize: 14, marginBottom: 4 }}>{t}</li>)}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
