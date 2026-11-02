const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getToken() {
  return localStorage.getItem('eduverse_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = 'Something went wrong';
    try {
      const errBody = await response.json();
      detail = errBody.detail || detail;
    } catch (e) {
      // ignore parse error
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

// ---------- Auth ----------

export function registerStudent(data) {
  return request('/api/auth/register', { method: 'POST', body: JSON.stringify(data) });
}

export function loginStudent(data) {
  return request('/api/auth/login', { method: 'POST', body: JSON.stringify(data) });
}

export function getMe() {
  return request('/api/auth/me');
}

export function updateProfile(data) {
  return request('/api/auth/me', { method: 'PATCH', body: JSON.stringify(data) });
}

// ---------- Dashboard / Progress ----------

export function getDashboardSummary() {
  return request('/api/progress/summary');
}

export function getSubjectProgress() {
  return request('/api/progress/subjects');
}

export function createSubject(data) {
  return request('/api/progress/subjects', { method: 'POST', body: JSON.stringify(data) });
}

export function getWeeklyActivity() {
  return request('/api/progress/weekly');
}

export function logActivity(data) {
  return request('/api/progress/activity', { method: 'POST', body: JSON.stringify(data) });
}

export function getWeakTopics() {
  return request('/api/progress/weak-topics');
}

// ---------- Tasks ----------

export function getTasks(status = '') {
  const query = status ? `?status=${status}` : '';
  return request(`/api/tasks${query}`);
}

export function createTask(data) {
  return request('/api/tasks', { method: 'POST', body: JSON.stringify(data) });
}

export function updateTask(taskId, status) {
  return request(`/api/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify({ status }) });
}

export function deleteTask(taskId) {
  return request(`/api/tasks/${taskId}`, { method: 'DELETE' });
}

// ---------- Chat ----------

export function sendChatMessage(data) {
  return request('/api/chat', { method: 'POST', body: JSON.stringify(data) });
}

export function getChatHistory(subject = '') {
  const query = subject ? `?subject=${encodeURIComponent(subject)}` : '';
  return request(`/api/chat/history${query}`);
}

export function clearChatHistory() {
  return request('/api/chat/history', { method: 'DELETE' });
}

export async function streamChatMessage(data, { onToken, onFirstToken, onDone, onSources, signal }) {
  const response = await fetch(`${API_URL}/api/chat/stream`, {
    method: 'POST',
    signal,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    let detail = 'Something went wrong';
    try { detail = (await response.json()).detail || detail; } catch (e) { /* ignore */ }
    throw new Error(detail);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop();
    for (const ev of events) {
      if (!ev.startsWith('data: ')) continue;
      const msg = JSON.parse(ev.slice(6));
      if (msg.error) throw new Error(msg.error);
      if (msg.sources) onSources?.(msg.sources, msg);
      if (msg.first_token_s != null) onFirstToken?.(msg.first_token_s);
      if (msg.t) onToken?.(msg.t);
      if (msg.done) onDone?.(msg);
    }
  }
}

// ---------- Knowledge base (RAG) ----------

export function listDocs() {
  return request('/api/docs');
}

export function deleteDoc(id) {
  return request(`/api/docs/${id}`, { method: 'DELETE' });
}

export async function uploadDoc(file, { title = '', subject = '' } = {}) {
  const form = new FormData();
  form.append('file', file);
  form.append('title', title);
  form.append('subject', subject);
  // no Content-Type header: the browser adds the multipart boundary itself
  const response = await fetch(`${API_URL}/api/docs/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
  });
  if (!response.ok) {
    let detail = 'Upload failed';
    try { detail = (await response.json()).detail || detail; } catch (e) { /* ignore */ }
    throw new Error(detail);
  }
  return response.json();
}

export function getRagStatus(probe = false) {
  return request(`/api/docs/status${probe ? '?probe=true' : ''}`);
}

export function reindexDocs() {
  return request('/api/docs/reindex', { method: 'POST' });
}

export function searchDocs(q) {
  return request(`/api/docs/search?q=${encodeURIComponent(q)}`);
}

// ---------- Gamification ----------

export function getGamification() {
  return request('/api/gamification/me');
}

// ---------- Quiz ----------

export function generateQuiz(data) {
  return request('/api/quiz/generate', { method: 'POST', body: JSON.stringify(data) });
}

export function submitQuiz(data) {
  return request('/api/quiz/submit', { method: 'POST', body: JSON.stringify(data) });
}

export function getQuizHistory() {
  return request('/api/quiz/history/all');
}

// ---------- Content ----------

// Study material arrives as it is written (server-sent events), so long notes never feel like a hang.
export async function streamContent(data, { onMeta, onToken, onDone, signal }) {
  const response = await fetch(`${API_URL}/api/content/stream`, {
    method: 'POST',
    signal,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    let detail = 'Something went wrong';
    try { detail = (await response.json()).detail || detail; } catch (e) { /* ignore */ }
    throw new Error(detail);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop();
    for (const ev of events) {
      if (!ev.startsWith('data: ')) continue;
      const msg = JSON.parse(ev.slice(6));
      if (msg.error) throw new Error(msg.error);
      if (msg.meta) onMeta?.(msg.meta);
      if (msg.t) onToken?.(msg.t);
      if (msg.done) onDone?.(msg);
    }
  }
}

export function generateContent(data) {
  return request('/api/content/generate', { method: 'POST', body: JSON.stringify(data) });
}

// ---------- Planner ----------

export function generateStudyPlan(data) {
  return request('/api/planner/generate', { method: 'POST', body: JSON.stringify(data) });
}

export { getToken };
