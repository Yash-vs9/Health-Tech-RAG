import { useState, useEffect, useCallback } from "react";
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

  useEffect(() => {
    if (!token) {
      navigate("/login");
      return;
    }
    loadChats();
  }, [token]);

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
      <ChatList
        chats={chats}
        activeChat={activeChat}
        onSelect={handleSelectChat}
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
