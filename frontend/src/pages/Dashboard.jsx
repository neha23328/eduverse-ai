import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import {
  getDashboardSummary, getSubjectProgress, getWeeklyActivity,
  getTasks, updateTask, createTask, deleteTask, createSubject, getWeakTopics,
} from '../services/api';
import { useAuth } from '../context/AuthContext';
import StatCard from '../components/StatCard';
import SubjectProgress from '../components/SubjectProgress';
import Achievements from '../components/Achievements';
import Icon from '../components/Icon';

export default function Dashboard() {
  const { student } = useAuth();
  const [summary, setSummary] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [weekly, setWeekly] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [weakTopics, setWeakTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newSubjectName, setNewSubjectName] = useState('');
  const [showAddSubject, setShowAddSubject] = useState(false);

  async function loadAll() {
    try {
      const [summaryData, subjectData, weeklyData, taskData, weakData] = await Promise.all([
        getDashboardSummary(),
        getSubjectProgress(),
        getWeeklyActivity(),
        getTasks(),
        getWeakTopics(),
      ]);
      setSummary(summaryData);
      setSubjects(subjectData);
      setWeekly(weeklyData);
      setTasks(taskData);
      setWeakTopics(weakData);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleToggleTask(task) {
    const newStatus = task.status === 'completed' ? 'pending' : 'completed';
    setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, status: newStatus } : t)));
    try {
      await updateTask(task.id, newStatus);
      const summaryData = await getDashboardSummary();
      setSummary(summaryData);
    } catch (err) {
      loadAll();
    }
  }

  async function handleDeleteTask(taskId) {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
    try {
      await deleteTask(taskId);
    } catch (err) {
      loadAll();
    }
  }

  async function handleAddTask(e) {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    try {
      const task = await createTask({ title: newTaskTitle.trim() });
      setTasks((prev) => [task, ...prev]);
      setNewTaskTitle('');
      const summaryData = await getDashboardSummary();
      setSummary(summaryData);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAddSubject(e) {
    e.preventDefault();
    if (!newSubjectName.trim()) return;
    try {
      const subject = await createSubject({ subject: newSubjectName.trim(), total_topics: 10 });
      setSubjects((prev) => [...prev, subject]);
      setNewSubjectName('');
      setShowAddSubject(false);
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 100 }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const scored = subjects.filter((x) => x.averageScore > 0).sort((x, y) => x.averageScore - y.averageScore);
  const weakest = scored[0];
  const streak = summary?.studyStreak ?? 0;
  const overview = {
    text: subjects.length === 0
      ? "Let's set up your first subject so we can start tracking your progress."
      : [streak > 1 ? `You're on a ${streak}-day streak.` : 'Welcome back.',
         weakest ? `${weakest.subject} needs the most attention right now (average ${weakest.averageScore}%).` : 'Take a quiz to see where you stand.'].join(' '),
    nextText: weakTopics[0]
      ? `A short quiz on ${weakTopics[0]} will show whether it has sunk in.`
      : weakest ? `Revise ${weakest.subject} with a few practice questions.` : 'Ask the mentor about something you are studying today.',
    nextCta: weakTopics[0] || weakest ? 'Start a quiz' : 'Ask the mentor',
    nextTo: weakTopics[0] || weakest ? '/quiz' : '/mentor',
  };

  const pendingTasks = tasks.filter((t) => t.status !== 'completed');
  const completedTasks = tasks.filter((t) => t.status === 'completed');
  const totalTasks = pendingTasks.length + completedTasks.length;
  const taskPct = totalTasks ? Math.round((completedTasks.length / totalTasks) * 100) : 0;
  const quizAvg = summary?.averageScore || 0;
  const progressPct = summary?.overallProgress || 0;

  function TaskRow({ task }) {
    const done = task.status === 'completed';
    return (
      <div className="task-row">
        <div className={`task-checkbox${done ? ' checked' : ''}`} onClick={() => handleToggleTask(task)}
          role="checkbox" aria-checked={done} tabIndex={0}
          onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); handleToggleTask(task); } }}>
          {done && '✓'}
        </div>
        <div className={`task-title${done ? ' completed' : ''}`}>{task.title}</div>
        {task.subject && <span className="task-subject-badge">{task.subject}</span>}
        <button className="task-delete-btn" aria-label="Remove task" onClick={() => handleDeleteTask(task.id)}>✕</button>
      </div>
    );
  }

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}

      <section className="hero">
        <div className="hero-main">
          <h1>{greeting}, {student?.name?.split(' ')[0]}.</h1>
          <p>{overview.text}</p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to={overview.nextTo}>{overview.nextCta} <Icon name="arrow" size={16} /></Link>
            {overview.nextTo !== '/mentor' && <Link className="btn btn-light" to="/mentor">Ask the mentor</Link>}
            <Link className="btn btn-light" to="/planner">Plan my week</Link>
          </div>
        </div>
        <aside className="hero-next">
          <div className="hero-next-label">Suggested next step</div>
          <div className="hero-next-text">{overview.nextText}</div>
        </aside>
      </section>

      <div className="metrics">
        <div className="metric">
          <div className="metric-label"><Icon name="trend" size={16} />Course progress</div>
          <div className="metric-value">{progressPct}%</div>
          <div className="progress-track"><div className="progress-fill" style={{ width: `${progressPct}%` }} /></div>
          <div className="metric-note">of your topics completed</div>
        </div>
        <div className="metric">
          <div className="metric-label"><Icon name="check" size={16} />Tasks done</div>
          <div className="metric-value">{completedTasks.length}<span>/{totalTasks}</span></div>
          <div className="progress-track"><div className="progress-fill" style={{ width: `${taskPct}%` }} /></div>
          <div className="metric-note">{pendingTasks.length} still to do</div>
        </div>
        <div className="metric">
          <div className="metric-label"><Icon name="target" size={16} />Quiz average</div>
          <div className="metric-value">{quizAvg ? `${quizAvg}%` : '–'}</div>
          <div className="progress-track"><div className="progress-fill" style={{ width: `${quizAvg}%` }} /></div>
          <div className="metric-note">{quizAvg ? 'across your subjects' : 'take a quiz to see this'}</div>
        </div>
        <div className="metric">
          <div className="metric-label"><Icon name="flame" size={16} />Study streak</div>
          <div className="metric-value">{streak}<span> {streak === 1 ? 'day' : 'days'}</span></div>
          <div className="week-dots" aria-label="Study days this week">
            {weekly.map((w) => (
              <span key={w.date} className="week-dot-wrap" title={`${w.day}: ${w.minutes} min`}>
                <span className={`week-dot${w.minutes > 0 ? ' on' : ''}`} />
                <span className="week-dot-day">{w.day[0]}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      <Achievements />

      <h2 className="block-title">Learning analytics</h2>
      <div className="two-col-grid">
        <div className="card">
          <div className="section-title">Minutes studied this week</div>
          <ResponsiveContainer width="100%" height={230}>
            <LineChart data={weekly}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E3E6DF" />
              <XAxis dataKey="day" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} width={30} />
              <Tooltip formatter={(v) => [`${v} min`, 'Study time']} />
              <Line type="monotone" dataKey="minutes" stroke="#1E5AA8" strokeWidth={3} dot={{ r: 4, fill: '#fff', strokeWidth: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="section-title">Quiz average by subject</div>
          {scored.length === 0 ? (
            <div className="empty-state">Take a quiz in any subject and its average will appear here.</div>
          ) : (
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={scored} layout="vertical" margin={{ left: 10, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E3E6DF" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="subject" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} width={120} />
                <Tooltip formatter={(v) => [`${v}%`, 'Average']} />
                <Bar dataKey="averageScore" fill="#1E5AA8" radius={[0, 3, 3, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          )}
          {weakTopics.length > 0 && (
            <div className="revisit">
              <span className="revisit-label">Topics to revisit:</span>
              {weakTopics.map((t, i) => <span key={i} className="badge badge-warning">{t}</span>)}
            </div>
          )}
        </div>
      </div>

      <div className="two-col-grid">
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div className="section-title" style={{ marginBottom: 0 }}>Your subjects</div>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowAddSubject((v) => !v)}>Add subject</button>
          </div>
          {showAddSubject && (
            <form onSubmit={handleAddSubject} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <input className="form-input" placeholder="e.g. Data Structures" value={newSubjectName}
                onChange={(e) => setNewSubjectName(e.target.value)} autoFocus />
              <button className="btn btn-primary btn-sm" type="submit">Add</button>
            </form>
          )}
          {subjects.length === 0 ? (
            <div className="empty-state">No subjects yet. Add the ones you're studying this semester.</div>
          ) : subjects.map((x) => <SubjectProgress key={x.subject} subject={x} />)}
        </div>

        <div className="card">
          <div className="section-title">Your to-do list</div>
          <form onSubmit={handleAddTask} style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            <input className="form-input" placeholder="What do you need to finish?" value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)} />
            <button className="btn btn-primary btn-sm" type="submit">Add</button>
          </form>
          {totalTasks === 0 ? (
            <div className="empty-state">Nothing on your list. Add what you plan to finish this week.</div>
          ) : (
            <>
              {pendingTasks.map((t) => <TaskRow key={t.id} task={t} />)}
              {completedTasks.map((t) => <TaskRow key={t.id} task={t} />)}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
