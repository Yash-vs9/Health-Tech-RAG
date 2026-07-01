import { useNavigate } from "react-router-dom";

export default function Sidebar() {
  const navigate = useNavigate();

  return (
    <div className="sidebar">

      <h2>HealthTech AI</h2>

      <button className="new-chat-btn">
        + New Chat
      </button>

      <div className="sidebar-section">
        <h3>Previous Chats</h3>

        <p>🩺 Heart Report</p>
        <p>🩸 Blood Test</p>
        <p>💊 Diabetes Report</p>
      </div>

      <div className="sidebar-section">
        <h3>Upload Documents</h3>

        <input
          type="file"
          accept=".pdf"
        />
      </div>

      <div className="sidebar-section">
        <h3>Uploaded Files</h3>

        <p>report.pdf</p>
        <p>blood-test.pdf</p>
      </div>

      <button
        className="upload-btn"
        onClick={() => navigate("/")}
      >
        Logout
      </button>

    </div>
  );
}
   import { useNavigate } from "react-router-dom";

export default function Sidebar() {
  const navigate = useNavigate();

  return (
    <div className="sidebar">

      <h2>HealthTech AI</h2>

      <button className="new-chat-btn">
        + New Chat
      </button>

      <div className="sidebar-section">
        <h3>Previous Chats</h3>

        <p>🩺 Heart Report</p>
        <p>🩸 Blood Test</p>
        <p>💊 Diabetes Report</p>
      </div>

      <div className="sidebar-section">
        <h3>Upload Documents</h3>

        <input
          type="file"
          accept=".pdf"
        />
      </div>

      <div className="sidebar-section">
        <h3>Uploaded Files</h3>

        <p>report.pdf</p>
        <p>blood-test.pdf</p>
      </div>

      <button
        className="logout-btn"
        onClick={() => navigate("/")}
      >
        Logout
      </button>

    </div>
  );
}  