import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { motion } from "framer-motion";
import { LogOut, LayoutDashboard } from "lucide-react";

export default function Navbar() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <motion.nav
      className="navbar"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <div className="nav-container">
        <Link to="/" className="logo">
          <div className="logo-icon">FA</div>
          <span>FinAssist AI</span>
        </Link>

        <ul className="nav-links">
          <li><a href="#features">Features</a></li>
          <li><a href="#team">Team</a></li>
          {isAuthenticated ? (
            <>
              <li>
                <Link to="/dashboard" className="nav-btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <LayoutDashboard size={16} />
                  Dashboard
                </Link>
              </li>
              <li>
                <button
                  className="nav-btn-outline"
                  onClick={handleLogout}
                  style={{ background: 'none', border: '1px solid var(--border-hover)', borderRadius: '10px', padding: '8px 18px', fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px', transition: 'all 0.25s' }}
                >
                  <LogOut size={15} />
                  Logout
                </button>
              </li>
            </>
          ) : (
            <>
              <li><Link to="/login" className="nav-btn-outline">Login</Link></li>
              <li><Link to="/signup" className="nav-btn-primary">Get Started</Link></li>
            </>
          )}
        </ul>
      </div>
    </motion.nav>
  );
}
