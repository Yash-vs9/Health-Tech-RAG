import { Link } from "react-router-dom";

export default function Navbar() {
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
          <li><Link to="/login" className="nav-btn-outline">Login</Link></li>
          <li><Link to="/signup" className="nav-btn-primary">Get Started</Link></li>
        </ul>
      </div>
    </nav>
  );
}
