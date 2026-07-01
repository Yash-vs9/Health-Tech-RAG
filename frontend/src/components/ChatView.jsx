import React, { useState, useRef, useEffect } from 'react';
import FileUpload from './FileUpload';

export default function ChatView({ chat, messages, docs, onSend, onUpload, onDeleteDoc, loading }) {
  const [input, setInput] = useState('');
  const messagesEnd = useRef(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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

  return (
    <div className="chat-view">
      <div className="chat-header">
        <h3>{chat.title}</h3>
        <span className="doc-count">{docs.length} documents</span>
      </div>

      {/* Documents panel */}
      <div className="docs-panel">
        <FileUpload onUpload={onUpload} />
        {docs.length > 0 && (
          <div className="doc-list">
            {docs.map(doc => (
              <div key={doc.id} className="doc-item">
                <span className="doc-name">{doc.filename}</span>
                <span className={`doc-status ${doc.status}`}>{doc.status}</span>
                {doc.num_chunks > 0 && <span className="doc-chunks">{doc.num_chunks} chunks</span>}
                <button className="btn-remove" onClick={() => onDeleteDoc(doc.id)}>×</button>
              </div>
            ))}
          </div>
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
