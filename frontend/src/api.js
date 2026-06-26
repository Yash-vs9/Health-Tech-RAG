const API_BASE = '';

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function ingestDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: formData });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Ingestion failed');
  }
  return res.json();
}

export async function queryDocs(question, docIds = []) {
  const res = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, doc_ids: docIds }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Query failed');
  }
  return res.json();
}
