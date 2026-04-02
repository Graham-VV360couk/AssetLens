import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('assetlens_token');
    if (token) {
      api.get('/api/auth/me')
        .then(res => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('assetlens_token');
          localStorage.removeItem('assetlens_refresh_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.post('/api/auth/login', { email, password });
    localStorage.setItem('assetlens_token', res.data.access_token);
    localStorage.setItem('assetlens_refresh_token', res.data.refresh_token);
    localStorage.setItem('assetlens_user_email', res.data.user.email);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const register = useCallback(async (data) => {
    const res = await api.post('/api/auth/register', data);
    localStorage.setItem('assetlens_token', res.data.access_token);
    localStorage.setItem('assetlens_refresh_token', res.data.refresh_token);
    localStorage.setItem('assetlens_user_email', res.data.user.email);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('assetlens_token');
    localStorage.removeItem('assetlens_refresh_token');
    localStorage.removeItem('assetlens_user_email');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
