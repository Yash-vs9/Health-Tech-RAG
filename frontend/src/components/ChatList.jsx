import React from 'react';

export default function ChatList({ chats, activeChat, onSelect, onNew, onDelete, user, onLogout }) {
  return (
    <div className="chat-list">
      <div className="chat-list-header">
        <h2>Chats</h2>
        <button className="btn-new" onClick={onNew}>+ New Chat</button>
      </div>

      <div className="chat-items">
        {chats.length === 0 && (
          <p className="empty">No chats yet. Create one to get started.</p>
        )}
        {chats.map(chat => (
          <div
            key={chat.id}
            className={`chat-item ${activeChat?.id === chat.id ? 'active' : ''}`}
            onClick={() => onSelect(chat)}
          >
            <div className="chat-item-title">{chat.title}</div>
            <div className="chat-item-meta">{chat.document_count} docs</div>
            <button
              className="btn-delete"
              onClick={(e) => { e.stopPropagation(); onDelete(chat.id); }}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <div className="chat-list-footer">
        <span>{user?.email || 'User'}</span>
        <button className="btn-logout" onClick={onLogout}>Logout</button>
      </div>
    </div>
  );
}
