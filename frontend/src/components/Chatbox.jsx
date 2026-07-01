import { useState } from "react";

export default function Chatbox() {
  const [messages, setMessages] = useState([
    {
      text: "👋 Welcome to Health-Tech AI Assistant. Upload your medical report or ask any health-related question.",
      sender: "bot",
    },
  ]);

  const [input, setInput] = useState("");

  const sendMessage = () => {
    if (input.trim() === "") return;

    setMessages([
      ...messages,
      {
        text: input,
        sender: "user",
      },
    ]);

    setInput("");
  };

  return (
    <div className="chat-area">

      <div className="chat-header">
        <h2>Health-Tech AI Assistant</h2>
      </div>

      <div className="messages">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={msg.sender === "user" ? "user-message" : "bot-message"}
          >
            {msg.text}
          </div>
        ))}
      </div>

      <div className="chat-input">
        <input
          type="text"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />

        <button onClick={sendMessage}>
          Send
        </button>
      </div>

    </div>
  );
}
