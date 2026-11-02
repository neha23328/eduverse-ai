import Icon from './Icon';

export default function StatCard({ label, value, icon, note }) {
  return (
    <div className="stat-item">
      <div className="stat-item-label"><Icon name={icon} size={16} />{label}</div>
      <div className="stat-item-value">{value}</div>
      {note && <div className="stat-item-note">{note}</div>}
    </div>
  );
}
