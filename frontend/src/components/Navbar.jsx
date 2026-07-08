import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="logo">
          <div className="logo-icon">FA</div>
          <span>FinAssist AI</span>
        </div>

        <ul className="nav-links">
          <li><a href="#features">Features</a></li>
          <li><a href="#team">Team</a></li>
          {isAuthenticated ? (
            <>
              <li><Link to="/dashboard" className="nav-btn-primary">Dashboard</Link></li>
              <li><button className="nav-btn-outline" onClick={handleLogout} style={{ background: 'none', border: '1px solid var(--border)', borderRadius: '8px', padding: '8px 16px', fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)', cursor: 'pointer' }}>Logout</button></li>
            </>
          ) : (
            <>
              <li><Link to="/login" className="nav-btn-outline">Login</Link></li>
              <li><Link to="/signup" className="nav-btn-primary">Get Started</Link></li>
            </>
          )}
        </ul>
      </div>
    </nav>
  );
}
