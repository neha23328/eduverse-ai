import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { createSubject } from '../services/api';
import { COURSES, OTHER_COURSE, LEARNING_STYLES, searchCourses } from '../data/courses';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '', career_goal: '', learning_style: '' });
  const [course, setCourse] = useState(null);
  const [query, setQuery] = useState('');
  const [specialization, setSpecialization] = useState('');
  const [semester, setSemester] = useState('');
  const [picked, setPicked] = useState([]);        // starter subjects to add after sign-up
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const matches = useMemo(() => searchCourses(query), [query]);
  const popular = COURSES.filter((c) => c.popular);

  function update(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  function chooseCourse(c) {
    setCourse(c);
    setQuery('');
    setSpecialization('');
    setSemester('');
    setPicked(c.subjects.slice(0, 5));
  }

  function clearCourse() { setCourse(null); setPicked([]); }

  function toggleSubject(s) {
    setPicked((p) => (p.includes(s) ? p.filter((x) => x !== s) : [...p, s]));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (form.password.length < 6) { setError('Password must be at least 6 characters.'); return; }
    if (!course) { setError('Choose your course so the mentor can match its syllabus.'); return; }
    setLoading(true);
    try {
      await register({
        ...form,
        branch: specialization ? `${course.label} (${specialization})` : course.label,
        semester,
      });
      // Starter subjects are a convenience: a failure here must not block the sign-up.
      await Promise.allSettled(picked.map((s) => createSubject({ subject: s, total_topics: 10 })));
      navigate('/');
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="reg-page">
      <div className="reg-top">
        <div className="landing-brand">
          <div className="sidebar-brand-icon">EV</div>
          <span className="brand-name">EduVerse</span>
        </div>
        <h1>Create your account</h1>
        <p>Tell us your course and we will set up subjects, practice and study plans to match it.</p>
      </div>

      <form className="reg-card" onSubmit={handleSubmit}>
        {error && <div className="error-banner" role="alert">{error}</div>}

        <fieldset className="reg-section">
          <legend>Your details</legend>
          <div className="form-group">
            <label className="form-label" htmlFor="r-name">Full name</label>
            <input id="r-name" className="form-input" value={form.name} onChange={(e) => update('name', e.target.value)} autoComplete="name" required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label" htmlFor="r-email">Email</label>
              <input id="r-email" type="email" className="form-input" value={form.email} onChange={(e) => update('email', e.target.value)} placeholder="you@college.edu" autoComplete="email" required />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="r-pass">Password</label>
              <input id="r-pass" type="password" className="form-input" value={form.password} onChange={(e) => update('password', e.target.value)} placeholder="At least 6 characters" autoComplete="new-password" required />
            </div>
          </div>
        </fieldset>

        <fieldset className="reg-section">
          <legend>Your course</legend>

          {!course ? (
            <>
              <div className="course-chips" role="group" aria-label="Popular courses">
                {popular.map((c) => (
                  <button key={c.id} type="button" className="course-chip" onClick={() => chooseCourse(c)}>
                    <strong>{c.label}</strong><span>{c.level}</span>
                  </button>
                ))}
              </div>
              <div className="form-group" style={{ marginTop: 14, position: 'relative' }}>
                <label className="form-label" htmlFor="r-course">Or search for your course</label>
                <input id="r-course" className="form-input" value={query} onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. B.Tech, M.Sc, commerce" autoComplete="off" />
                {query.trim() && (
                  <ul className="suggest-list">
                    {matches.map((c) => (
                      <li key={c.id}>
                        <button type="button" onClick={() => chooseCourse(c)}>
                          <strong>{c.label}</strong> <span>{c.full}</span>
                        </button>
                      </li>
                    ))}
                    <li>
                      <button type="button" onClick={() => chooseCourse({ ...OTHER_COURSE, label: query.trim() })}>
                        Use “{query.trim()}” as my course
                      </button>
                    </li>
                  </ul>
                )}
              </div>
            </>
          ) : (
            <div className="course-picked">
              <div>
                <strong>{course.label}</strong>
                <span>{course.full}</span>
              </div>
              <button type="button" className="btn btn-outline btn-sm" onClick={clearCourse}>Change</button>
            </div>
          )}

          {course && (
            <>
              <div className="form-row" style={{ marginTop: 14 }}>
                <div className="form-group">
                  <label className="form-label" htmlFor="r-sem">Current semester</label>
                  <select id="r-sem" className="form-select" value={semester} onChange={(e) => setSemester(e.target.value)}>
                    <option value="">Select semester</option>
                    {Array.from({ length: course.semesters }, (_, i) => i + 1).map((n) => <option key={n} value={n}>Semester {n}</option>)}
                  </select>
                </div>
                {course.specializations.length > 0 && (
                  <div className="form-group">
                    <label className="form-label" htmlFor="r-spec">Specialisation (optional)</label>
                    <select id="r-spec" className="form-select" value={specialization} onChange={(e) => setSpecialization(e.target.value)}>
                      <option value="">Not decided yet</option>
                      {course.specializations.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="r-goal">Career goal (optional)</label>
                <input id="r-goal" className="form-input" value={form.career_goal} onChange={(e) => update('career_goal', e.target.value)} placeholder="Type your own or pick one" />
                <div className="pill-row">
                  {course.careers.map((c) => (
                    <button key={c} type="button" className={`pill${form.career_goal === c ? ' on' : ''}`} onClick={() => update('career_goal', c)}>{c}</button>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <span className="form-label">Subjects to add to your dashboard</span>
                <div className="pill-row">
                  {course.subjects.map((s) => (
                    <button key={s} type="button" className={`pill${picked.includes(s) ? ' on' : ''}`} aria-pressed={picked.includes(s)} onClick={() => toggleSubject(s)}>{s}</button>
                  ))}
                </div>
                <small className="reg-hint">Suggested for {course.label}. You can add or remove subjects any time.</small>
              </div>
            </>
          )}
        </fieldset>

        <fieldset className="reg-section">
          <legend>How do you like to learn? (optional)</legend>
          <div className="style-grid">
            {LEARNING_STYLES.map((s) => (
              <button key={s.value} type="button" className={`style-opt${form.learning_style === s.value ? ' on' : ''}`} aria-pressed={form.learning_style === s.value}
                onClick={() => update('learning_style', form.learning_style === s.value ? '' : s.value)}>
                <strong>{s.value}</strong><span>{s.hint}</span>
              </button>
            ))}
          </div>
        </fieldset>

        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? 'Creating your account...' : 'Create account'}
        </button>
        <div className="auth-switch">Already have an account? <Link to="/login">Log in</Link></div>
      </form>
    </div>
  );
}
