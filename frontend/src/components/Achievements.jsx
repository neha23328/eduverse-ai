import { useEffect, useState } from 'react';
import { getGamification } from '../services/api';
import Icon, { BADGE_ICONS } from './Icon';

export default function Achievements() {
  const [g, setG] = useState(null);

  useEffect(() => {
    getGamification().then(setG).catch(() => {});
  }, []);

  if (!g) return null;
  const span = Math.max(1, g.nextLevelXp - g.levelStartXp);
  const pct = Math.min(100, Math.round(((g.xp - g.levelStartXp) / span) * 100));
  const earned = g.badges.filter((b) => b.earned).length;

  return (
    <div className="two-col-grid">
      <div className="card">
        <div className="section-title">Your level and badges</div>
        <div className="xp-header">
          <div className="level-pill">Lv {g.level}</div>
          <div style={{ flex: 1 }}>
            <div className="xp-text">{g.xp} XP <span>· {g.nextLevelXp - g.xp} XP to level {g.level + 1}</span></div>
            <div className="progress-track"><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
          </div>
        </div>
        <div className="badge-grid">
          {g.badges.map((b) => (
            <div key={b.id} className={`ach-badge${b.earned ? ' earned' : ''}`} title={b.desc}>
              <div className="ach-icon"><Icon name={BADGE_ICONS[b.id] || 'target'} size={22} /></div>
              <div className="ach-name">{b.name}</div>
              <div className="ach-desc">{b.earned ? 'Unlocked' : b.desc}</div>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 10 }}>
          You've unlocked {earned} of {g.badges.length} badges.
        </div>
      </div>

      <div className="card">
        <div className="section-title">Class leaderboard</div>
        {g.leaderboard.map((r) => (
          <div key={r.rank + r.name} className={`lb-row${r.isMe ? ' me' : ''}`}>
            <div className="lb-rank">{`#${r.rank}`}</div>
            <div className="lb-name">{r.name}{r.isMe ? ' (you)' : ''}</div>
            <div className="lb-level">Lv {r.level}</div>
            <div className="lb-xp">{r.xp} XP</div>
          </div>
        ))}
        <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 10 }}>
          How XP works: a quiz earns 20 (plus 15 for 70% or more), a finished topic 30, a task 10, and each mentor question 2.
        </div>
      </div>
    </div>
  );
}
