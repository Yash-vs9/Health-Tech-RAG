import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

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
        <div className="auth-brand">
          <div className="logo">
            <div className="logo-icon">FA</div>
            <span>FinAssist AI</span>
          </div>
        </div>
        <div className="auth-illustration">
          <div className="auth-card-stack">
            <div className="floating-card card-1">
              <div className="fc-icon green">$</div>
              <div><strong>$24,580.00</strong><br /><small>Total Balance</small></div>
            </div>
            <div className="floating-card card-2">
              <div className="fc-icon blue">+</div>
              <div><strong>$3,240.00</strong><br /><small>Monthly Income</small></div>
            </div>
            <div className="floating-card card-3">
              <div className="fc-icon purple">AI</div>
              <div><strong>Analysis Ready</strong><br /><small>3 Documents</small></div>
            </div>
          </div>
        </div>
      </div>

      <div className="auth-right">
        <form className="auth-form" onSubmit={handleLogin}>
          <h1>Welcome back</h1>
          <p className="auth-subtitle">Sign in to access your banking dashboard</p>

          {error && <div className="auth-error">{error}</div>}

          <div className="form-group">
            <label>Email address</label>
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-primary-full" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>

          <p className="auth-footer">
            Don't have an account? <Link to="/signup">Create one</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
