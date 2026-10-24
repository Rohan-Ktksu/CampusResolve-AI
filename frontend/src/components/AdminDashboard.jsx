import React, { useState, useEffect } from 'react';
import { api } from '../api.js';
import TicketWorkspace from './TicketWorkspace.jsx';
import AdminQueryChat from './AdminQueryChat.jsx';
import CommonIssuesPanel, { CommonIssueList } from './CommonIssues.jsx';

function formatDefaultDates() {
  const now = new Date();
  const to = now.toISOString().slice(0, 10);
  const past = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  const from = past.toISOString().slice(0, 10);
  return { from, to };
}

export default function AdminDashboard({
  user,
  categories,
  departments,
  locations,
  onConfigChanged
}) {
  const [subTab, setSubTab] = useState('inbox');

  // Operational Inbox state
  const [tickets, setTickets] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [loadingInbox, setLoadingInbox] = useState(false);
  const [inboxError, setInboxError] = useState('');
  const [selectedId, setSelectedId] = useState(null);

  // Analytics state (GET /dashboard/stats)
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [statsError, setStatsError] = useState('');

  // Optional AI Insights state (GET /dashboard/insights & POST /dashboard/insights/report)
  const defaults = formatDefaultDates();
  const [fromDate, setFromDate] = useState(defaults.from);
  const [toDate, setToDate] = useState(defaults.to);
  const [insights, setInsights] = useState(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [insightsError, setInsightsError] = useState('');
  const [report, setReport] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState('');

  // Admin Config state (ADMIN only)
  const [newDeptName, setNewDeptName] = useState('');
  const [editDeptId, setEditDeptId] = useState(null);
  const [editDeptName, setEditDeptName] = useState('');

  const [newCatName, setNewCatName] = useState('');
  const [newCatDeptId, setNewCatDeptId] = useState('');
  const [editCatId, setEditCatId] = useState(null);
  const [editCatName, setEditCatName] = useState('');
  const [editCatDeptId, setEditCatDeptId] = useState('');

  const [configMsg, setConfigMsg] = useState('');
  const [configError, setConfigError] = useState('');

  useEffect(() => {
    if (subTab === 'inbox') {
      loadInbox();
    } else if (subTab === 'analytics') {
      loadStats();
    } else if (subTab === 'insights' && !insights) {
      loadInsights();
    }
  }, [subTab, statusFilter, categoryFilter]);

  async function loadInbox() {
    setLoadingInbox(true);
    setInboxError('');
    try {
      const list = await api.getComplaints({
        status: statusFilter || undefined,
        category_id: categoryFilter ? Number(categoryFilter) : undefined
      });
      const arr = Array.isArray(list) ? list : [];
      setTickets(arr);
      if (arr.length > 0 && (!selectedId || !arr.some((t) => t.id === selectedId))) {
        setSelectedId(arr[0].id);
      } else if (arr.length === 0) {
        setSelectedId(null);
      }
    } catch (err) {
      setInboxError(err.message || 'Failed to load operational queue.');
    } finally {
      setLoadingInbox(false);
    }
  }

  async function loadStats() {
    setLoadingStats(true);
    setStatsError('');
    try {
      const data = await api.getDashboardStats();
      setStats(data);
    } catch (err) {
      setStatsError(err.message || 'Failed to load resolution analytics.');
    } finally {
      setLoadingStats(false);
    }
  }

  function validateDateRange() {
    if (!fromDate || !toDate) return 'Both From and To UTC dates are required.';
    if (fromDate > toDate) return 'From date must be on or before To date.';
    const diffDays =
      (new Date(`${toDate}T00:00:00Z`) - new Date(`${fromDate}T00:00:00Z`)) /
      (1000 * 60 * 60 * 24);
    if (diffDays > 366) return 'Date range cannot exceed 366 days.';
    return '';
  }

  async function loadInsights(e) {
    if (e) e.preventDefault();
    const rangeErr = validateDateRange();
    if (rangeErr) {
      setInsightsError(rangeErr);
      return;
    }
    setLoadingInsights(true);
    setInsightsError('');
    try {
      const data = await api.getDashboardInsights(fromDate, toDate);
      setInsights(data);
    } catch (err) {
      setInsightsError(err.message || 'Failed to load cohort aggregates.');
    } finally {
      setLoadingInsights(false);
    }
  }

  async function handleGenerateReport() {
    const rangeErr = validateDateRange();
    if (rangeErr) {
      setReportError(rangeErr);
      return;
    }
    setGeneratingReport(true);
    setReportError('');
    try {
      const rep = await api.generateInsightsReport(fromDate, toDate);
      setReport(rep);
    } catch (err) {
      setReportError(err.message || 'Could not generate report.');
    } finally {
      setGeneratingReport(false);
    }
  }

  // Admin Department CRUD
  async function handleCreateDept(e) {
    e.preventDefault();
    if (!newDeptName.trim()) return;
    setConfigError('');
    setConfigMsg('');
    try {
      await api.createDepartment({ name: newDeptName.trim() });
      setNewDeptName('');
      setConfigMsg('Department created.');
      if (onConfigChanged) await onConfigChanged();
    } catch (err) {
      setConfigError(err.message || 'Failed to create department.');
    }
  }

  async function handleUpdateDept(e) {
    e.preventDefault();
    if (!editDeptId || !editDeptName.trim()) return;
    setConfigError('');
    setConfigMsg('');
    try {
      await api.updateDepartment(editDeptId, { name: editDeptName.trim() });
      setEditDeptId(null);
      setEditDeptName('');
      setConfigMsg('Department updated.');
      if (onConfigChanged) await onConfigChanged();
    } catch (err) {
      setConfigError(err.message || 'Failed to update department.');
    }
  }

  async function handleDeactivateDept(id, name) {
    if (!window.confirm(`Deactivate department "${name}"? Historical references remain intact.`)) {
      return;
    }
    setConfigError('');
    setConfigMsg('');
    try {
      await api.deactivateDepartment(id);
      setConfigMsg(`Department "${name}" deactivated.`);
      if (onConfigChanged) await onConfigChanged();
    } catch (err) {
      setConfigError(err.message || 'Failed to deactivate department.');
    }
  }

  // Admin Category CRUD
  async function handleCreateCat(e) {
    e.preventDefault();
    if (!newCatName.trim()) return;
    setConfigError('');
    setConfigMsg('');
    try {
      await api.createCategory({
        name: newCatName.trim(),
        default_department_id: newCatDeptId ? Number(newCatDeptId) : null
      });
      setNewCatName('');
      setNewCatDeptId('');
      setConfigMsg('Category created.');
      if (onConfigChanged) await onConfigChanged();
    } catch (err) {
      setConfigError(err.message || 'Failed to create category.');
    }
  }

  async function handleUpdateCat(e) {
    e.preventDefault();
    if (!editCatId || !editCatName.trim()) return;
    setConfigError('');
    setConfigMsg('');
    try {
      await api.updateCategory(editCatId, {
        name: editCatName.trim(),
        default_department_id: editCatDeptId ? Number(editCatDeptId) : null
      });
      setEditCatId(null);
      setEditCatName('');
      setEditCatDeptId('');
      setConfigMsg('Category updated.');
      if (onConfigChanged) await onConfigChanged();
    } catch (err) {
      setConfigError(err.message || 'Failed to update category.');
    }
  }

  async function handleDeactivateCat(id, name) {
    if (!window.confirm(`Deactivate category "${name}"? Historical references remain intact.`)) {
      return;
    }
    setConfigError('');
    setConfigMsg('');
    try {
      await api.deactivateCategory(id);
      setConfigMsg(`Category "${name}" deactivated.`);
      if (onConfigChanged) await onConfigChanged();
    } catch (err) {
      setConfigError(err.message || 'Failed to deactivate category.');
    }
  }

  function getDepartmentName(deptId) {
    if (!deptId) return 'Unassigned / Review';
    const d = departments.find((item) => item.id === deptId);
    return d ? d.name : `Department #${deptId}`;
  }

  function getCategoryName(catId) {
    if (!catId) return 'Uncategorized';
    const c = categories.find((item) => item.id === catId);
    return c ? c.name : `Category #${catId}`;
  }

  return (
    <div>
      {/* Single Admin Dashboard Sub-navigation */}
      <div className="sub-tabs">
        <button
          type="button"
          className={`sub-tab ${subTab === 'inbox' ? 'active' : ''}`}
          onClick={() => setSubTab('inbox')}
        >
          1. Operational Inbox &amp; AI Triage
        </button>
        <button
          type="button"
          className={`sub-tab ${subTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setSubTab('analytics')}
        >
          2. Resolution Analytics
        </button>
        <button
          type="button"
          className={`sub-tab ${subTab === 'insights' ? 'active' : ''}`}
          onClick={() => setSubTab('insights')}
        >
          3. AI Insights (Optional Tab)
        </button>
        <button
          type="button"
          className={`sub-tab ${subTab === 'ask' ? 'active' : ''}`}
          onClick={() => setSubTab('ask')}
        >
          4. Ask &amp; Reports
        </button>
        {user.role === 'ADMIN' && (
          <button
            type="button"
            className={`sub-tab ${subTab === 'config' ? 'active' : ''}`}
            onClick={() => setSubTab('config')}
          >
            5. Categories &amp; Departments (ADMIN)
          </button>
        )}
      </div>

      {/* TAB 1: Operational Inbox & Per-Ticket AI Assistance */}
      {subTab === 'inbox' && (
        <div className="workspace-grid">
          <div className="card">
            <div className="card-header">
              <div>
                <h3 className="card-title">Institution Queue ({tickets.length})</h3>
                <p className="section-subtitle">
                  All active non-archived complaints across the institution.
                </p>
              </div>
              <button type="button" className="btn btn-secondary btn-sm" onClick={loadInbox}>
                Refresh
              </button>
            </div>

            <div className="form-row" style={{ marginBottom: '0.75rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Filter Status</label>
                <select
                  className="form-select"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">All Statuses</option>
                  <option value="SUBMITTED">SUBMITTED</option>
                  <option value="IN_PROGRESS">IN_PROGRESS</option>
                  <option value="RESOLVED">RESOLVED</option>
                  <option value="REJECTED">REJECTED</option>
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Filter Category</label>
                <select
                  className="form-select"
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                >
                  <option value="">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {inboxError && <div className="alert alert-error">{inboxError}</div>}

            {loadingInbox ? (
              <div className="empty-state">Loading tickets...</div>
            ) : tickets.length === 0 ? (
              <div className="empty-state">No complaints match the current filters.</div>
            ) : (
              <div className="ticket-list">
                {tickets.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className={`ticket-item ${selectedId === t.id ? 'selected' : ''}`}
                    onClick={() => setSelectedId(t.id)}
                  >
                    <div className="ticket-item-top">
                      <span className="ticket-number">{t.ticket_number}</span>
                      <div style={{ display: 'flex', gap: '0.35rem' }}>
                        <span className={`badge priority-${t.priority}`}>{t.priority}</span>
                        <span className={`badge status-${t.status}`}>{t.status}</span>
                      </div>
                    </div>
                    <div className="ticket-title">{t.title}</div>
                    <div className="ticket-meta">
                      <span>{t.location}</span>
                      <span>&bull; {getCategoryName(t.category_id)}</span>
                      <span>&bull; {getDepartmentName(t.assigned_department_id)}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <TicketWorkspace
            complaintId={selectedId}
            user={user}
            categories={categories}
            departments={departments}
            locations={locations}
            onTicketUpdated={(updated) => {
              setTickets((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
            }}
            onTicketArchived={(archivedId) => {
              setTickets((prev) => prev.filter((item) => item.id !== archivedId));
              setSelectedId(null);
            }}
          />
        </div>
      )}

      {/* TAB 2: P0 Resolution Analytics */}
      {subTab === 'analytics' && (
        <>
        <CommonIssuesPanel />
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Institution Resolution Analytics</h3>
              <p className="section-subtitle">
                Excludes archived complaints. Counts represent reported ticket volume, not unique
                affected people.
              </p>
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={loadStats}>
              Refresh Analytics
            </button>
          </div>

          {statsError && <div className="alert alert-error">{statsError}</div>}

          {loadingStats && !stats ? (
            <div className="empty-state">Loading analytics...</div>
          ) : stats ? (
            <>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">Total Active Reports</div>
                  <div className="stat-value">{stats.total}</div>
                  <div className="stat-sub">Non-archived volume</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Submitted</div>
                  <div className="stat-value">{stats.submitted}</div>
                  <div className="stat-sub">Awaiting triage / start</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">In Progress</div>
                  <div className="stat-value">{stats.in_progress}</div>
                  <div className="stat-sub">Assigned &amp; active</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Resolved</div>
                  <div className="stat-value">{stats.resolved}</div>
                  <div className="stat-sub">Sample: {stats.resolved_count}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Rejected</div>
                  <div className="stat-value">{stats.rejected}</div>
                  <div className="stat-sub">Closed with note</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Mean Resolution Time</div>
                  <div className="stat-value">
                    {stats.avg_resolution_hours === null || stats.avg_resolution_hours === undefined
                      ? 'N/A'
                      : `${Number(stats.avg_resolution_hours).toFixed(2)}h`}
                  </div>
                  <div className="stat-sub">
                    {stats.resolved_count === 0
                      ? 'No resolved records (null average)'
                      : `Across ${stats.resolved_count} resolved ticket(s)`}
                  </div>
                </div>
              </div>

              <h4 className="card-title" style={{ marginTop: '1.2rem', marginBottom: '0.75rem' }}>
                Ticket Volume by Category
              </h4>
              {Array.isArray(stats.by_category) && stats.by_category.length > 0 ? (
                <div>
                  {stats.by_category.map((row, idx) => {
                    const max = Math.max(...stats.by_category.map((r) => r.count), 1);
                    const pct = Math.round((row.count / max) * 100);
                    return (
                      <div key={idx} className="bar-row">
                        <div className="bar-label-row">
                          <span>
                            <strong>{row.category}</strong>
                          </span>
                          <span>{row.count} ticket(s)</span>
                        </div>
                        <div className="bar-track">
                          <div className="bar-fill" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="section-subtitle">No category counts recorded yet.</div>
              )}
            </>
          ) : null}
        </div>
        </>
      )}

      {/* TAB 3: Optional AI Insights & On-Demand Admin Report */}
      {subTab === 'insights' && (
        <div>
          <div className="card">
            <div className="card-header">
              <div>
                <h3 className="card-title">Cohort Insights &amp; On-Demand Recommendations</h3>
                <p className="section-subtitle">
                  Cohort definition: non-archived complaints with <code>created_at</code> inside the
                  selected UTC date range (inclusive from-date through whole to-date; max 366 days).
                  Counts reflect current status at <code>generated_at</code> and represent reported
                  tickets, not unique students.
                </p>
              </div>
            </div>

            <form
              onSubmit={loadInsights}
              style={{
                display: 'flex',
                gap: '0.75rem',
                alignItems: 'flex-end',
                flexWrap: 'wrap',
                marginBottom: '1rem'
              }}
            >
              <div>
                <label className="form-label">From Date (UTC)</label>
                <input
                  type="date"
                  className="form-input"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="form-label">To Date (UTC)</label>
                <input
                  type="date"
                  className="form-input"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className="btn btn-secondary" disabled={loadingInsights}>
                {loadingInsights ? 'Loading Cohort...' : 'Load Cohort Aggregates'}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={generatingReport}
                onClick={handleGenerateReport}
              >
                {generatingReport ? 'Generating Report...' : 'Generate Recommendations Report'}
              </button>
            </form>

            {insightsError && <div className="alert alert-error">{insightsError}</div>}
            {reportError && <div className="alert alert-error">{reportError}</div>}

            {insights && (
              <>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-label">Cohort Sample Size</div>
                    <div className="stat-value">{insights.sample_size}</div>
                    <div className="stat-sub">
                      {insights.period?.from} to {insights.period?.to}
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Unresolved in Cohort</div>
                    <div className="stat-value">{insights.unresolved}</div>
                    <div className="stat-sub">Submitted + In Progress</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">High-Priority Unresolved</div>
                    <div className="stat-value" style={{ color: 'var(--danger)' }}>
                      {insights.high_priority_unresolved}
                    </div>
                    <div className="stat-sub">Urgent triage signal</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Cohort Mean Resolution</div>
                    <div className="stat-value">
                      {insights.avg_resolution_hours === null ||
                      insights.avg_resolution_hours === undefined
                        ? 'N/A'
                        : `${Number(insights.avg_resolution_hours).toFixed(2)}h`}
                    </div>
                    <div className="stat-sub">Resolved count: {insights.resolved_count}</div>
                  </div>
                </div>

                <div className="form-row" style={{ marginTop: '1rem' }}>
                  {/* Frequent Categories (Separate from Urgency) */}
                  <div
                    style={{
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '6px',
                      padding: '0.85rem'
                    }}
                  >
                    <h4 className="card-title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                      Frequent Issues by Category
                    </h4>
                    {insights.by_category?.length ? (
                      insights.by_category.map((c, i) => (
                        <div
                          key={i}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '0.3rem 0',
                            borderBottom: '1px solid var(--surface-muted)',
                            fontSize: '0.85rem'
                          }}
                        >
                          <span>{c.category}</span>
                          <strong>{c.count} ticket(s)</strong>
                        </div>
                      ))
                    ) : (
                      <div className="section-subtitle">No tickets in selected period.</div>
                    )}
                  </div>

                  {/* Location Hotspots */}
                  <div
                    style={{
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '6px',
                      padding: '0.85rem'
                    }}
                  >
                    <h4 className="card-title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                      Category by Location Hotspots
                    </h4>
                    {insights.by_location?.length ? (
                      insights.by_location.map((loc, i) => (
                        <div
                          key={i}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '0.3rem 0',
                            borderBottom: '1px solid var(--surface-muted)',
                            fontSize: '0.85rem'
                          }}
                        >
                          <span>
                            <strong>{loc.location}</strong> — {loc.category}
                          </span>
                          <strong>{loc.count}</strong>
                        </div>
                      ))
                    ) : (
                      <div className="section-subtitle">No location hotspots in selected period.</div>
                    )}
                  </div>
                </div>

                {/* Urgent & Oldest Unresolved Backlog (Separate Ranking) */}
                <div style={{ marginTop: '1rem' }}>
                  <h4 className="card-title" style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                    Oldest &amp; Urgent Unresolved Backlog (Separate from Frequency)
                  </h4>
                  {insights.oldest_unresolved?.length ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                      {insights.oldest_unresolved.map((item) => (
                        <div
                          key={item.complaint_id}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '0.5rem 0.75rem',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '6px',
                            fontSize: '0.85rem'
                          }}
                        >
                          <div>
                            <span className="ticket-number">{item.ticket_number}</span> &bull;{' '}
                            <strong>{item.location}</strong> &bull; Age:{' '}
                            {Number(item.age_hours).toFixed(1)}h
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <span className={`badge priority-${item.priority}`}>
                              {item.priority}
                            </span>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => {
                                setSelectedId(item.complaint_id);
                                setSubTab('inbox');
                              }}
                            >
                              Open Ticket
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="section-subtitle">No unresolved backlog in this cohort.</div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Generated Admin Report Card */}
          {report && (
            <div className="card">
              <div className="card-header">
                <div>
                  <h3 className="card-title">On-Demand Maintenance &amp; Planning Report</h3>
                  <p className="section-subtitle">
                    Period: {report.period?.from} to {report.period?.to} &bull; Sample Size:{' '}
                    {report.sample_size} &bull; Generated:{' '}
                    {new Date(report.generated_at).toLocaleString()}
                  </p>
                </div>
                <span className="badge source-badge">
                  source: {report.source}{' '}
                  {{ rules: '(Rules-based local synthesis)', nlp: '(NLTK text analysis)' }[report.source] || '(Local model)'}
                </span>
              </div>

              <div
                style={{
                  background: 'var(--primary-soft)',
                  border: '1px solid #bfdbfe',
                  borderRadius: '6px',
                  padding: '0.85rem',
                  marginBottom: '1rem',
                  fontSize: '0.9rem'
                }}
              >
                <strong>Executive Summary:</strong> {report.summary}
              </div>

              <h4 className="card-title" style={{ fontSize: '0.95rem', marginBottom: '0.6rem' }}>
                Evidence-Based Recommendations ({report.recommendations?.length || 0})
              </h4>
              {Array.isArray(report.recommendations) && report.recommendations.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {report.recommendations.map((rec, i) => (
                    <div
                      key={i}
                      style={{
                        border: '1px solid var(--border)',
                        borderRadius: '6px',
                        padding: '0.85rem'
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: '0.5rem',
                          marginBottom: '0.35rem'
                        }}
                      >
                        <strong>{rec.title}</strong>
                        <span
                          className={`badge ${
                            rec.horizon === 'IMMEDIATE' ? 'priority-HIGH' : 'status-SUBMITTED'
                          }`}
                        >
                          Horizon: {rec.horizon}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                        <strong>Supporting Evidence:</strong> {rec.evidence}
                      </div>
                      <div style={{ fontSize: '0.85rem', marginBottom: '0.3rem' }}>
                        <strong>Responsible Department:</strong>{' '}
                        {getDepartmentName(rec.department_id)}
                      </div>
                      <div style={{ fontSize: '0.86rem' }}>
                        <strong>Next Step:</strong> {rec.next_step}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="section-subtitle">
                  No recommendations generated (insufficient complaint volume in this period).
                </div>
              )}

              <h4 className="card-title" style={{ fontSize: '0.95rem', margin: '1rem 0 0.6rem' }}>
                Common Issues From Complaint Descriptions ({report.common_issues?.length || 0})
              </h4>
              <CommonIssueList issues={report.common_issues} />
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Admin Categories & Departments Configuration */}
      {/* TAB 4: Admin chatbox questions -> editable report table */}
      {subTab === 'ask' && <AdminQueryChat categories={categories} departments={departments} />}

      {subTab === 'config' && user.role === 'ADMIN' && (
        <div className="form-row">
          {/* Departments Management */}
          <div className="card">
            <h3 className="card-title" style={{ marginBottom: '0.3rem' }}>
              Departments ({departments.length})
            </h3>
            <p className="section-subtitle" style={{ marginBottom: '0.85rem' }}>
              Deactivating preserves historical ticket references.
            </p>

            {configError && <div className="alert alert-error">{configError}</div>}
            {configMsg && <div className="alert alert-success">{configMsg}</div>}

            <form onSubmit={handleCreateDept} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <input
                className="form-input"
                placeholder="New department name (e.g. IT Services)"
                value={newDeptName}
                onChange={(e) => setNewDeptName(e.target.value)}
                maxLength={100}
                required
              />
              <button type="submit" className="btn btn-primary">
                Add
              </button>
            </form>

            {editDeptId && (
              <form
                onSubmit={handleUpdateDept}
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  marginBottom: '1rem',
                  padding: '0.6rem',
                  background: 'var(--surface-muted)',
                  borderRadius: '6px'
                }}
              >
                <input
                  className="form-input"
                  value={editDeptName}
                  onChange={(e) => setEditDeptName(e.target.value)}
                  maxLength={100}
                  required
                />
                <button type="submit" className="btn btn-primary btn-sm">
                  Save
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setEditDeptId(null)}
                >
                  Cancel
                </button>
              </form>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {departments.map((d) => (
                <div
                  key={d.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.5rem 0.65rem',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px'
                  }}
                >
                  <div>
                    <strong>{d.name}</strong>{' '}
                    <span className="section-subtitle">(ID #{d.id})</span>
                  </div>
                  <div className="btn-group">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setEditDeptId(d.id);
                        setEditDeptName(d.name);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDeactivateDept(d.id, d.name)}
                    >
                      Deactivate
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Categories Management */}
          <div className="card">
            <h3 className="card-title" style={{ marginBottom: '0.3rem' }}>
              Categories &amp; Routing Rules ({categories.length})
            </h3>
            <p className="section-subtitle" style={{ marginBottom: '0.85rem' }}>
              Configured default departments automatically route new or recategorized tickets.
            </p>

            <form onSubmit={handleCreateCat} style={{ marginBottom: '1rem' }}>
              <div className="form-row" style={{ marginBottom: '0.5rem' }}>
                <input
                  className="form-input"
                  placeholder="New category name (e.g. Wi-Fi)"
                  value={newCatName}
                  onChange={(e) => setNewCatName(e.target.value)}
                  maxLength={100}
                  required
                />
                <select
                  className="form-select"
                  value={newCatDeptId}
                  onChange={(e) => setNewCatDeptId(e.target.value)}
                >
                  <option value="">-- No Default Department (Review) --</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      Route to: {d.name}
                    </option>
                  ))}
                </select>
              </div>
              <button type="submit" className="btn btn-primary btn-sm">
                Add Category
              </button>
            </form>

            {editCatId && (
              <form
                onSubmit={handleUpdateCat}
                style={{
                  marginBottom: '1rem',
                  padding: '0.65rem',
                  background: 'var(--surface-muted)',
                  borderRadius: '6px'
                }}
              >
                <div className="form-row" style={{ marginBottom: '0.5rem' }}>
                  <input
                    className="form-input"
                    value={editCatName}
                    onChange={(e) => setEditCatName(e.target.value)}
                    maxLength={100}
                    required
                  />
                  <select
                    className="form-select"
                    value={editCatDeptId}
                    onChange={(e) => setEditCatDeptId(e.target.value)}
                  >
                    <option value="">-- No Default Department --</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        Route to: {d.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="btn-group">
                  <button type="submit" className="btn btn-primary btn-sm">
                    Save Category
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setEditCatId(null)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {categories.map((c) => (
                <div
                  key={c.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.5rem 0.65rem',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px'
                  }}
                >
                  <div>
                    <strong>{c.name}</strong>{' '}
                    <span className="section-subtitle">
                      &rarr; {getDepartmentName(c.default_department_id)}
                    </span>
                  </div>
                  <div className="btn-group">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setEditCatId(c.id);
                        setEditCatName(c.name);
                        setEditCatDeptId(
                          c.default_department_id ? String(c.default_department_id) : ''
                        );
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDeactivateCat(c.id, c.name)}
                    >
                      Deactivate
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
