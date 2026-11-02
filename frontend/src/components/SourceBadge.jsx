const MAP = {
  live: { text: 'Live AI answer', cls: 'badge-primary' },
  cache: { text: 'Saved answer (instant)', cls: 'badge-success' },
  offline: { text: 'Offline copy', cls: 'badge-warning' },
};

export default function SourceBadge({ source, seconds }) {
  const m = MAP[source];
  if (!m) return null;
  return (
    <span className={`badge ${m.cls}`} title="Where this response came from">
      {m.text}{seconds != null ? ` · ${seconds}s` : ''}
    </span>
  );
}
