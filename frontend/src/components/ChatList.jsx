import React, { useState, useRef, useEffect } from 'react';

export default function ChatList({ chats, activeChat, onSelect, onNew, onDelete, onRename, user, onLogout }) {
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState('');
  const editRef = useRef(null);

  useEffect(() => {
    if (editingId && editRef.current) {
      editRef.current.focus();
      editRef.current.select();
    }
  }, [editingId]);

  const startEdit = (e, chat) => {
    e.stopPropagation();
    setEditingId(chat.id);
    setEditValue(chat.title);
  };

  const commitEdit = () => {
    if (editValue.trim() && editingId) {
      onRename(editingId, editValue.trim());
    }
    setEditingId(null);
    setEditValue('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      commitEdit();
    } else if (e.key === 'Escape') {
      setEditingId(null);
      setEditValue('');
    }
  };

  return (
    <div className="chat-list">
      <div className="chat-list-header">
        <h2>Chats</h2>
        <button className="btn-new" onClick={onNew}>+ New</button>
      </div>

      <div className="chat-items">
        {chats.length === 0 && (
          <p className="empty">No chats yet.</p>
        )}
        {chats.map(chat => (
          <div
            key={chat.id}
            className={`chat-item ${activeChat?.id === chat.id ? 'active' : ''}`}
            onClick={() => onSelect(chat)}
          >
            {editingId === chat.id ? (
              <input
                ref={editRef}
                className="chat-rename-input"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={commitEdit}
                onKeyDown={handleKeyDown}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <div className="chat-item-title" onDoubleClick={(e) => startEdit(e, chat)}>
                {chat.title}
              </div>
            )}
            <div className="chat-item-meta">{chat.document_count} docs</div>
            <div className="chat-item-actions">
              <button
                className="btn-rename"
                onClick={(e) => startEdit(e, chat)}
                title="Rename"
              >
                &#9998;
              </button>
              <button
                className="btn-delete"
                onClick={(e) => { e.stopPropagation(); onDelete(chat.id); }}
                title="Delete"
              >
                ×
              </button>
            </div>
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
