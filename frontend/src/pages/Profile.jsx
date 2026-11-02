import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { updateProfile } from '../services/api';

const BRANCHES = ['CSE', 'ECE', 'ME', 'CE', 'EE', 'IT', 'Other'];
const LEARNING_STYLES = ['Visual', 'Reading/Writing', 'Practice-based', 'Mixed'];

export default function Profile() {
  const { student, refreshStudent } = useAuth();
  const [form, setForm] = useState({
    branch: student?.branch || '',
    semester: student?.semester || '',
    career_goal: student?.career_goal || '',
    learning_style: student?.learning_style || '',
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setSaved(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      await updateProfile(form);
      await refreshStudent();
      setSaved(true);
    } catch (err) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Profile</h1>
        <p>Manage your academic details and preferences.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="card" style={{ maxWidth: 520 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24 }}>
          <div className="avatar" style={{ width: 56, height: 56, fontSize: 20 }}>
            {(student?.name || '?').split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{student?.name}</div>
            <div style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>{student?.email}</div>
          </div>
        </div>

        <form onSubmit={handleSave}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Branch</label>
              <select className="form-select" value={form.branch} onChange={(e) => update('branch', e.target.value)}>
                <option value="">Select branch</option>
                {BRANCHES.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Semester</label>
              <input className="form-input" value={form.semester} onChange={(e) => update('semester', e.target.value)} placeholder="e.g. 5" />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Career goal</label>
            <input
              className="form-input"
              value={form.career_goal}
              onChange={(e) => update('career_goal', e.target.value)}
              placeholder="e.g. Software Engineer"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Preferred learning style</label>
            <select className="form-select" value={form.learning_style} onChange={(e) => update('learning_style', e.target.value)}>
              <option value="">Select style</option>
              {LEARNING_STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save changes'}
          </button>
          {saved && <span style={{ marginLeft: 12, color: 'var(--color-success)', fontSize: 14 }}>Saved</span>}
        </form>
      </div>
    </div>
  );
}
