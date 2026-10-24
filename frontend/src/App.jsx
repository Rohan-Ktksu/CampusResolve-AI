import React, { useState, useEffect } from 'react';
import {
  api,
  getStoredToken,
  getStoredUser,
  setStoredSession,
  clearStoredSession,
  setUnauthorizedHandler
} from './api.js';
import TicketWorkspace from './components/TicketWorkspace.jsx';
import AdminDashboard from './components/AdminDashboard.jsx';

const MAX_IMAGE_BYTES = 5 * 1024 * 1024; // 5 MiB

const SEEDED_DEMO_ACCOUNTS = [
  { label: 'Student 1', email: 'student@demo.edu', role: 'STUDENT' },
  { label: 'Student 2', email: 'student2@demo.edu', role: 'STUDENT' },
  { label: 'IT Staff', email: 'it.staff@demo.edu', role: 'STAFF (IT)' },
  { label: 'Facilities Staff', email: 'facilities.staff@demo.edu', role: 'STAFF (Facilities)' },
  { label: 'Coordinator', email: 'coordinator@demo.edu', role: 'COORDINATOR' },
  { label: 'Admin', email: 'admin@demo.edu', role: 'ADMIN' }
];

export default function App() {
  const [pathname, setPathname] = useState(window.location.pathname);
  const [search, setSearch] = useState(window.location.search);

  const isEmbed = new URLSearchParams(search).get('embed') === '1';
  const isDemoPortal = pathname === '/demo-portal';

  // Auth & context state
  const [user, setUser] = useState(() => getStoredUser());
  const [authChecking, setAuthChecking] = useState(Boolean(getStoredToken()));
  const [authMessage, setAuthMessage] = useState('');

  // Login form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Institution & configuration lookups
  const [institution, setInstitution] = useState(null);
  const [categories, setCategories] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [locations, setLocations] = useState([]);
  const [lookupError, setLookupError] = useState('');

  // Navigation tab: 'report' | 'my_complaints' | 'dept_queue' | 'admin_dashboard' | 'wireframe'
  const [activeTab, setActiveTab] = useState('my_complaints');

  // Report Issue Form state (STUDENT / STAFF)
  const [repTitle, setRepTitle] = useState('');
  const [repLocation, setRepLocation] = useState('');
  const [repCategoryId, setRepCategoryId] = useState('');
  const [repDesc, setRepDesc] = useState('');
  const [repFile, setRepFile] = useState(null);
  const [submittingReport, setSubmittingReport] = useState(false);
  const [reportError, setReportError] = useState('');
  const [reportSuccess, setReportSuccess] = useState('');

  // My Complaints / Staff Department Queue list state
  const [tickets, setTickets] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [ticketsError, setTicketsError] = useState('');
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [pendingRetryMap, setPendingRetryMap] = useState({});

  useEffect(() => {
    const onPopState = () => {
      setPathname(window.location.pathname);
      setSearch(window.location.search);
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler((msg) => {
      setUser(null);
      setAuthMessage(msg || 'Session expired. Please sign in again.');
    });
  }, []);

  // Verify token on initial load
  useEffect(() => {
    if (isDemoPortal) return;
    const token = getStoredToken();
    if (!token) {
      setAuthChecking(false);
      return;
    }
    setAuthChecking(true);
    api
      .getMe()
      .then((verifiedUser) => {
        setStoredSession(token, verifiedUser);
        setUser(verifiedUser);
        chooseDefaultTab(verifiedUser);
      })
      .catch(() => {
        clearStoredSession();
        setUser(null);
      })
      .finally(() => {
        setAuthChecking(false);
      });
  }, [isDemoPortal]);

  // Load institution, categories, departments, locations when authenticated
  useEffect(() => {
    if (!user || isDemoPortal) return;
    loadLookups();
  }, [user, isDemoPortal]);

  // Reload tickets when switching to my_complaints or dept_queue
  useEffect(() => {
    if (!user || isDemoPortal) return;
    if (activeTab === 'my_complaints' || activeTab === 'dept_queue') {
      loadRoleTickets();
    }
  }, [user, activeTab, statusFilter, categoryFilter, isDemoPortal]);

  function navigateTo(nextPath, nextSearch = '') {
    window.history.pushState({}, '', `${nextPath}${nextSearch}`);
    setPathname(nextPath);
    setSearch(nextSearch);
  }

  function chooseDefaultTab(u) {
    if (!u) return;
    if (u.role === 'ADMIN' || u.role === 'COORDINATOR') {
      setActiveTab('admin_dashboard');
    } else if (u.role === 'STAFF') {
      setActiveTab('dept_queue');
    } else {
      setActiveTab('my_complaints');
    }
  }

  async function loadLookups() {
    setLookupError('');
    try {
      const [inst, cats, depts, locs] = await Promise.all([
        api.getCurrentInstitution(),
        api.getCategories(),
        api.getDepartments(),
        api.getLocations()
      ]);
      setInstitution(inst);
      setCategories(Array.isArray(cats) ? cats : []);
      setDepartments(Array.isArray(depts) ? depts : []);
      const locList = Array.isArray(locs) ? locs : [];
      setLocations(locList);
      if (locList.length > 0 && !repLocation) {
        setRepLocation(locList[0].name);
      }
    } catch (err) {
      setLookupError(err.message || 'Could not load institution configuration.');
    }
  }

  async function loadRoleTickets() {
    setLoadingTickets(true);
    setTicketsError('');
    try {
      const isMineTab = activeTab === 'my_complaints';
      const list = await api.getComplaints({
        status: statusFilter || undefined,
        category_id: categoryFilter ? Number(categoryFilter) : undefined,
        mine: isMineTab ? true : undefined
      });
      let filtered = Array.isArray(list) ? list : [];
      if (activeTab === 'dept_queue' && user.role === 'STAFF') {
        filtered = filtered.filter(
          (t) =>
            t.assigned_department_id === user.department_id &&
            (t.assigned_user_id === null || t.assigned_user_id === user.id)
        );
      }
      setTickets(filtered);
      if (filtered.length > 0 && (!selectedTicketId || !filtered.some((t) => t.id === selectedTicketId))) {
        setSelectedTicketId(filtered[0].id);
      } else if (filtered.length === 0) {
        setSelectedTicketId(null);
      }
    } catch (err) {
      setTicketsError(err.message || 'Failed to load tickets.');
    } finally {
      setLoadingTickets(false);
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');
    setAuthMessage('');
    try {
      const res = await api.login(email.trim(), password);
      setStoredSession(res.access_token, res.user);
      setUser(res.user);
      chooseDefaultTab(res.user);
      setPassword('');
    } catch (err) {
      setLoginError(err.message || 'Invalid credentials or backend unreachable.');
    } finally {
      setLoginLoading(false);
    }
  }

  function handleLogout() {
    clearStoredSession();
    setUser(null);
    setInstitution(null);
    setTickets([]);
    setSelectedTicketId(null);
    setAuthMessage('Signed out.');
  }

  async function handleCreateComplaint(e) {
    e.preventDefault();
    setReportError('');
    setReportSuccess('');

    if (repFile) {
      if (!['image/jpeg', 'image/png'].includes(repFile.type)) {
        setReportError('Attachment must be a valid JPEG or PNG image.');
        return;
      }
      if (repFile.size > MAX_IMAGE_BYTES) {
        setReportError('Image attachment cannot exceed 5 MiB.');
        return;
      }
    }

    setSubmittingReport(true);
    try {
      const created = await api.createComplaint({
        title: repTitle.trim(),
        description: repDesc.trim(),
        location: repLocation.trim(),
        category_id: repCategoryId ? Number(repCategoryId) : null
      });

      let finalTicket = created;
      let uploadFailedFile = null;

      if (repFile) {
        try {
          finalTicket = await api.uploadComplaintImage(created.id, repFile);
        } catch (uploadErr) {
          uploadFailedFile = repFile;
          setPendingRetryMap((prev) => ({ ...prev, [created.id]: repFile }));
        }
      }

      setRepTitle('');
      setRepDesc('');
      setRepCategoryId('');
      setRepFile(null);

      setSelectedTicketId(finalTicket.id);
      setActiveTab('my_complaints');

      if (uploadFailedFile) {
        setReportSuccess(
          `Ticket ${finalTicket.ticket_number} saved in PostgreSQL, but image upload failed. You can retry on the ticket detail panel.`
        );
      } else {
        setReportSuccess(`Ticket ${finalTicket.ticket_number} submitted!`);
      }
    } catch (err) {
      setReportError(err.message || 'Could not submit complaint.');
    } finally {
      setSubmittingReport(false);
    }
  }

  function getCategoryName(catId) {
    if (!catId) return 'Uncategorized';
    const found = categories.find((c) => c.id === catId);
    return found ? found.name : `Category #${catId}`;
  }

  function getDepartmentName(deptId) {
    if (!deptId) return 'Unassigned / Review';
    const found = departments.find((d) => d.id === deptId);
    return found ? found.name : `Dept #${deptId}`;
  }

  // Fictional College Portal wrapper (/demo-portal) embedding /app?embed=1
  if (isDemoPortal) {
    return (
      <div className="app-shell">
        <div className="portal-banner">
          <div>
            <strong>Fictional College Student &amp; Staff Portal (Prototype Demo)</strong> — Same-origin
            iframe embedding <code>/app?embed=1</code> against the shared FastAPI + PostgreSQL
            backend. Real college ERP/SSO integration is future work.
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => navigateTo('/app', '')}
          >
            Exit to Standalone /app
          </button>
        </div>
        <div className="main-container" style={{ paddingTop: '0.75rem' }}>
          <iframe
            className="portal-iframe"
            src="/app?embed=1"
            title="CampusResolve AI Embedded Workspace"
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`app-shell ${isEmbed ? 'embed-mode' : ''}`}>
      {/* Header */}
      <header className="topbar">
        <div className="brand-group">
          <h1 className="brand-title">
            CampusResolve AI {isEmbed ? '(Embedded Portal View)' : ''}
          </h1>
          {institution && (
            <span className="inst-badge" title={`Institution Code: ${institution.code}`}>
              {institution.name} ({institution.code})
            </span>
          )}
        </div>

        <div className="user-controls">
          {!isEmbed && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => navigateTo('/demo-portal', '')}
            >
              Open /demo-portal Iframe
            </button>
          )}
          {user && (
            <>
              <span className="user-pill">
                {user.name}
                <span className="role-tag">{user.role}</span>
                {user.department_id ? ` • Dept #${user.department_id}` : ''}
              </span>
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleLogout}>
                Sign Out
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main Content */}
      {authChecking ? (
        <div className="main-container">
          <div className="card empty-state">Verifying session...</div>
        </div>
      ) : !user ? (
        <div className="login-wrapper">
          <div className="card">
            <h2 className="card-title" style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>
              Sign in to CampusResolve AI
            </h2>
            <p className="section-subtitle" style={{ marginBottom: '1rem' }}>
              Authenticate with your seeded institution account. Role and permissions are verified
              on the backend.
            </p>

            {authMessage && <div className="alert alert-info">{authMessage}</div>}
            {loginError && <div className="alert alert-error">{loginError}</div>}

            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="student@campus.edu"
                  maxLength={254}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="form-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  maxLength={256}
                  required
                />
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={loginLoading}
              >
                {loginLoading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            <div
              style={{
                marginTop: '1.1rem',
                paddingTop: '0.85rem',
                borderTop: '1px solid var(--border-subtle)',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)'
              }}
            >
              <div style={{ marginBottom: '0.45rem', fontWeight: 600 }}>
                Quick-Fill Seeded Prototype Accounts (Institution: DEMO, Password: <code>demo1234</code>):
              </div>
              <div className="btn-group" style={{ marginBottom: '0.85rem' }}>
                {SEEDED_DEMO_ACCOUNTS.map((acct) => (
                  <button
                    key={acct.email}
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setEmail(acct.email);
                      setPassword('demo1234');
                    }}
                  >
                    {acct.label}
                  </button>
                ))}
              </div>
              <div style={{ marginBottom: '0.4rem', fontWeight: 600 }}>
                Need the Figma Wireframe Sketch?
              </div>
              <a
                href="/wireframe.svg"
                target="_blank"
                rel="noreferrer"
                className="btn btn-secondary btn-sm"
              >
                View Wireframe Diagram (/wireframe.svg)
              </a>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Role-Aware Navigation Tabs */}
          <nav className="nav-tabs">
            {(user.role === 'STUDENT' || user.role === 'STAFF') && (
              <>
                <button
                  type="button"
                  className={`nav-tab ${activeTab === 'report' ? 'active' : ''}`}
                  onClick={() => setActiveTab('report')}
                >
                  + Report Issue
                </button>
                <button
                  type="button"
                  className={`nav-tab ${activeTab === 'my_complaints' ? 'active' : ''}`}
                  onClick={() => setActiveTab('my_complaints')}
                >
                  My Complaints
                </button>
              </>
            )}

            {user.role === 'STAFF' && (
              <button
                type="button"
                className={`nav-tab ${activeTab === 'dept_queue' ? 'active' : ''}`}
                onClick={() => setActiveTab('dept_queue')}
              >
                Department Queue
              </button>
            )}

            {(user.role === 'ADMIN' || user.role === 'COORDINATOR') && (
              <button
                type="button"
                className={`nav-tab ${activeTab === 'admin_dashboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('admin_dashboard')}
              >
                Admin Dashboard (Queue, Analytics &amp; AI)
              </button>
            )}

            <button
              type="button"
              className={`nav-tab ${activeTab === 'wireframe' ? 'active' : ''}`}
              onClick={() => setActiveTab('wireframe')}
            >
              Figma Wireframe
            </button>
          </nav>

          <main className="main-container">
            {lookupError && <div className="alert alert-error">{lookupError}</div>}
            {reportSuccess && (
              <div className="alert alert-success">
                <span>{reportSuccess}</span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setReportSuccess('')}
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* SCREEN 1: Report Issue (STUDENT & STAFF) */}
            {activeTab === 'report' && (user.role === 'STUDENT' || user.role === 'STAFF') && (
              <div className="card" style={{ maxWidth: '720px', margin: '0 auto' }}>
                <h2 className="card-title">Submit a Campus Issue Report</h2>
                <p className="section-subtitle" style={{ marginBottom: '1rem' }}>
                  Both students and staff can report campus issues. Selecting a category applies
                  configured departmental routing; leaving it blank routes your ticket to admin
                  review.
                </p>

                {reportError && <div className="alert alert-error">{reportError}</div>}

                <form onSubmit={handleCreateComplaint}>
                  <div className="form-group">
                    <label className="form-label">Issue Title (Required, 1–160 chars)</label>
                    <input
                      className="form-input"
                      placeholder="e.g., Wi-Fi unavailable during lab session"
                      value={repTitle}
                      onChange={(e) => setRepTitle(e.target.value)}
                      maxLength={160}
                      required
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Campus Location (Required)</label>
                      <select
                        className="form-select"
                        value={repLocation}
                        onChange={(e) => setRepLocation(e.target.value)}
                        required
                      >
                        <option value="">-- Select Canonical Campus Location --</option>
                        {locations.map((loc) => (
                          <option key={loc.id} value={loc.name}>
                            {loc.name}
                          </option>
                        ))}
                      </select>
                      <span className="form-hint">
                        Uses canonical seeded campus locations from GET /api/v1/locations.
                      </span>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Category (Optional)</label>
                      <select
                        className="form-select"
                        value={repCategoryId}
                        onChange={(e) => setRepCategoryId(e.target.value)}
                      >
                        <option value="">-- Uncategorized (Route to Admin Review) --</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}{' '}
                            {c.default_department_id
                              ? `(Routes to ${getDepartmentName(c.default_department_id)})`
                              : '(Review)'}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Detailed Description (Required, up to 5000 chars)</label>
                    <textarea
                      className="form-textarea"
                      placeholder="Describe what is happening, which room/equipment is affected, and any safety or class impact..."
                      value={repDesc}
                      onChange={(e) => setRepDesc(e.target.value)}
                      maxLength={5000}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      Optional Photo Attachment (JPEG or PNG, max 5 MiB)
                    </label>
                    <input
                      type="file"
                      accept="image/jpeg,image/png"
                      onChange={(e) => setRepFile(e.target.files?.[0] || null)}
                    />
                    <span className="form-hint">
                      Your ticket is created first; if the image upload fails, your ticket stays
                      saved and you can retry the upload from the ticket view.
                    </span>
                  </div>

                  <div className="btn-group">
                    <button type="submit" className="btn btn-primary" disabled={submittingReport}>
                      {submittingReport ? 'Submitting Ticket...' : 'Submit Issue Report'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setActiveTab('my_complaints')}
                    >
                      View My Complaints
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* SCREEN 2 & 3: My Complaints (STUDENT/STAFF) & Department Queue (STAFF) */}
            {(activeTab === 'my_complaints' || activeTab === 'dept_queue') && (
              <div className="workspace-grid">
                <div className="card">
                  <div className="card-header">
                    <div>
                      <h3 className="card-title">
                        {activeTab === 'my_complaints'
                          ? `My Reported Complaints (${tickets.length})`
                          : `Department Operational Queue (${tickets.length})`}
                      </h3>
                      <p className="section-subtitle">
                        {activeTab === 'my_complaints'
                          ? 'Issues you personally submitted as a reporter.'
                          : `Tickets assigned to your department (Dept #${user.department_id || 'None'}) and unassigned or assigned to you.`}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={loadRoleTickets}
                    >
                      Refresh
                    </button>
                  </div>

                  <div className="form-row" style={{ marginBottom: '0.75rem' }}>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label className="form-label">Status</label>
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
                      <label className="form-label">Category</label>
                      <select
                        className="form-select"
                        value={categoryFilter}
                        onChange={(e) => setCategoryFilter(e.target.value)}
                      >
                        <option value="">All Categories</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {ticketsError && <div className="alert alert-error">{ticketsError}</div>}

                  {loadingTickets ? (
                    <div className="empty-state">Loading tickets...</div>
                  ) : tickets.length === 0 ? (
                    <div className="empty-state">
                      {activeTab === 'my_complaints'
                        ? 'You have not submitted any complaints matching these filters yet.'
                        : 'No departmental queue tickets match these filters.'}
                    </div>
                  ) : (
                    <div className="ticket-list">
                      {tickets.map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          className={`ticket-item ${selectedTicketId === t.id ? 'selected' : ''}`}
                          onClick={() => setSelectedTicketId(t.id)}
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
                  complaintId={selectedTicketId}
                  user={user}
                  categories={categories}
                  departments={departments}
                  locations={locations}
                  pendingRetryFile={selectedTicketId ? pendingRetryMap[selectedTicketId] : null}
                  onClearPendingRetry={() => {
                    if (!selectedTicketId) return;
                    setPendingRetryMap((prev) => {
                      const next = { ...prev };
                      delete next[selectedTicketId];
                      return next;
                    });
                  }}
                  onTicketUpdated={(updated) => {
                    setTickets((prev) =>
                      prev.map((item) => (item.id === updated.id ? updated : item))
                    );
                  }}
                />
              </div>
            )}

            {/* SCREEN 4: Single Admin Dashboard (ADMIN / COORDINATOR) */}
            {activeTab === 'admin_dashboard' &&
              (user.role === 'ADMIN' || user.role === 'COORDINATOR') && (
                <AdminDashboard
                  user={user}
                  categories={categories}
                  departments={departments}
                  locations={locations}
                  onConfigChanged={loadLookups}
                />
              )}

            {/* Wireframe Reference View */}
            {activeTab === 'wireframe' && (
              <div className="card">
                <div className="card-header">
                  <div>
                    <h3 className="card-title">Figma Wireframe &amp; Screen Flow</h3>
                    <p className="section-subtitle">
                      Visual layout specification for Reporter, Staff Queue, and Single Admin
                      Dashboard (`frontend/FIGMA_WIREFRAME.md`).
                    </p>
                  </div>
                </div>
                <div className="image-frame">
                  <img src="/wireframe.svg" alt="CampusResolve AI Figma Wireframe" />
                </div>
              </div>
            )}
          </main>
        </>
      )}
    </div>
  );
}
