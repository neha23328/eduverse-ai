import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Icon from '../components/Icon';

const COLLEGE = import.meta.env.VITE_COLLEGE_NAME || '';
const FACTS = [
  { icon: 'chat', title: 'Ask anything you are studying', text: 'Clear explanations at the level you choose.' },
  { icon: 'folder', title: 'Use your own notes', text: 'Answers point back to the page they came from.' },
  { icon: 'trend', title: 'See how you are doing', text: 'Quizzes, streaks and a plan for what to do next.' },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function signIn(e, p, demo = false) {
    setError('');
    setLoading(true);
    try {
      await login(e, p);
      navigate('/');
    } catch (err) {
      setError(demo
        ? "The demo account isn't set up yet. In the backend folder, run: python seed_demo.py"
        : (err.message || "We couldn't log you in. Check your email and password."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="landing">
      <div className="landing-top">
        <div className="landing-brand">
          <div className="sidebar-brand-icon">EV</div>
          <span className="brand-name">EduVerse</span>
        </div>
        <h1>A study companion that adapts to how you learn.</h1>
        <p>Pick how you would like to get started.</p>
      </div>

      <div className="landing-tiles">
        <section className="tile tile-form">
          <div className="tile-icon"><Icon name="user" size={26} /></div>
          <h2>Student login</h2>
          {error && <div className="error-banner">{error}</div>}
          <form onSubmit={(e) => { e.preventDefault(); signIn(email, password); }}>
            <label className="form-label" htmlFor="email">Email</label>
            <input id="email" type="email" className="form-input" value={email} autoComplete="email"
              onChange={(e) => setEmail(e.target.value)} placeholder="you@college.edu" required />
            <label className="form-label" htmlFor="password" style={{ marginTop: 10, display: 'block' }}>Password</label>
            <input id="password" type="password" className="form-input" value={password} autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)} required />
            <button type="submit" className="btn btn-primary tile-btn" disabled={loading}>
              {loading ? 'Logging in…' : 'Log in'}
            </button>
          </form>
        </section>

        <section className="tile">
          <div className="tile-icon"><Icon name="bulb" size={26} /></div>
          <h2>Just visiting?</h2>
          <p>Look around with a sample student who already has quizzes, notes and a study streak. No sign-up needed.</p>
          <button type="button" className="btn btn-primary tile-btn" disabled={loading}
            onClick={() => signIn('demo@eduverse.ai', 'demo1234', true)}>
            Explore the demo
          </button>
        </section>

        <section className="tile">
          <div className="tile-icon"><Icon name="book" size={26} /></div>
          <h2>New student</h2>
          <p>Create an account to keep your own subjects, notes and progress. It takes a minute.</p>
          <Link to="/register" className="btn btn-primary tile-btn">Create an account</Link>
        </section>
      </div>

      <div className="landing-band">
        <ul className="landing-facts">
          {FACTS.map((f) => (
            <li key={f.title}>
              <span className="fact-icon"><Icon name={f.icon} size={20} /></span>
              <span><strong>{f.title}</strong><br />{f.text}</span>
            </li>
          ))}
        </ul>
        {COLLEGE && <div className="landing-college">{COLLEGE}</div>}
      </div>
    </div>
  );
}
