import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="logo">
        <h2>HealthTech AI</h2>
      </div>

      <ul className="nav-links">
        <li><a href="#features">Features</a></li>
        <li><a href="#team">Team</a></li>
        <li><Link to="/login">Login</Link></li>
        <li><Link to="/signup">Signup</Link></li>
      </ul>
    </nav>
  );
}