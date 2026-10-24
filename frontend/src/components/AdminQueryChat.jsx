import React, { useState, useMemo } from 'react';
import { api } from '../api.js';
import { CommonIssueList } from './CommonIssues.jsx';

const EXAMPLES = [
  'How many unresolved complaints by category this month?',
  'Top 5 locations with most complaints in the last 30 days',
  'Average resolution time by department',
  'Show oldest open high priority tickets',
  'Weekly trend of food complaints',
  'Safety issues in Hostel 1 last month'
];

const METRIC_LABELS = { count: 'Ticket counts', avg_resolution: 'Resolution time', list: 'Ticket list' };

function formatCell(key, value) {
  if (value === null || value === undefined) return '—';
  if (key === 'created_at') return new Date(value).toLocaleString();
  if (key === 'status') return String(value).replace('_', ' ');
  if (typeof value === 'number' && !Number.isInteger(value)) return value.toFixed(1);
  return String(value);
}

function toCsv(columns, rows) {
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const lines = [columns.map((c) => esc(c.label)).join(',')];
  for (const row of rows) lines.push(columns.map((c) => esc(row[c.key])).join(','));
  return lines.join('\r\n');
}

function downloadCsv(result) {
  const blob = new Blob([toCsv(result.columns, result.rows)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `campusresolve-report-${result.plan.from}-to-${result.plan.to}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AdminQueryChat({ categories, departments }) {
  const [messages, setMessages] = useState([]);
  const [selected, setSelected] = useState(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sort, setSort] = useState({ key: null, dir: 1 });
  const [rowFilter, setRowFilter] = useState('');

  const result = selected !== null ? messages[selected]?.result : null;

  async function run(body, label) {
    setBusy(true);
    setError('');
    try {
      const res = await api.askDashboardQuery(body);
      setMessages((prev) => {
        const next = [...prev, { role: 'user', text: label }, { role: 'assistant', result: res }];
        setSelected(next.length - 1);
        return next;
      });
      setSort({ key: null, dir: 1 });
      setRowFilter('');
    } catch (err) {
      setError(err.message || 'The question could not be answered.');
    } finally {
      setBusy(false);
    }
  }

  function ask(e, question) {
    if (e) e.preventDefault();
    const q = (question ?? text).trim();
    if (!q || busy) return;
    setText('');
    run({ text: q }, q);
  }

  function editPlan(change, label) {
    if (!result || busy) return;
    run({ plan: { ...result.plan, ...change } }, label);
  }

  const name = (list, id) => list.find((x) => x.id === id)?.name || `#${id}`;

  const chips = useMemo(() => {
    if (!result) return [];
    const p = result.plan;
    const out = [];
    p.category_ids.forEach((id) =>
      out.push({ label: `Category: ${name(categories, id)}`, change: { category_ids: p.category_ids.filter((x) => x !== id) } })
    );
    p.department_ids.forEach((id) =>
      out.push({ label: `Department: ${name(departments, id)}`, change: { department_ids: p.department_ids.filter((x) => x !== id) } })
    );
    p.locations.forEach((loc) =>
      out.push({ label: `Location: ${loc}`, change: { locations: p.locations.filter((x) => x !== loc) } })
    );
    if (p.statuses.length) out.push({ label: `Status: ${p.statuses.join(', ').replace(/_/g, ' ')}`, change: { statuses: [] } });
    if (p.priorities.length) out.push({ label: `Priority: ${p.priorities.join(', ')}`, change: { priorities: [] } });
    if (p.group_by) out.push({ label: `Grouped by ${p.group_by}`, change: { group_by: null } });
    return out;
  }, [result, categories, departments]);

  const rows = useMemo(() => {
    if (!result) return [];
    const needle = rowFilter.trim().toLowerCase();
    let list = needle
      ? result.rows.filter((r) => result.columns.some((c) => String(r[c.key] ?? '').toLowerCase().includes(needle)))
      : [...result.rows];
    if (sort.key) {
      list.sort((a, b) => {
        const x = a[sort.key];
        const y = b[sort.key];
        if (x === y) return 0;
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        return (x > y ? 1 : -1) * sort.dir;
      });
    }
    return list;
  }, [result, rowFilter, sort]);

  const maxTickets = result && result.plan.metric !== 'list' ? Math.max(1, ...result.rows.map((r) => r.tickets || 0)) : 1;

  return (
    <div className="query-layout">
      {/* Chat column */}
      <div className="card query-chat">
        <div className="card-header">
          <div>
            <h3 className="card-title">Ask CampusResolve</h3>
            <p className="section-subtitle">
              Ask in plain English. NLTK keyword parsing turns the question into a safe, editable report filter.
            </p>
          </div>
        </div>

        <div className="chat-log" aria-live="polite">
          {messages.length === 0 && (
            <div className="section-subtitle">
              Try one of these:
              <div className="example-list">
                {EXAMPLES.map((q) => (
                  <button key={q} type="button" className="btn btn-secondary btn-sm" onClick={() => ask(null, q)} disabled={busy}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className="chat-bubble chat-user">
                {m.text}
              </div>
            ) : (
              <button
                key={i}
                type="button"
                className={`chat-bubble chat-assistant ${selected === i ? 'active' : ''}`}
                onClick={() => setSelected(i)}
                title="Show this report"
              >
                {m.result.summary}
                <span className="chat-meta">
                  {m.result.rows.length} row(s) · {m.result.suggestions.length} suggestion(s) · view report →
                </span>
              </button>
            )
          )}
          {busy && <div className="section-subtitle">Analysing…</div>}
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form className="chat-input" onSubmit={ask}>
          <label htmlFor="admin-query" className="visually-hidden">
            Question
          </label>
          <input
            id="admin-query"
            className="form-input"
            value={text}
            maxLength={500}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. unresolved plumbing complaints in Block B this week"
            disabled={busy}
          />
          <button type="submit" className="btn btn-primary" disabled={busy || !text.trim()}>
            Ask
          </button>
        </form>
      </div>

      {/* Report column */}
      <div className="card query-report">
        {!result ? (
          <div className="empty-state">Ask a question to generate a report table here.</div>
        ) : (
          <>
            <div className="card-header">
              <div>
                <h3 className="card-title">Report: {METRIC_LABELS[result.plan.metric]}</h3>
                <p className="section-subtitle">
                  {result.query ? `“${result.query}”` : 'Edited filters'} · {result.plan.from} to {result.plan.to}
                </p>
              </div>
              <span className="badge source-badge">
                source: {result.source} {result.source === 'nlp' ? '(NLTK text analysis)' : '(Rules fallback)'}
              </span>
            </div>

            {result.warnings.map((w) => (
              <div key={w} className="alert alert-warning">
                {w}
              </div>
            ))}

            <div className="chip-row">
              <span className="chip chip-static">
                {result.plan.from} → {result.plan.to}
              </span>
              {chips.map((c) => (
                <span key={c.label} className="chip">
                  {c.label}
                  <button
                    type="button"
                    aria-label={`Remove ${c.label}`}
                    onClick={() => editPlan(c.change, `Removed “${c.label}”`)}
                    disabled={busy}
                  >
                    ×
                  </button>
                </span>
              ))}
              {result.plan.metric !== 'list' && !result.plan.group_by && (
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => editPlan({ metric: 'list' }, 'Show matching tickets')} disabled={busy}>
                  Show matching tickets
                </button>
              )}
            </div>

            <div className="query-summary">
              <strong>Summary:</strong> {result.summary}
            </div>

            {result.suggestions.length > 0 && (
              <>
                <h4 className="card-title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                  AI Suggestions ({result.suggestions.length})
                </h4>
                <div className="suggestion-list">
                  {result.suggestions.map((s) => (
                    <div key={s.title} className="suggestion">
                      <strong>{s.title}</strong>
                      <div className="suggestion-evidence">Evidence: {s.evidence}</div>
                      <div>Next step: {s.next_step}</div>
                    </div>
                  ))}
                </div>
              </>
            )}

            <h4 className="card-title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
              Common Issues in These Tickets ({result.common_issues.length})
            </h4>
            <CommonIssueList issues={result.common_issues} emptyText="No issue appears in more than one matching ticket." />

            <div className="table-toolbar" style={{ marginTop: '0.9rem' }}>
              <input
                className="form-input"
                value={rowFilter}
                onChange={(e) => setRowFilter(e.target.value)}
                placeholder="Filter rows…"
                aria-label="Filter table rows"
              />
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => downloadCsv(result)} disabled={!result.rows.length}>
                Export CSV
              </button>
            </div>

            {rows.length === 0 ? (
              <div className="empty-state">No rows to show.</div>
            ) : (
              <div className="table-wrap">
                <table className="report-table">
                  <thead>
                    <tr>
                      {result.columns.map((c) => (
                        <th key={c.key} aria-sort={sort.key === c.key ? (sort.dir > 0 ? 'ascending' : 'descending') : 'none'}>
                          <button
                            type="button"
                            onClick={() => setSort((s) => ({ key: c.key, dir: s.key === c.key ? -s.dir : 1 }))}
                          >
                            {c.label}
                            {sort.key === c.key ? (sort.dir > 0 ? ' ▲' : ' ▼') : ''}
                          </button>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr key={row.id ?? `${row.label}-${i}`}>
                        {result.columns.map((c) => (
                          <td key={c.key}>
                            {c.key === 'tickets' ? (
                              <div className="cell-bar">
                                <span>{row.tickets}</span>
                                <div className="bar-track">
                                  <div className="bar-fill" style={{ width: `${Math.round((row.tickets / maxTickets) * 100)}%` }} />
                                </div>
                              </div>
                            ) : (
                              formatCell(c.key, row[c.key])
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
