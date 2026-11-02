import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { loginStudent, registerStudent, getMe } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('eduverse_token');
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then(setStudent)
      .catch(() => {
        localStorage.removeItem('eduverse_token');
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await loginStudent({ email, password });
    localStorage.setItem('eduverse_token', data.access_token);
    setStudent(data.student);
    return data.student;
  }, []);

  const register = useCallback(async (payload) => {
    const data = await registerStudent(payload);
    localStorage.setItem('eduverse_token', data.access_token);
    setStudent(data.student);
    return data.student;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('eduverse_token');
    setStudent(null);
  }, []);

  const refreshStudent = useCallback(async () => {
    const data = await getMe();
    setStudent(data);
    return data;
  }, []);

  return (
    <AuthContext.Provider value={{ student, loading, login, register, logout, refreshStudent }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
