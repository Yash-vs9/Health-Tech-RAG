import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import ChatList from "../components/ChatList";
import ChatView from "../components/ChatView";

export default function Dashboard() {
  const { token, user, logout } = useAuth();
  const navigate = useNavigate();

  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const pollingRef = useRef(null);

  useEffect(() => {
    if (!token) {
      navigate("/login");
      return;
    }
    loadChats();
  }, [token]);

  // Poll for document status updates every 5s while any doc is "processing"
  useEffect(() => {
    if (!activeChat) return;

    const hasProcessing = docs.some(d => d.status === 'processing');

    if (hasProcessing && !pollingRef.current) {
      pollingRef.current = setInterval(async () => {
        try {
          const freshDocs = await api.listDocs(token, activeChat.id);
          setDocs((prev) => {
            // Merge: keep in-progress uploads that aren't in freshDocs yet
            const freshMap = new Map(freshDocs.map(d => [d.id, d]));
            const merged = prev.map(d => {
              const updated = freshMap.get(d.id);
              if (updated) { freshMap.delete(d.id); return updated; }
              return d;
            });
            // Add any docs from server we didn't have
            for (const d of freshMap.values()) merged.push(d);
            return merged;
          });
        } catch (err) {
          console.error('Polling failed:', err);
        }
      }, 5000);
    } else if (!hasProcessing && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [docs, activeChat, token]);

  const loadChats = async () => {
    try {
      const data = await api.listChats(token);
      setChats(data);
    } catch (err) {
      console.error("Failed to load chats:", err);
    } finally {
      setInitialLoading(false);
    }
  };

  const loadChatData = useCallback(async (chat) => {
    setActiveChat(chat);
    setMessages([]);
    setDocs([]);
    try {
      const [historyData, docsData] = await Promise.all([
        api.getHistory(token, chat.id),
        api.listDocs(token, chat.id),
      ]);
      setMessages(historyData.messages || []);
      setDocs(docsData);
    } catch (err) {
      console.error("Failed to load chat data:", err);
    }
  }, [token]);

  const handleNewChat = async () => {
    try {
      const chat = await api.createChat(token, "New Chat");
      setChats((prev) => [chat, ...prev]);
      loadChatData(chat);
    } catch (err) {
      console.error("Failed to create chat:", err);
    }
  };

  const handleSelectChat = (chat) => {
    loadChatData(chat);
  };

  const handleDeleteChat = async (chatId) => {
    try {
      await api.deleteChat(token, chatId);
      setChats((prev) => prev.filter((c) => c.id !== chatId));
      if (activeChat?.id === chatId) {
        setActiveChat(null);
        setMessages([]);
        setDocs([]);
      }
    } catch (err) {
      console.error("Failed to delete chat:", err);
    }
  };

  const handleRenameChat = async (chatId, newTitle) => {
    if (!newTitle.trim()) return;
    try {
      const updated = await api.renameChat(token, chatId, newTitle.trim());
      setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, title: updated.title } : c)));
      if (activeChat?.id === chatId) {
        setActiveChat((prev) => ({ ...prev, title: updated.title }));
      }
    } catch (err) {
      console.error("Failed to rename chat:", err);
    }
  };

  const handleSendMessage = async (question) => {
    if (!activeChat) return;
    const userMsg = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    try {
      const response = await api.sendMessage(token, activeChat.id, question);
      const assistantMsg = {
        role: "assistant",
        content: response.answer || response.content,
        sources: response.sources || [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error("Failed to send message:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (file) => {
    if (!activeChat) return;
    try {
      const doc = await api.uploadDoc(token, activeChat.id, file);
      setDocs((prev) => [...prev, doc]);
    } catch (err) {
      console.error("Failed to upload document:", err);
      throw err;
    }
  };

  const handleDeleteDoc = async (docId) => {
    if (!activeChat) return;
    try {
      await api.deleteDoc(token, activeChat.id, docId);
      setDocs((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (!token) return null;

  return (
    <div className="dashboard">
      <div className={`chat-list-panel ${sidebarOpen ? 'open' : 'closed'}`}>
        <ChatList
          chats={chats}
          activeChat={activeChat}
          onSelect={handleSelectChat}
          onNew={handleNewChat}
          onDelete={handleDeleteChat}
          onRename={handleRenameChat}
          user={user}
          onLogout={handleLogout}
        />
      </div>
      <div className="main-area">
        <div className="sidebar-edge-toggle" onClick={() => setSidebarOpen((v) => !v)} title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {sidebarOpen ? (
              <>
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
              </>
            ) : (
              <>
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="15" y1="3" x2="15" y2="21" />
              </>
            )}
          </svg>
        </div>
        <ChatView
          chat={activeChat}
          messages={messages}
          docs={docs}
          onSend={handleSendMessage}
          onUpload={handleUpload}
          onDeleteDoc={handleDeleteDoc}
          onRename={handleRenameChat}
          loading={loading}
        />
      </div>
    </div>
  );
}
