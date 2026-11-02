export default function SubjectProgress({ subject }) {
  return (
    <div className="subject-card">
      <div className="subject-header">
        <span>{subject.subject}</span>
        <span>{subject.percentage}%</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${subject.percentage}%` }} />
      </div>
      <div className="subject-meta">
        <span>{subject.completedTopics} of {subject.totalTopics} topics</span>
        {subject.averageScore > 0 && <span>Avg score: {subject.averageScore}%</span>}
      </div>
    </div>
  );
}
