import React from 'react';

export function CitationPanel({ sources = [] }) {
  if (!sources.length) {
    return <div className="citation-panel empty">No sources returned.</div>;
  }

  return (
    <div className="citation-panel">
      <details>
        <summary>Sources</summary>
        <ul>
          {sources.map((source, index) => (
            <li key={`${source.doc_id}-${index}`}>
              <strong>{source.doc_id}</strong>
              {source.page !== null && source.page !== undefined ? `, page ${source.page}` : ''}
              {source.section ? `, ${source.section}` : ''}
              <div>{source.text}</div>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
