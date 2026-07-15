const API_BASE = '';

let onUnauthorized = null;

export function setOnUnauthorized(callback) {
  onUnauthorized = callback;
}

function handle401() {
  if (onUnauthorized) onUnauthorized();
}

async function request(method, path, body = null, token = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  if (res.status === 401) {
    handle401();
    throw new Error('Session expired');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    let errorMsg = 'Request failed';
    if (Array.isArray(err.detail)) {
      errorMsg = err.detail.map(e => e.msg || JSON.stringify(e)).join(', ');
    } else if (err.detail) {
      errorMsg = err.detail;
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

async function uploadFile(path, file, token) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  });
  if (res.status === 401) {
    handle401();
    throw new Error('Session expired');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export const api = {
  // Auth
  signup: (email, password, full_name) =>
    request('POST', '/auth/signup', { email, password, full_name }),
  login: (email, password) =>
    request('POST', '/auth/login', { email, password }),
  me: (token) => request('GET', '/auth/me', null, token),
  logout: (token) => request('POST', '/auth/logout', null, token),

  // Chats
  createChat: (token, title = 'New Chat') =>
    request('POST', '/chats', { title }, token),
  listChats: (token) => request('GET', '/chats', null, token),
  deleteChat: (token, id) => request('DELETE', `/chats/${id}`, null, token),
  renameChat: (token, id, title) =>
    request('PATCH', `/chats/${id}`, { title }, token),

  // Documents
  uploadDoc: (token, chatId, file) =>
    uploadFile(`/chats/${chatId}/documents`, file, token),
  listDocs: (token, chatId) =>
    request('GET', `/chats/${chatId}/documents`, null, token),
  deleteDoc: (token, chatId, docId) =>
    request('DELETE', `/chats/${chatId}/documents/${docId}`, null, token),
  getDocPdfUrl: (token, chatId, docId) =>
    `${API_BASE}/chats/${chatId}/documents/${docId}/pdf`,

  // Messages
  sendMessage: (token, chatId, question) =>
    request('POST', `/chats/${chatId}/messages`, { chat_session_id: chatId, question }, token),
  getHistory: (token, chatId) =>
    request('GET', `/chats/${chatId}/messages`, null, token),
  setFeedback: (token, chatId, messageId, feedback) =>
    request('PATCH', `/chats/${chatId}/messages/${messageId}/feedback`, { feedback }, token),

  // Legacy (no auth)
  ingest: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/ingest`, { method: 'POST', body: formData }).then(r => r.json());
  },
  query: (question, doc_ids = null) =>
    request('POST', '/query', { question, doc_ids }),
};