import { useState, useRef, useEffect } from "react";

export default function Chatbox() {
  const [messages, setMessages] = useState([
    {
      text: "Welcome to FinAssist AI. I can help you analyze bank statements, review transactions, and answer financial questions. Upload a document or ask me anything.",
      sender: "bot",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = () => {
    if (input.trim() === "") return;

    const userMsg = input.trim();
    setMessages((prev) => [...prev, { text: userMsg, sender: "user" }]);
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          text: `I received your query: "${userMsg}". In a fully connected setup, this would be sent to the backend for AI analysis. For now, the backend proxy is configured to forward requests to localhost:8000.`,
          sender: "bot",
        },
      ]);
      setIsTyping(false);
    }, 1200);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-area">
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-icon">AI</div>
          <div>
            <h2>Financial Assistant</h2>
            <span className="chat-status">
              <span className="status-dot"></span> Online
            </span>
          </div>
        </div>
      </div>

      <div className="messages">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.sender === "user" ? "user-message" : "bot-message"}`}
          >
            {msg.sender === "bot" && <div className="msg-avatar">AI</div>}
            <div className="msg-content">
              <div className="msg-text">{msg.text}</div>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="message bot-message">
            <div className="msg-avatar">AI</div>
            <div className="msg-content">
              <div className="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <div className="input-wrapper">
          <input
            type="text"
            placeholder="Ask about your finances..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button onClick={sendMessage} disabled={!input.trim()}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <p className="input-hint">Press Enter to send. Your data is encrypted end-to-end.</p>
      </div>
    </div>
  );
}
