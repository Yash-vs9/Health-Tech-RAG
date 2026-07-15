import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import FileUpload from './FileUpload';
import { Send, ChevronDown, ChevronRight, Bot, User, Sparkles, ExternalLink, Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react';

export default function ChatView({ chat, messages, docs, onSend, onUpload, onDeleteDoc, onRename, loading, onSourceClick, onFeedback }) {
  const [input, setInput] = useState('');
  const [docsExpanded, setDocsExpanded] = useState(true);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState('');
  const [copiedId, setCopiedId] = useState(null);
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
        <motion.div
          className="empty-icon"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, type: "spring" }}
        >
          <Sparkles size={36} color="var(--accent)" />
        </motion.div>
        <motion.h2
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          Mortgage RAG Assistant
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          Select a chat or create a new one to get started.
        </motion.p>
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

  const handleCopy = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  const handleFeedback = (msg, type) => {
    const newValue = msg.feedback === type ? null : type;
    onFeedback && onFeedback(msg, newValue);
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

      <div className={`docs-panel ${docsExpanded ? 'expanded' : 'collapsed'}`}>
        <div className="docs-panel-header">
          <button
            className="docs-toggle-btn"
            onClick={() => setDocsExpanded((v) => !v)}
            title={docsExpanded ? 'Collapse' : 'Expand'}
          >
            <span className="docs-toggle-arrow">
              {docsExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
            <span className="docs-toggle-label">Documents ({docs.length})</span>
          </button>
        </div>
        {docsExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.2 }}
          >
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
          </motion.div>
        )}
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <motion.div
            className="no-messages"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Bot size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
            <p>Ask a question about your documents.</p>
          </motion.div>
        )}
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={msg.id || i}
              className={`message ${msg.role}`}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              layout
            >
              <div className="message-role">
                {msg.role === 'user' ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><User size={12} /> You</span>
                ) : (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><Bot size={12} /> Assistant</span>
                )}
              </div>
              <div className="message-text">{msg.content}</div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <details>
                    <summary>Sources ({msg.sources.length})</summary>
                    {msg.sources.map((s, j) => (
                      <div
                        key={j}
                        className="source-item clickable"
                        onClick={() => onSourceClick && onSourceClick(
                          s.metadata?.doc_id,
                          s.metadata?.filename,
                          s.metadata?.page_number || s.metadata?.page
                        )}
                        title="Click to view in PDF"
                      >
                        <div className="source-item-header">
                          <strong>{s.metadata?.filename || s.metadata?.doc_id || 'Doc'}</strong>
                          {s.metadata?.page_number !== undefined && (
                            <span className="source-page">Page {s.metadata.page_number}</span>
                          )}
                          {s.metadata?.section && (
                            <span className="source-section">{s.metadata.section}</span>
                          )}
                          <ExternalLink size={12} className="source-link-icon" />
                        </div>
                        <p>{s.content?.substring(0, 150)}...</p>
                      </div>
                    ))}
                  </details>
                </div>
              )}
              {msg.role === 'assistant' && (
                <div className="message-actions">
                  <button
                    className="msg-action-btn"
                    onClick={() => handleCopy(msg.content, msg.id || i)}
                    title="Copy response"
                  >
                    {copiedId === (msg.id || i) ? <Check size={14} /> : <Copy size={14} />}
                  </button>
                  <button
                    className={`msg-action-btn ${msg.feedback === 'up' ? 'active-up' : ''}`}
                    onClick={() => handleFeedback(msg, 'up')}
                    title="Good response"
                  >
                    <ThumbsUp size={14} />
                  </button>
                  <button
                    className={`msg-action-btn ${msg.feedback === 'down' ? 'active-down' : ''}`}
                    onClick={() => handleFeedback(msg, 'down')}
                    title="Bad response"
                  >
                    <ThumbsDown size={14} />
                  </button>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <motion.div
            className="message assistant loading"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="message-role">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><Bot size={12} /> Assistant</span>
            </div>
            <div className="message-text">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </motion.div>
        )}
        <div ref={messagesEnd} />
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about your mortgage documents..."
          disabled={loading}
        />
        <motion.button
          type="submit"
          disabled={loading || !input.trim()}
          whileHover={{ scale: loading ? 1 : 1.03 }}
          whileTap={{ scale: loading ? 1 : 0.97 }}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Send size={18} />
        </motion.button>
      </form>
    </div>
  );
}