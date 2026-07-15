import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Pencil, X, LogOut } from 'lucide-react';

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
        <motion.button
          className="btn-new"
          onClick={onNew}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Plus size={16} />
          New
        </motion.button>
      </div>

      <div className="chat-items">
        <AnimatePresence>
          {chats.length === 0 && (
            <p className="empty">No chats yet.</p>
          )}
          {chats.map((chat, i) => (
            <motion.div
              key={chat.id}
              className={`chat-item ${activeChat?.id === chat.id ? 'active' : ''}`}
              onClick={() => onSelect(chat)}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2, delay: i * 0.03 }}
              layout
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
                  <Pencil size={13} />
                </button>
                <button
                  className="btn-delete"
                  onClick={(e) => { e.stopPropagation(); onDelete(chat.id); }}
                  title="Delete"
                >
                  <X size={15} />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <div className="chat-list-footer">
        <span>{user?.email || 'User'}</span>
        <button className="btn-logout" onClick={onLogout} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <LogOut size={14} />
          Logout
        </button>
      </div>
    </div>
  );
}
