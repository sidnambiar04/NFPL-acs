const API_BASE = import.meta.env.VITE_API_URL || 'https://nfpl-acs-backend.onrender.com/api';

// Current active persona ID
let currentUserId = 'usr_asha';

export const setCurrentUser = (userId) => {
  currentUserId = userId;
  localStorage.setItem('nfpl_user_id', userId);
};

export const getCurrentUser = () => {
  return localStorage.getItem('nfpl_user_id') || currentUserId;
};

const request = async (endpoint, options = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': getCurrentUser(),
    ...(options.headers || {})
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const error = new Error(data?.detail?.reason || data?.detail || 'Request failed');
    error.status = response.status;
    error.detail = data?.detail;
    throw error;
  }

  return data;
};

export const api = {
  // Auth & Profile
  getUsers: () => request('/auth/users'),
  getBranches: () => request('/auth/branches'),
  getClients: () => request('/auth/clients'),
  getMe: () => request('/auth/me'),

  // Work Queue
  getWorkQueue: (limit = 50, offset = 0) => request(`/me/work-queue?limit=${limit}&offset=${offset}`),

  // Jobs
  getJobs: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.append(k, v);
    });
    return request(`/jobs?${query.toString()}`);
  },
  getJob: (id) => request(`/jobs/${id}`),
  getAvailableActions: (id) => request(`/jobs/${id}/available-actions`),
  getJobHistory: (id) => request(`/jobs/${id}/history`),

  // Workflow Transitions
  prepareJob: (id, reason) => request(`/jobs/${id}/prepare`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),
  checkJob: (id, reason) => request(`/jobs/${id}/check`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),
  fileJob: (id, reason) => request(`/jobs/${id}/file`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),
  cancelJob: (id, reason) => request(`/jobs/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),
  reopenJob: (id, reason) => request(`/jobs/${id}/reopen`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),

  // Access Simulator & Compare
  authorizeAction: (userId, action, jobId) => request('/access/authorize', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, action, job_id: jobId })
  }),
  compareAccess: (userAId, userBId, jobId, action) => request('/access/compare', {
    method: 'POST',
    body: JSON.stringify({ user_a_id: userAId, user_b_id: userBId, job_id: jobId, action })
  }),

  // Audit & Temporal Inquiries
  getDecisions: () => request('/audit/decisions'),
  getAuditEvents: () => request('/audit/events'),
  whoCouldAct: (jobId, action, targetTime) => 
    request(`/audit/who-could-act?job_id=${jobId}&action=${action}&target_time=${encodeURIComponent(targetTime)}`),

  // Admin
  getAssignments: (userId) => request(`/admin/assignments${userId ? `?user_id=${userId}` : ''}`),
  createAssignment: (data) => request('/admin/assignments', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  revokeAssignment: (id) => request(`/admin/assignments/${id}/revoke`, { method: 'PATCH' }),
  getDelegations: () => request('/admin/delegations'),
  createDelegation: (data) => request('/admin/delegations', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  getRoles: () => request('/admin/roles'),
  getPermissions: () => request('/admin/permissions'),
  createRole: (data) => request('/admin/roles', {
    method: 'POST',
    body: JSON.stringify(data)
  })
};
