import React, { useState, useEffect } from 'react';
import { api } from './api';
import Login from './components/Login';
import ChatList from './components/ChatList';
import ChatView from './components/ChatView';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [docs, setDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Load user on mount
  useEffect(() => {
    if (token) {
      api.me(token).then(u => setUser(u)).catch(() => {
        localStorage.removeItem('token');
        setToken(null);
      });
    }
  }, [token]);

  // Load chats when logged in
  useEffect(() => {
    if (token) {
      api.listChats(token).then(c => setChats(c)).catch(() => {});
    }
  }, [token]);

  // Load messages + docs when chat selected
  useEffect(() => {
    if (token && activeChat) {
      api.getHistory(token, activeChat.id).then(h => {
        setMessages(h.messages || []);
        setDocs(h.documents || []);
      }).catch(() => {});
    }
  }, [token, activeChat]);

  const handleLogin = (t) => {
    localStorage.setItem('token', t);
    setToken(t);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setChats([]);
    setActiveChat(null);
  };

  const handleNewChat = async () => {
    const chat = await api.createChat(token);
    setChats([chat, ...chats]);
    setActiveChat(chat);
  };

  const handleDeleteChat = async (id) => {
    await api.deleteChat(token, id);
    setChats(chats.filter(c => c.id !== id));
    if (activeChat?.id === id) {
      setActiveChat(null);
      setMessages([]);
      setDocs([]);
    }
  };

  const handleSendMessage = async (question) => {
    if (!activeChat) return;
    setLoading(true);
    try {
      const userMsg = { role: 'user', content: question, created_at: new Date().toISOString() };
      setMessages(prev => [...prev, userMsg]);

      const result = await api.sendMessage(token, activeChat.id, question);
      setMessages(prev => [...prev.slice(0, -1), userMsg, result]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}`, created_at: new Date().toISOString() }]);
    }
    setLoading(false);
  };

  const handleUpload = async (file) => {
    if (!activeChat) return;
    const doc = await api.uploadDoc(token, activeChat.id, file);
    setDocs(prev => [...prev, doc]);
  };

  const handleDeleteDoc = async (docId) => {
    if (!activeChat) return;
    await api.deleteDoc(token, activeChat.id, docId);
    setDocs(prev => prev.filter(d => d.id !== docId));
  };

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app">
      <ChatList
        chats={chats}
        activeChat={activeChat}
        onSelect={setActiveChat}
        onNew={handleNewChat}
        onDelete={handleDeleteChat}
        user={user}
        onLogout={handleLogout}
      />
      <ChatView
        chat={activeChat}
        messages={messages}
        docs={docs}
        onSend={handleSendMessage}
        onUpload={handleUpload}
        onDeleteDoc={handleDeleteDoc}
        loading={loading}
      />
    </div>
  );
}
