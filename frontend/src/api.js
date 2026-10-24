// ponytail: single /api/v1 fetch wrapper over native fetch + sessionStorage; no axios/react-query bloat
const API_BASE = '/api/v1';
const TOKEN_KEY = 'campusresolve_token';
const USER_KEY = 'campusresolve_user';

let onUnauthorizedCallback = null;

export function setUnauthorizedHandler(fn) {
  onUnauthorizedCallback = fn;
}

export function getStoredToken() {
  return sessionStorage.getItem(TOKEN_KEY) || '';
}

export function getStoredUser() {
  try {
    const raw = sessionStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredSession(accessToken, user) {
  sessionStorage.setItem(TOKEN_KEY, accessToken);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function formatApiError(detail, status) {
  if (!detail) return `Request failed (${status})`;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        const loc = Array.isArray(item.loc) ? item.loc.filter((p) => p !== 'body').join('.') : '';
        const msg = item.msg || JSON.stringify(item);
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join('; ');
  }
  return JSON.stringify(detail);
}

async function request(path, options = {}) {
  const token = getStoredToken();
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
  });

  if (res.status === 401 && path !== '/auth/login') {
    clearStoredSession();
    if (onUnauthorizedCallback) onUnauthorizedCallback('Session expired or unauthenticated. Please sign in again.');
  }

  if (res.status === 204) {
    return null;
  }

  let payload = null;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      payload = await res.json();
    } catch {
      payload = null;
    }
  } else {
    const text = await res.text();
    payload = text ? { detail: text } : null;
  }

  if (!res.ok) {
    const err = new Error(formatApiError(payload?.detail, res.status));
    err.status = res.status;
    err.detail = payload?.detail;
    throw err;
  }

  return payload;
}

export const api = {
  // Auth & context
  login: (email, password) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    }),
  getMe: () => request('/auth/me'),
  getCurrentInstitution: () => request('/institutions/current'),
  getLocations: () => request('/locations'),

  // Categories
  getCategories: () => request('/categories'),
  createCategory: (data) =>
    request('/categories', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
  updateCategory: (id, data) =>
    request(`/categories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    }),
  deactivateCategory: (id) =>
    request(`/categories/${id}`, {
      method: 'DELETE'
    }),

  // Departments & Staff
  getDepartments: () => request('/departments'),
  createDepartment: (data) =>
    request('/departments', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
  updateDepartment: (id, data) =>
    request(`/departments/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    }),
  deactivateDepartment: (id) =>
    request(`/departments/${id}`, {
      method: 'DELETE'
    }),
  getStaff: (departmentId) =>
    request(`/staff?department_id=${encodeURIComponent(departmentId)}`),

  // Complaints
  createComplaint: (data) =>
    request('/complaints', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
  getComplaints: (params = {}) => {
    const search = new URLSearchParams();
    if (params.status) search.set('status', params.status);
    if (params.category_id) search.set('category_id', String(params.category_id));
    if (params.mine !== undefined && params.mine !== null) {
      search.set('mine', String(Boolean(params.mine)));
    }
    const qs = search.toString();
    return request(`/complaints${qs ? `?${qs}` : ''}`);
  },
  getComplaint: (id) => request(`/complaints/${id}`),
  updateComplaint: (id, data) =>
    request(`/complaints/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    }),
  archiveComplaint: (id) =>
    request(`/complaints/${id}`, {
      method: 'DELETE'
    }),

  // Image attachment (multipart field `file` & authorized binary fetch)
  uploadComplaintImage: (id, file) => {
    const form = new FormData();
    form.append('file', file);
    return request(`/complaints/${id}/image`, {
      method: 'POST',
      body: form
    });
  },
  fetchComplaintImageBlobUrl: async (id) => {
    const token = getStoredToken();
    const res = await fetch(`${API_BASE}/complaints/${id}/image`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (res.status === 401) {
      clearStoredSession();
      if (onUnauthorizedCallback) onUnauthorizedCallback('Session expired or unauthenticated.');
      throw new Error('Unauthenticated');
    }
    if (!res.ok) {
      throw new Error(`Image unavailable (${res.status})`);
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },

  // Assignment, Status & History
  assignComplaint: (id, data) =>
    request(`/complaints/${id}/assign`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    }),
  changeComplaintStatus: (id, data) =>
    request(`/complaints/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    }),
  getComplaintHistory: (id) => request(`/complaints/${id}/history`),

  // Reporter Feedback CRUD
  getFeedback: (id) => request(`/complaints/${id}/feedback`),
  createFeedback: (id, data) =>
    request(`/complaints/${id}/feedback`, {
      method: 'POST',
      body: JSON.stringify(data)
    }),
  updateFeedback: (id, data) =>
    request(`/complaints/${id}/feedback`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    }),
  deleteFeedback: (id) =>
    request(`/complaints/${id}/feedback`, {
      method: 'DELETE'
    }),

  // Dashboard Stats, AI Triage & Optional AI Insights
  getDashboardStats: () => request('/dashboard/stats'),
  analyzeComplaint: (id) =>
    request(`/complaints/${id}/analyze`, {
      method: 'POST'
    }),
  getDashboardInsights: (fromDate, toDate) =>
    request(
      `/dashboard/insights?from=${encodeURIComponent(fromDate)}&to=${encodeURIComponent(toDate)}`
    ),
  generateInsightsReport: (fromDate, toDate) =>
    request('/dashboard/insights/report', {
      method: 'POST',
      body: JSON.stringify({ from: fromDate, to: toDate })
    })
};
