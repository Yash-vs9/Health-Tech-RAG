import React, { useState, useRef, useEffect } from 'react';
import FileUpload from './FileUpload';

export default function ChatView({ chat, messages, docs, onSend, onUpload, onDeleteDoc, onRename, loading }) {
  const [input, setInput] = useState('');
  const [docsExpanded, setDocsExpanded] = useState(true);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState('');
  const messagesEnd = useRef(null);
  const titleRef = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (editingTitle && titleRef.current) {
      titleRef.current.focus();
      titleRef.current.select();
    }
  }, [editingTitle]);

  if (!chat) {
    return (
      <div className="chat-view empty-state">
        <div className="empty-icon">🏠</div>
        <h2>Mortgage RAG Assistant</h2>
        <p>Select a chat or create a new one to get started.</p>
      </div>
    );
  }

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !loading) {
      onSend(input.trim());
      setInput('');
    }
  };

  const startRename = () => {
    setTitleValue(chat.title);
    setEditingTitle(true);
  };

  const commitRename = () => {
    if (titleValue.trim() && titleValue.trim() !== chat.title) {
      onRename(chat.id, titleValue.trim());
    }
    setEditingTitle(false);
  };

  const handleTitleKeyDown = (e) => {
    if (e.key === 'Enter') commitRename();
    else if (e.key === 'Escape') setEditingTitle(false);
  };

  const hasProcessing = docs.some(d => d.status === 'processing');
  const readyCount = docs.filter(d => d.status === 'ready').length;

  return (
    <div className="chat-view">
      <div className="chat-header">
        <div className="chat-header-left">
          {editingTitle ? (
            <input
              ref={titleRef}
              className="chat-title-input"
              value={titleValue}
              onChange={(e) => setTitleValue(e.target.value)}
              onBlur={commitRename}
              onKeyDown={handleTitleKeyDown}
            />
          ) : (
            <h3 onDoubleClick={startRename} title="Double-click to rename">{chat.title}</h3>
          )}
        </div>
        <div className="chat-header-right">
          <span className="doc-count">{readyCount} docs ready{hasProcessing ? ` · ${docs.filter(d => d.status === 'processing').length} processing` : ''}</span>
        </div>
      </div>

      {/* Documents panel — collapsible */}
      <div className={`docs-panel ${docsExpanded ? 'expanded' : 'collapsed'}`}>
        <div className="docs-panel-header">
          <button
            className="docs-toggle-btn"
            onClick={() => setDocsExpanded((v) => !v)}
            title={docsExpanded ? 'Collapse' : 'Expand'}
          >
            <span className="docs-toggle-arrow">{docsExpanded ? '▾' : '▸'}</span>
            <span className="docs-toggle-label">Documents ({docs.length})</span>
          </button>
        </div>
        {docsExpanded && (
          <>
            <FileUpload onUpload={onUpload} />
            {docs.length > 0 && (
              <div className="doc-list">
                {docs.map(doc => (
                  <div key={doc.id} className="doc-item">
                    <span className="doc-name">{doc.filename}</span>
                    <span className={`doc-status ${doc.status}`}>{doc.status}</span>
                    {doc.num_chunks > 0 && <span className="doc-chunks">{doc.num_chunks} chunks</span>}
                    <button className="btn-remove" onClick={() => onDeleteDoc(doc.id)} title="Remove">×</button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Messages */}
      <div className="messages">
        {messages.length === 0 && (
          <div className="no-messages">
            <p>Ask a question about your documents.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="message-role">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
            <div className="message-text">{msg.content}</div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="message-sources">
                <details>
                  <summary>Sources ({msg.sources.length})</summary>
                  {msg.sources.map((s, j) => (
                    <div key={j} className="source-item">
                      <strong>{s.metadata?.filename || s.metadata?.doc_id || 'Doc'}</strong>
                      {s.metadata?.page !== undefined && ` — page ${s.metadata.page}`}
                      <p>{s.content?.substring(0, 150)}...</p>
                    </div>
                  ))}
                </details>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="message assistant loading">
            <div className="message-role">Assistant</div>
            <div className="message-text">Thinking...</div>
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      {/* Input */}
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about your mortgage documents..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
