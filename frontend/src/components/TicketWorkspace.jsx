import React, { useState, useEffect } from 'react';
import { api } from '../api.js';

const MAX_IMAGE_BYTES = 5 * 1024 * 1024; // 5 MiB

export default function TicketWorkspace({
  complaintId,
  user,
  categories,
  departments,
  locations,
  pendingRetryFile,
  onClearPendingRetry,
  onTicketUpdated,
  onTicketArchived
}) {
  const [complaint, setComplaint] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  // Image state
  const [imageBlobUrl, setImageBlobUrl] = useState('');
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);

  // Reporter edit state (while SUBMITTED)
  const [editingDetails, setEditingDetails] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editLocation, setEditLocation] = useState('');
  const [editCategoryId, setEditCategoryId] = useState('');
  const [savingDetails, setSavingDetails] = useState(false);

  // Admin/Coordinator triage & assignment state
  const [triageCategoryId, setTriageCategoryId] = useState('');
  const [triagePriority, setTriagePriority] = useState('NORMAL');
  const [savingTriage, setSavingTriage] = useState(false);

  const [assignDeptId, setAssignDeptId] = useState('');
  const [assignUserId, setAssignUserId] = useState('');
  const [deptStaff, setDeptStaff] = useState([]);
  const [loadingStaff, setLoadingStaff] = useState(false);
  const [savingAssign, setSavingAssign] = useState(false);

  // Per-ticket AI assistance state
  const [aiResult, setAiResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiError, setAiError] = useState('');

  // Status update state
  const [nextStatus, setNextStatus] = useState('');
  const [statusNote, setStatusNote] = useState('');
  const [staffVerified, setStaffVerified] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);

  // Feedback state (original reporter on RESOLVED ticket)
  const [feedback, setFeedback] = useState(null);
  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [loadingFeedback, setLoadingFeedback] = useState(false);
  const [savingFeedback, setSavingFeedback] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState('');

  const isAdminOrCoord = user.role === 'ADMIN' || user.role === 'COORDINATOR';
  const isReporter = complaint && user.id === complaint.reporter_user_id;
  const isNonTerminal =
    complaint && (complaint.status === 'SUBMITTED' || complaint.status === 'IN_PROGRESS');
  const canStaffOperate =
    complaint &&
    (isAdminOrCoord ||
      (user.role === 'STAFF' &&
        user.department_id &&
        complaint.assigned_department_id === user.department_id &&
        (complaint.assigned_user_id === null || complaint.assigned_user_id === user.id)));

  useEffect(() => {
    if (!complaintId) {
      setComplaint(null);
      setHistory([]);
      return;
    }
    let active = true;
    loadFullTicket(complaintId, () => active);
    return () => {
      active = false;
    };
  }, [complaintId]);

  useEffect(() => {
    if (pendingRetryFile) {
      setSelectedFile(pendingRetryFile);
    }
  }, [pendingRetryFile]);

  // Clean up object URL when changed or unmounted
  useEffect(() => {
    return () => {
      if (imageBlobUrl) {
        URL.revokeObjectURL(imageBlobUrl);
      }
    };
  }, [imageBlobUrl]);

  async function loadFullTicket(id, isActive = () => true) {
    setLoading(true);
    setError('');
    setActionMsg('');
    setAiResult(null);
    setAiError('');
    setEditingDetails(false);
    try {
      const [cData, hData] = await Promise.all([
        api.getComplaint(id),
        api.getComplaintHistory(id)
      ]);
      if (!isActive()) return;
      syncComplaintFields(cData);
      setHistory(Array.isArray(hData) ? hData : []);

      if (cData.image_url) {
        loadAuthorizedImage(id);
      } else {
        if (imageBlobUrl) URL.revokeObjectURL(imageBlobUrl);
        setImageBlobUrl('');
      }

      if (cData.status === 'RESOLVED' && user.id === cData.reporter_user_id) {
        loadReporterFeedback(id);
      } else {
        setFeedback(null);
      }
    } catch (err) {
      if (!isActive()) return;
      setError(err.message || 'Could not load ticket details.');
    } finally {
      if (isActive()) setLoading(false);
    }
  }

  function syncComplaintFields(cData) {
    setComplaint(cData);
    setEditTitle(cData.title || '');
    setEditDesc(cData.description || '');
    setEditLocation(cData.location || '');
    setEditCategoryId(cData.category_id ? String(cData.category_id) : '');

    setTriageCategoryId(cData.category_id ? String(cData.category_id) : '');
    setTriagePriority(cData.priority || 'NORMAL');

    const deptStr = cData.assigned_department_id ? String(cData.assigned_department_id) : '';
    setAssignDeptId(deptStr);
    setAssignUserId(cData.assigned_user_id ? String(cData.assigned_user_id) : '');

    if (cData.status === 'SUBMITTED') {
      setNextStatus('IN_PROGRESS');
    } else if (cData.status === 'IN_PROGRESS') {
      setNextStatus('RESOLVED');
    } else {
      setNextStatus('');
    }
    setStatusNote('');
    setStaffVerified(false);
  }

  // Load departmental staff whenever assignDeptId changes for ADMIN/COORDINATOR
  useEffect(() => {
    if (!isAdminOrCoord || !assignDeptId) {
      setDeptStaff([]);
      return;
    }
    let active = true;
    setLoadingStaff(true);
    api
      .getStaff(Number(assignDeptId))
      .then((list) => {
        if (active) setDeptStaff(Array.isArray(list) ? list : []);
      })
      .catch(() => {
        if (active) setDeptStaff([]);
      })
      .finally(() => {
        if (active) setLoadingStaff(false);
      });
    return () => {
      active = false;
    };
  }, [assignDeptId, isAdminOrCoord]);

  async function loadAuthorizedImage(id) {
    setImageLoading(true);
    setImageError('');
    try {
      const url = await api.fetchComplaintImageBlobUrl(id);
      setImageBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return url;
      });
    } catch (err) {
      setImageError(err.message || 'Could not fetch authorized image.');
    } finally {
      setImageLoading(false);
    }
  }

  async function loadReporterFeedback(id) {
    setLoadingFeedback(true);
    setFeedbackMsg('');
    try {
      const fb = await api.getFeedback(id);
      setFeedback(fb);
      setFeedbackRating(fb.rating || 5);
      setFeedbackComment(fb.comment || '');
    } catch (err) {
      if (err.status === 404) {
        setFeedback(null);
        setFeedbackRating(5);
        setFeedbackComment('');
      } else {
        setFeedbackMsg(err.message || 'Failed to load feedback.');
      }
    } finally {
      setLoadingFeedback(false);
    }
  }

  async function refreshHistory(id) {
    try {
      const hData = await api.getComplaintHistory(id);
      setHistory(Array.isArray(hData) ? hData : []);
    } catch {
      // keep existing history
    }
  }

  async function handleReporterSaveDetails(e) {
    e.preventDefault();
    setSavingDetails(true);
    setError('');
    setActionMsg('');
    try {
      const updated = await api.updateComplaint(complaint.id, {
        title: editTitle.trim(),
        description: editDesc.trim(),
        location: editLocation.trim(),
        category_id: editCategoryId ? Number(editCategoryId) : null
      });
      syncComplaintFields(updated);
      setEditingDetails(false);
      setActionMsg('Complaint details updated.');
      await refreshHistory(complaint.id);
      if (onTicketUpdated) onTicketUpdated(updated);
    } catch (err) {
      setError(err.message || 'Failed to update complaint.');
    } finally {
      setSavingDetails(false);
    }
  }

  async function handleImageUpload(fileToUpload) {
    const file = fileToUpload || selectedFile;
    if (!file) {
      setImageError('Please select a JPEG or PNG file first.');
      return;
    }
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setImageError('Only JPEG and PNG images are allowed.');
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setImageError('Image exceeds maximum size of 5 MiB.');
      return;
    }

    setUploadingImage(true);
    setImageError('');
    setActionMsg('');
    try {
      const updated = await api.uploadComplaintImage(complaint.id, file);
      syncComplaintFields(updated);
      setSelectedFile(null);
      if (onClearPendingRetry) onClearPendingRetry();
      setActionMsg('Image uploaded and verified.');
      await loadAuthorizedImage(complaint.id);
      if (onTicketUpdated) onTicketUpdated(updated);
    } catch (err) {
      setImageError(
        `Upload failed: ${err.message || 'Server error'}. Ticket is saved — you can retry upload below.`
      );
    } finally {
      setUploadingImage(false);
    }
  }

  async function handleAdminTriageSave(e) {
    e.preventDefault();
    setSavingTriage(true);
    setError('');
    setActionMsg('');
    try {
      const updated = await api.updateComplaint(complaint.id, {
        category_id: triageCategoryId ? Number(triageCategoryId) : null,
        priority: triagePriority
      });
      syncComplaintFields(updated);
      setActionMsg('Category and priority updated.');
      await refreshHistory(complaint.id);
      if (onTicketUpdated) onTicketUpdated(updated);
    } catch (err) {
      setError(err.message || 'Failed to update category/priority.');
    } finally {
      setSavingTriage(false);
    }
  }

  async function handleAssignSubmit(e) {
    e.preventDefault();
    if (!assignDeptId) {
      setError('Department is required for assignment.');
      return;
    }
    setSavingAssign(true);
    setError('');
    setActionMsg('');
    try {
      const updated = await api.assignComplaint(complaint.id, {
        department_id: Number(assignDeptId),
        assigned_user_id: assignUserId ? Number(assignUserId) : null
      });
      syncComplaintFields(updated);
      setActionMsg('Department assignment saved.');
      await refreshHistory(complaint.id);
      if (onTicketUpdated) onTicketUpdated(updated);
    } catch (err) {
      setError(err.message || 'Assignment failed.');
    } finally {
      setSavingAssign(false);
    }
  }

  async function handleStatusSubmit(e) {
    e.preventDefault();
    if (!nextStatus) return;
    if (nextStatus === 'IN_PROGRESS' && !complaint.assigned_department_id) {
      setError('A department must be assigned before moving to IN_PROGRESS.');
      return;
    }
    if ((nextStatus === 'RESOLVED' || nextStatus === 'REJECTED') && !statusNote.trim()) {
      setError(`An outcome note is required when marking a ticket ${nextStatus}.`);
      return;
    }
    if (nextStatus === 'RESOLVED' && !staffVerified) {
      setError('Please confirm staff verification of actual resolution work before resolving.');
      return;
    }

    setSavingStatus(true);
    setError('');
    setActionMsg('');
    try {
      const payload = { status: nextStatus };
      if (statusNote.trim()) payload.note = statusNote.trim();
      const updated = await api.changeComplaintStatus(complaint.id, payload);
      syncComplaintFields(updated);
      setActionMsg(`Status updated to ${updated.status}.`);
      await refreshHistory(complaint.id);
      if (updated.status === 'RESOLVED' && user.id === updated.reporter_user_id) {
        loadReporterFeedback(updated.id);
      }
      if (onTicketUpdated) onTicketUpdated(updated);
    } catch (err) {
      setError(err.message || 'Failed to change status.');
    } finally {
      setSavingStatus(false);
    }
  }

  async function handleRunAiAnalyze() {
    setAnalyzing(true);
    setAiError('');
    try {
      const res = await api.analyzeComplaint(complaint.id);
      setAiResult(res);
    } catch (err) {
      setAiError(err.message || 'AI triage analysis unavailable.');
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleApplyAiCategoryPriority() {
    if (!aiResult) return;
    setSavingTriage(true);
    setError('');
    setActionMsg('');
    try {
      const body = { priority: aiResult.priority || triagePriority };
      if (aiResult.category_id !== undefined) {
        body.category_id = aiResult.category_id;
      }
      const updated = await api.updateComplaint(complaint.id, body);
      syncComplaintFields(updated);
      setActionMsg('Applied suggested category/priority via authorized PATCH.');
      await refreshHistory(complaint.id);
      if (onTicketUpdated) onTicketUpdated(updated);
    } catch (err) {
      setError(err.message || 'Could not apply suggestion.');
    } finally {
      setSavingTriage(false);
    }
  }

  function handlePrefillAiDepartment() {
    if (!aiResult || !aiResult.suggested_department_id) return;
    setAssignDeptId(String(aiResult.suggested_department_id));
    setAssignUserId('');
    setActionMsg('Pre-filled suggested department below. Review and click Save Assignment.');
  }

  async function handleArchive() {
    if (!window.confirm(`Archive ticket ${complaint.ticket_number}? History is preserved.`)) {
      return;
    }
    setError('');
    try {
      await api.archiveComplaint(complaint.id);
      if (onTicketArchived) onTicketArchived(complaint.id);
    } catch (err) {
      setError(err.message || 'Failed to archive ticket.');
    }
  }

  async function handleFeedbackSubmit(e) {
    e.preventDefault();
    setSavingFeedback(true);
    setFeedbackMsg('');
    try {
      const payload = {
        rating: Number(feedbackRating),
        comment: feedbackComment.trim()
      };
      const saved = feedback
        ? await api.updateFeedback(complaint.id, payload)
        : await api.createFeedback(complaint.id, payload);
      setFeedback(saved);
      setFeedbackRating(saved.rating);
      setFeedbackComment(saved.comment || '');
      setFeedbackMsg(feedback ? 'Feedback updated.' : 'Feedback submitted. Thank you!');
    } catch (err) {
      setFeedbackMsg(`Error: ${err.message || 'Failed to save feedback.'}`);
    } finally {
      setSavingFeedback(false);
    }
  }

  async function handleFeedbackDelete() {
    if (!feedback) return;
    setSavingFeedback(true);
    setFeedbackMsg('');
    try {
      await api.deleteFeedback(complaint.id);
      setFeedback(null);
      setFeedbackRating(5);
      setFeedbackComment('');
      setFeedbackMsg('Feedback removed.');
    } catch (err) {
      setFeedbackMsg(`Error: ${err.message || 'Failed to delete feedback.'}`);
    } finally {
      setSavingFeedback(false);
    }
  }

  function getCategoryName(catId) {
    if (!catId) return 'Uncategorized (Needs Review)';
    const found = categories.find((c) => c.id === catId);
    return found ? found.name : `Category #${catId}`;
  }

  function getDepartmentName(deptId) {
    if (!deptId) return 'Unassigned';
    const found = departments.find((d) => d.id === deptId);
    return found ? found.name : `Department #${deptId}`;
  }

  if (!complaintId) {
    return (
      <div className="card empty-state">
        Select a ticket from the list to view its details, timeline, attachments, and workflow controls.
      </div>
    );
  }

  if (loading && !complaint) {
    return <div className="card empty-state">Loading ticket #{complaintId}...</div>;
  }

  if (!complaint) {
    return (
      <div className="card">
        {error ? <div className="alert alert-error">{error}</div> : null}
        <div className="empty-state">Ticket inaccessible or not found.</div>
      </div>
    );
  }

  return (
    <div>
      {/* Main Ticket Overview Card */}
      <div className="card">
        <div className="card-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span className="ticket-number" style={{ fontSize: '0.95rem' }}>
                {complaint.ticket_number}
              </span>
              <span className={`badge status-${complaint.status}`}>{complaint.status}</span>
              <span className={`badge priority-${complaint.priority}`}>
                Priority: {complaint.priority}
              </span>
            </div>
            <h3 className="card-title" style={{ marginTop: '0.35rem', fontSize: '1.18rem' }}>
              {complaint.title}
            </h3>
          </div>

          <div className="btn-group">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => loadFullTicket(complaint.id)}
            >
              Refresh
            </button>
            {isReporter && complaint.status === 'SUBMITTED' && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setEditingDetails((v) => !v)}
              >
                {editingDetails ? 'Cancel Edit' : 'Edit Report'}
              </button>
            )}
            {user.role === 'ADMIN' && (
              <button type="button" className="btn btn-danger btn-sm" onClick={handleArchive}>
                Archive Ticket
              </button>
            )}
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}
        {actionMsg && <div className="alert alert-success">{actionMsg}</div>}
        {pendingRetryFile && (
          <div className="alert alert-warning">
            <span>
              Ticket <strong>{complaint.ticket_number}</strong> was created, but the initial image
              upload for <strong>{pendingRetryFile.name}</strong> failed.
            </span>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={uploadingImage}
              onClick={() => handleImageUpload(pendingRetryFile)}
            >
              {uploadingImage ? 'Retrying...' : 'Retry Image Upload'}
            </button>
          </div>
        )}

        {editingDetails ? (
          <form onSubmit={handleReporterSaveDetails} style={{ marginTop: '0.75rem' }}>
            <div className="form-group">
              <label className="form-label">Title</label>
              <input
                className="form-input"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                maxLength={160}
                required
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Location</label>
                <select
                  className="form-select"
                  value={editLocation}
                  onChange={(e) => setEditLocation(e.target.value)}
                  required
                >
                  {locations.length === 0 && (
                    <option value={editLocation}>{editLocation || '-- Loading locations --'}</option>
                  )}
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.name}>
                      {loc.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Category (Optional)</label>
                <select
                  className="form-select"
                  value={editCategoryId}
                  onChange={(e) => setEditCategoryId(e.target.value)}
                >
                  <option value="">-- Uncategorized (Route to Review) --</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                className="form-textarea"
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                maxLength={5000}
                required
              />
            </div>
            <div className="btn-group">
              <button type="submit" className="btn btn-primary" disabled={savingDetails}>
                {savingDetails ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setEditingDetails(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <>
            <p style={{ whiteSpace: 'pre-wrap', margin: '0.5rem 0 1rem' }}>
              {complaint.description}
            </p>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
                gap: '0.6rem',
                fontSize: '0.84rem',
                background: 'var(--surface-muted)',
                padding: '0.75rem',
                borderRadius: '6px'
              }}
            >
              <div>
                <strong>Location:</strong> {complaint.location}
              </div>
              <div>
                <strong>Category:</strong> {getCategoryName(complaint.category_id)}
              </div>
              <div>
                <strong>Assigned Department:</strong>{' '}
                {getDepartmentName(complaint.assigned_department_id)}
              </div>
              <div>
                <strong>Assigned Staff ID:</strong>{' '}
                {complaint.assigned_user_id ? `User #${complaint.assigned_user_id}` : 'Department Queue (Any)'}
              </div>
              <div>
                <strong>Reporter ID:</strong> User #{complaint.reporter_user_id}
                {isReporter ? ' (You)' : ''}
              </div>
              <div>
                <strong>Created:</strong> {new Date(complaint.created_at).toLocaleString()}
              </div>
              {complaint.resolved_at && (
                <div>
                  <strong>Resolved:</strong> {new Date(complaint.resolved_at).toLocaleString()}
                </div>
              )}
            </div>
          </>
        )}

        {/* Authorized Image Attachment Section */}
        <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.85rem' }}>
          <div className="card-header" style={{ marginBottom: '0.5rem' }}>
            <h4 className="card-title" style={{ fontSize: '0.95rem' }}>
              Evidence Image Attachment
            </h4>
            {complaint.image_url && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => loadAuthorizedImage(complaint.id)}
              >
                Reload Image
              </button>
            )}
          </div>

          {imageError && <div className="alert alert-error">{imageError}</div>}

          {imageLoading && <div className="section-subtitle">Loading authorized image...</div>}

          {!imageLoading && imageBlobUrl && (
            <div className="image-frame" style={{ marginBottom: '0.75rem' }}>
              <img src={imageBlobUrl} alt={`Attachment for ${complaint.ticket_number}`} />
            </div>
          )}

          {!imageLoading && !imageBlobUrl && !complaint.image_url && (
            <div className="section-subtitle" style={{ marginBottom: '0.5rem' }}>
              No image attached to this ticket.
            </div>
          )}

          {isReporter && complaint.status === 'SUBMITTED' && (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginTop: '0.5rem' }}>
              <input
                type="file"
                accept="image/jpeg,image/png"
                onChange={(e) => {
                  setImageError('');
                  setSelectedFile(e.target.files?.[0] || null);
                }}
              />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={!selectedFile || uploadingImage}
                onClick={() => handleImageUpload(selectedFile)}
              >
                {uploadingImage
                  ? 'Uploading...'
                  : complaint.image_url
                  ? 'Replace Image (<= 5 MiB)'
                  : 'Upload Image (<= 5 MiB)'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Per-Ticket AI Triage Assistance (ADMIN / COORDINATOR) */}
      {isAdminOrCoord && (
        <div className="card">
          <div className="card-header">
            <div>
              <h4 className="card-title">AI Triage &amp; Resolution Assistance</h4>
              <p className="section-subtitle">
                Generates advisory suggestions only; never modifies ticket state without human confirmation.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={analyzing}
              onClick={handleRunAiAnalyze}
            >
              {analyzing ? 'Analyzing...' : 'Get AI Suggestions'}
            </button>
          </div>

          {aiError && <div className="alert alert-error">{aiError}</div>}

          {aiResult && (
            <div
              style={{
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                padding: '0.85rem'
              }}
            >
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
                <span className="badge source-badge">
                  source: {aiResult.source}{' '}
                  {aiResult.source === 'rules' ? '(Rules-based local fallback)' : '(Local model)'}
                </span>
                <span className={`badge priority-${aiResult.priority}`}>
                  Suggested Priority: {aiResult.priority}
                </span>
                {aiResult.needs_review && (
                  <span className="badge status-IN_PROGRESS">Needs Human Review</span>
                )}
              </div>

              <div style={{ fontSize: '0.88rem', marginBottom: '0.45rem' }}>
                <strong>Summary:</strong> {aiResult.summary}
              </div>
              <div style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginBottom: '0.45rem' }}>
                <strong>Reasoning:</strong> {aiResult.reason}
              </div>
              <div style={{ fontSize: '0.85rem', marginBottom: '0.55rem' }}>
                <strong>Suggested Category:</strong> {getCategoryName(aiResult.category_id)} &bull;{' '}
                <strong>Suggested Department:</strong>{' '}
                {getDepartmentName(aiResult.suggested_department_id)}
              </div>

              {Array.isArray(aiResult.suggested_actions) && aiResult.suggested_actions.length > 0 && (
                <div style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                  <strong>Suggested Next Steps for Staff:</strong>
                  <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.2rem' }}>
                    {aiResult.suggested_actions.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}

              {isNonTerminal && (
                <div className="btn-group">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={savingTriage}
                    onClick={handleApplyAiCategoryPriority}
                  >
                    Confirm &amp; Apply Category/Priority
                  </button>
                  {aiResult.suggested_department_id && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={handlePrefillAiDepartment}
                    >
                      Pre-fill Suggested Department Below
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Admin / Coordinator Assignment & Triage Controls (Non-terminal tickets) */}
      {isAdminOrCoord && isNonTerminal && (
        <div className="card">
          <h4 className="card-title" style={{ marginBottom: '0.75rem' }}>
            Admin / Coordinator Assignment &amp; Classification
          </h4>

          <form onSubmit={handleAdminTriageSave} style={{ marginBottom: '1rem' }}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Category</label>
                <select
                  className="form-select"
                  value={triageCategoryId}
                  onChange={(e) => setTriageCategoryId(e.target.value)}
                >
                  <option value="">-- Uncategorized --</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Priority</label>
                <select
                  className="form-select"
                  value={triagePriority}
                  onChange={(e) => setTriagePriority(e.target.value)}
                >
                  <option value="LOW">LOW</option>
                  <option value="NORMAL">NORMAL</option>
                  <option value="HIGH">HIGH</option>
                </select>
              </div>
            </div>
            <button type="submit" className="btn btn-secondary btn-sm" disabled={savingTriage}>
              {savingTriage ? 'Updating...' : 'Update Category & Priority'}
            </button>
          </form>

          <form
            onSubmit={handleAssignSubmit}
            style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.85rem' }}
          >
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Assign Department (Required)</label>
                <select
                  className="form-select"
                  value={assignDeptId}
                  onChange={(e) => {
                    setAssignDeptId(e.target.value);
                    setAssignUserId('');
                  }}
                  required
                >
                  <option value="">-- Select Active Department --</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">
                  Named Staff Assignee (Optional {loadingStaff ? '• loading...' : ''})
                </label>
                <select
                  className="form-select"
                  value={assignUserId}
                  onChange={(e) => setAssignUserId(e.target.value)}
                  disabled={!assignDeptId || loadingStaff}
                >
                  <option value="">-- Department Queue (Any Departmental Staff) --</option>
                  {deptStaff.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} (Staff #{s.id})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button type="submit" className="btn btn-primary btn-sm" disabled={savingAssign}>
              {savingAssign ? 'Assigning...' : 'Save Department Assignment'}
            </button>
          </form>
        </div>
      )}

      {/* Status Transition Controls (ADMIN, COORDINATOR, or Authorized Departmental STAFF) */}
      {canStaffOperate && (
        <div className="card">
          <h4 className="card-title" style={{ marginBottom: '0.4rem' }}>
            Workflow Status Update
          </h4>
          {isNonTerminal ? (
            <form onSubmit={handleStatusSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Next Status Transition</label>
                  <select
                    className="form-select"
                    value={nextStatus}
                    onChange={(e) => setNextStatus(e.target.value)}
                  >
                    {complaint.status === 'SUBMITTED' && (
                      <>
                        <option value="IN_PROGRESS">
                          IN_PROGRESS (Requires assigned department)
                        </option>
                        <option value="REJECTED">REJECTED (Requires outcome note)</option>
                      </>
                    )}
                    {complaint.status === 'IN_PROGRESS' && (
                      <>
                        <option value="RESOLVED">RESOLVED (Requires verification &amp; note)</option>
                        <option value="REJECTED">REJECTED (Requires outcome note)</option>
                      </>
                    )}
                  </select>
                  {complaint.status === 'SUBMITTED' &&
                    nextStatus === 'IN_PROGRESS' &&
                    !complaint.assigned_department_id && (
                      <span className="form-hint" style={{ color: 'var(--danger)' }}>
                        Assign a department first before moving to IN_PROGRESS.
                      </span>
                    )}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">
                  Outcome / Progress Note{' '}
                  {nextStatus === 'RESOLVED' || nextStatus === 'REJECTED'
                    ? '(Required)'
                    : '(Optional)'}
                </label>
                <textarea
                  className="form-textarea"
                  value={statusNote}
                  onChange={(e) => setStatusNote(e.target.value)}
                  maxLength={2000}
                  placeholder="Describe action taken, verification details, or reason for rejection..."
                  required={nextStatus === 'RESOLVED' || nextStatus === 'REJECTED'}
                />
              </div>

              {nextStatus === 'RESOLVED' && (
                <div className="form-group">
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.86rem', fontWeight: 600 }}>
                    <input
                      type="checkbox"
                      checked={staffVerified}
                      onChange={(e) => setStaffVerified(e.target.checked)}
                    />
                    I confirm departmental staff verified the physical/technical fix before resolving.
                  </label>
                </div>
              )}

              <button type="submit" className="btn btn-primary" disabled={savingStatus}>
                {savingStatus ? 'Updating Status...' : `Mark as ${nextStatus}`}
              </button>
            </form>
          ) : (
            <div className="section-subtitle">
              This ticket is in terminal state <strong>{complaint.status}</strong>. Reopening is
              disabled in this prototype.
            </div>
          )}
        </div>
      )}

      {/* Reporter Feedback CRUD (Original reporter on RESOLVED ticket) */}
      {isReporter && complaint.status === 'RESOLVED' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h4 className="card-title">Reporter Resolution Feedback</h4>
              <p className="section-subtitle">
                Rate how effectively your resolved issue was handled (1 to 5 stars).
              </p>
            </div>
            {feedback && (
              <span className="badge status-RESOLVED">Submitted: {feedback.rating}/5 Stars</span>
            )}
          </div>

          {feedbackMsg && (
            <div
              className={`alert ${
                feedbackMsg.startsWith('Error:') ? 'alert-error' : 'alert-success'
              }`}
            >
              {feedbackMsg}
            </div>
          )}

          {loadingFeedback ? (
            <div className="section-subtitle">Loading feedback...</div>
          ) : (
            <form onSubmit={handleFeedbackSubmit}>
              <div className="form-group">
                <label className="form-label">Rating (1 = Poor, 5 = Excellent)</label>
                <select
                  className="form-select"
                  value={feedbackRating}
                  onChange={(e) => setFeedbackRating(Number(e.target.value))}
                >
                  <option value={5}>5 Stars — Excellent resolution</option>
                  <option value={4}>4 Stars — Good resolution</option>
                  <option value={3}>3 Stars — Satisfactory</option>
                  <option value={2}>2 Stars — Subpar resolution</option>
                  <option value={1}>1 Star — Issue not properly addressed</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Comment (Optional)</label>
                <textarea
                  className="form-textarea"
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  maxLength={2000}
                  placeholder="Share any comments on the repair quality or response speed..."
                />
              </div>
              <div className="btn-group">
                <button type="submit" className="btn btn-primary btn-sm" disabled={savingFeedback}>
                  {savingFeedback
                    ? 'Saving...'
                    : feedback
                    ? 'Update Feedback'
                    : 'Submit Feedback'}
                </button>
                {feedback && (
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    disabled={savingFeedback}
                    onClick={handleFeedbackDelete}
                  >
                    Delete Feedback
                  </button>
                )}
              </div>
            </form>
          )}
        </div>
      )}

      {/* Chronological Status & Assignment History Timeline */}
      <div className="card">
        <h4 className="card-title" style={{ marginBottom: '0.75rem' }}>
          Audit History Timeline ({history.length})
        </h4>
        {history.length === 0 ? (
          <div className="section-subtitle">No history events recorded yet.</div>
        ) : (
          <ul className="timeline">
            {history.map((h) => (
              <li key={`${h.kind}-${h.id}`} className="timeline-item">
                <div style={{ fontWeight: 600 }}>
                  {h.kind === 'STATUS' ? (
                    <>
                      Status: {h.old_status ? `${h.old_status} → ` : ''}
                      <span className={`badge status-${h.new_status}`}>{h.new_status}</span>
                    </>
                  ) : (
                    <>
                      Assignment: {getDepartmentName(h.department_id)}
                      {h.assigned_user_id ? ` (Staff #${h.assigned_user_id})` : ' (Department Queue)'}
                    </>
                  )}
                </div>
                {h.note && (
                  <div style={{ marginTop: '0.2rem', color: 'var(--text)' }}>
                    Note: &ldquo;{h.note}&rdquo;
                  </div>
                )}
                <div className="timeline-time">
                  Actor User #{h.actor_user_id} &bull; {new Date(h.created_at).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
