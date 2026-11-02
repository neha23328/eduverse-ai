import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Icon from './Icon';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: 'grid', end: true },
  { to: '/mentor', label: 'AI Mentor', icon: 'chat' },
  { to: '/notes', label: 'My Notes', icon: 'folder' },
  { to: '/quiz', label: 'Quizzes', icon: 'quiz' },
  { to: '/study-material', label: 'Study Material', icon: 'book' },
  { to: '/planner', label: 'Study Planner', icon: 'calendar' },
];

const COLLEGE = import.meta.env.VITE_COLLEGE_NAME || '';

export default function AppLayout() {
  const { student, logout } = useAuth();

  const initials = (student?.name || '?')
    .split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase();

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="topbar-brand" aria-label="EduVerse home">
          <div className="sidebar-brand-icon">EV</div>
          <span className="brand-name">EduVerse</span>
        </NavLink>

        <nav className="topbar-nav" aria-label="Main">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}
              className={({ isActive }) => `topbar-link${isActive ? ' active' : ''}`}>
              <Icon name={item.icon} size={17} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="topbar-user">
          <NavLink to="/profile" className={({ isActive }) => `topbar-profile${isActive ? ' active' : ''}`}>
            <span className="avatar">{initials}</span>
            <span className="topbar-name">{student?.name}</span>
          </NavLink>
          <button className="topbar-logout" onClick={logout}>Log out</button>
        </div>
      </header>

      <main className="main-content">
        <Outlet />
      </main>

      <footer className="app-footer">
        EduVerse AI{COLLEGE ? ` · ${COLLEGE}` : ''} · A personalised learning assistant
      </footer>
    </div>
  );
}
