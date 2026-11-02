import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AppLayout from './components/AppLayout';

import Login from './pages/Login';
import Register from './pages/Register';
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Mentor = lazy(() => import('./pages/Mentor'));
const Notes = lazy(() => import('./pages/Notes'));
const Quiz = lazy(() => import('./pages/Quiz'));
const StudyMaterial = lazy(() => import('./pages/StudyMaterial'));
const Planner = lazy(() => import('./pages/Planner'));
const Profile = lazy(() => import('./pages/Profile'));

function ProtectedRoute({ children }) {
  const { student, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading-spinner" />
      </div>
    );
  }
  if (!student) return <Navigate to="/login" replace />;
  return children;
}

function PublicRoute({ children }) {
  const { student, loading } = useAuth();
  if (loading) return null;
  if (student) return <Navigate to="/" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Suspense fallback={<div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}><div className="loading-spinner" /></div>}>
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="mentor" element={<Mentor />} />
        <Route path="notes" element={<Notes />} />
        <Route path="quiz" element={<Quiz />} />
        <Route path="study-material" element={<StudyMaterial />} />
        <Route path="planner" element={<Planner />} />
        <Route path="profile" element={<Profile />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
