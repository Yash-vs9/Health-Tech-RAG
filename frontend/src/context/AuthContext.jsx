import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token && !user) {
      setLoading(true);
      api.me(token)
        .then((data) => {
          setUser(data);
          localStorage.setItem('user', JSON.stringify(data));
        })
        .catch(() => {
          logout();
        })
        .finally(() => setLoading(false));
    }
  }, [token]);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);
    const userData = { id: data.user_id, email: data.email, full_name: data.full_name };
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
    return data;
  };

  const signup = async (email, password, full_name) => {
    const data = await api.signup(email, password, full_name);
    if (data.access_token) {
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      const userData = { id: data.user_id, email: data.email };
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
    }
    return data;
  };

  const logout = () => {
    if (token) {
      api.logout(token).catch(() => {});
    }
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, login, signup, logout, loading, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
