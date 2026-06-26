import React from 'react';
import CitationPanel from './CitationPanel';

export default function ChatMessage({ message }) {
  const { role, text, sources } = message;

  if (role === 'system') {
    return (
      <div className="message system-message">
        <p>{text}</p>
      </div>
    );
  }

  return (
    <div className={`message ${role === 'user' ? 'user-message' : 'assistant-message'}`}>
      <div className="message-role">{role === 'user' ? 'You' : 'Assistant'}</div>
      <div className="message-text">{text}</div>
      {sources && sources.length > 0 && <CitationPanel sources={sources} />}
    </div>
  );
}
