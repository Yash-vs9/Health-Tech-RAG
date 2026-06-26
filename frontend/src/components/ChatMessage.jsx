import React from 'react';
import { CitationPanel } from './CitationPanel';

export function ChatMessage({ message, sources = [], role = 'assistant' }) {
  return (
    <div className={`chat-message chat-message-${role}`}>
      <p>{message}</p>
      <CitationPanel sources={sources} />
    </div>
  );
}
