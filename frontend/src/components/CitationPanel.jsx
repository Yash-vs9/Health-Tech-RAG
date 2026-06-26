import React, { useState } from 'react';

export default function CitationPanel({ sources }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="citation-panel">
      <button className="citation-toggle" onClick={() => setOpen(!open)}>
        Sources ({sources.length}) {open ? '▲' : '▼'}
      </button>
      {open && (
        <ul className="citation-list">
          {sources.map((source, i) => (
            <li key={i} className="citation-item">
              <span className="citation-doc">{source.metadata?.filename || source.metadata?.doc_id || 'Unknown'}</span>
              {source.metadata?.page !== undefined && (
                <span className="citation-page">, page {source.metadata.page}</span>
              )}
              <p className="citation-text">{source.content}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
