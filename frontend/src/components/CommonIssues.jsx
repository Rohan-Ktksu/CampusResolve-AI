import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

function lastDays(days) {
  const now = new Date();
  return {
    from: new Date(now.getTime() - (days - 1) * 86400000).toISOString().slice(0, 10),
    to: now.toISOString().slice(0, 10)
  };
}

// Issues found by grouping complaints that share wording (NLTK); used by the dashboard, report and chat.
export function CommonIssueList({ issues, emptyText = 'No issue was reported more than once in this period.' }) {
  if (!Array.isArray(issues) || issues.length === 0) {
    return <div className="section-subtitle">{emptyText}</div>;
  }
  const [main, ...others] = issues;
  return (
    <div className="issue-list">
      <div className="issue-headline">
        <span className="issue-kicker">Main issue</span> {main.summary}
      </div>
      {[main, ...others].map((issue) => (
        <div key={issue.issue} className="issue-card">
          <div className="issue-title-row">
            <strong className="issue-name">{issue.issue}</strong>
            <span className="badge status-SUBMITTED">{issue.category}</span>
          </div>
          <div className="issue-stats">
            <span>
              <strong>{issue.times_reported}</strong> times reported
            </span>
            <span>
              <strong>{issue.student_reporters}</strong> students
            </span>
            <span>
              <strong>{issue.reporters}</strong> reporters in total
            </span>
            <span>
              <strong>{issue.open}</strong> still open
            </span>
            <span>
              {issue.first_reported === issue.last_reported
                ? issue.first_reported
                : `${issue.first_reported} → ${issue.last_reported}`}
            </span>
          </div>
          <div className="issue-meta">
            Where: {issue.locations.map((l) => `${l.location} (${l.count})`).join(', ')}
          </div>
          <div className="issue-meta">Tickets: {issue.ticket_numbers.join(', ')}</div>
          <ul className="issue-suggestions">
            {issue.suggestions.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default function CommonIssuesPanel() {
  const [range, setRange] = useState(() => lastDays(30));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function load(e) {
    if (e) e.preventDefault();
    setLoading(true);
    setError('');
    try {
      setData(await api.getCommonIssues(range.from, range.to));
    } catch (err) {
      setError(err.message || 'Could not load common issues.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Common Issues From Complaint Descriptions</h3>
          <p className="section-subtitle">
            Complaints are grouped by shared wording (NLTK stemming). Counts are reports and distinct reporting accounts.
          </p>
        </div>
        <span className="badge source-badge">source: nlp (NLTK text analysis)</span>
      </div>
      <form className="form-row" onSubmit={load} style={{ alignItems: 'end', marginBottom: '0.75rem' }}>
        <div className="form-group">
          <label className="form-label" htmlFor="issues-from">From</label>
          <input id="issues-from" type="date" className="form-input" value={range.from}
            onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))} />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="issues-to">To</label>
          <input id="issues-to" type="date" className="form-input" value={range.to}
            onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))} />
        </div>
        <div className="form-group">
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Analysing…' : 'Find common issues'}
          </button>
        </div>
      </form>
      {error && <div className="alert alert-error">{error}</div>}
      {data && (
        <>
          <p className="section-subtitle">{data.sample_size} complaint(s) analysed from {data.period.from} to {data.period.to}.</p>
          <CommonIssueList issues={data.issues} />
        </>
      )}
    </div>
  );
}
