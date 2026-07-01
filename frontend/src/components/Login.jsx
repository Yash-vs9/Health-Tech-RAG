import React, { useState } from 'react';
import { api } from '../api';

export default function Login({ onLogin }) {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = isSignup
        ? await api.signup(email, password, name)
        : await api.login(email, password);
      onLogin(result.access_token);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Mortgage RAG</h1>
        <p className="subtitle">Document Intelligence Assistant</p>

        <form onSubmit={handleSubmit}>
          {isSignup && (
            <input
              type="text"
              placeholder="Full Name"
              value={name}
              onChange={e => setName(e.target.value)}
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={e => setPassword(e.target.value)}
            minLength={8}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Loading...' : isSignup ? 'Sign Up' : 'Log In'}
          </button>
        </form>

        {error && <p className="error">{error}</p>}

        <p className="toggle">
          {isSignup ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button className="link-btn" onClick={() => setIsSignup(!isSignup)}>
            {isSignup ? 'Log In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  );
}
