import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { motion } from "framer-motion";
import { Mail, Lock, ArrowRight, AlertCircle } from "lucide-react";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-left">
        <motion.div
          className="auth-brand"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Link to="/" className="logo">
            <div className="logo-icon">FA</div>
            <span>FinAssist AI</span>
          </Link>
        </motion.div>
        <div className="auth-illustration">
          <div className="auth-card-stack">
            <motion.div
              className="floating-card card-1"
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <div className="fc-icon green">$</div>
              <div><strong>$24,580.00</strong><br /><small>Total Balance</small></div>
            </motion.div>
            <motion.div
              className="floating-card card-2"
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              <div className="fc-icon blue">+</div>
              <div><strong>$3,240.00</strong><br /><small>Monthly Income</small></div>
            </motion.div>
            <motion.div
              className="floating-card card-3"
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.7 }}
            >
              <div className="fc-icon purple">AI</div>
              <div><strong>Analysis Ready</strong><br /><small>3 Documents</small></div>
            </motion.div>
          </div>
        </div>
      </div>

      <div className="auth-right">
        <motion.form
          className="auth-form"
          onSubmit={handleLogin}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <h1>Welcome back</h1>
          <p className="auth-subtitle">Sign in to access your banking dashboard</p>

          {error && (
            <motion.div
              className="auth-error"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <AlertCircle size={16} />
              {error}
            </motion.div>
          )}

          <div className="form-group">
            <label>Email address</label>
            <div style={{ position: 'relative' }}>
              <Mail size={18} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{ paddingLeft: 42 }}
              />
            </div>
          </div>

          <div className="form-group">
            <label>Password</label>
            <div style={{ position: 'relative' }}>
              <Lock size={18} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ paddingLeft: 42 }}
              />
            </div>
          </div>

          <button type="submit" className="btn-primary-full" disabled={loading}>
            {loading ? "Signing in..." : (
              <>
                Sign In
                <ArrowRight size={18} style={{ marginLeft: 8, verticalAlign: 'middle' }} />
              </>
            )}
          </button>

          <p className="auth-footer">
            Don't have an account? <Link to="/signup">Create one</Link>
          </p>
        </motion.form>
      </div>
    </div>
  );
}
