import React, { useState, useRef, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ChatMessage from './components/ChatMessage';
import { ingestDocument, queryDocs } from './api';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [ingestedDocs, setIngestedDocs] = useState([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleUpload = async (file) => {
    setUploadStatus(`Uploading ${file.name}...`);
    try {
      const result = await ingestDocument(file);
      setIngestedDocs(prev => [...prev, { doc_id: result.doc_id, filename: result.filename }]);
      setUploadStatus(`Uploaded: ${result.filename} → ${result.num_chunks} chunks (ID: ${result.doc_id})`);
      setMessages(prev => [...prev, {
        role: 'system',
        text: `Document ingested: ${result.filename} (${result.num_chunks} chunks)`,
      }]);
    } catch (err) {
      setUploadStatus(`Error: ${err.message}`);
    }
  };

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: question }]);
    setLoading(true);

    try {
      const docIds = ingestedDocs.map(d => d.doc_id);
      const result = await queryDocs(question, docIds);
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: result.answer,
        sources: result.sources,
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: `Error: ${err.message}`,
        sources: [],
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>Health RAG Chatbot</h1>
        <p>Upload a PDF or DOCX, then ask questions about its content</p>
      </header>

      <div className="sidebar">
        <FileUpload onUpload={handleUpload} />
        {uploadStatus && <div className="upload-status">{uploadStatus}</div>}
        {ingestedDocs.length > 0 && (
          <div className="doc-list">
            <h3>Ingested Documents</h3>
            <ul>
              {ingestedDocs.map((doc, i) => (
                <li key={i}>{doc.filename} <span className="doc-id">({doc.doc_id})</span></li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <main className="chat-area">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>Upload a document and ask a question to get started.</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))}
          {loading && <div className="typing">Thinking...</div>}
          <div ref={chatEndRef} />
        </div>

        <form className="input-bar" onSubmit={handleQuery}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a health question..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </main>
    </div>
  );
}
