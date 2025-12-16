import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import ServicesPage from './pages/ServicesPage';
import SignalsPage from './pages/SignalsPage';
import ContactPage from './pages/ContactPage';
import { Dashboard, LoginPage } from './DashboardPage';

// Scroll to top component for smooth page transitions
const ScrollToTop = () => {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
};

// Protected Route Wrapper
const ProtectedRoute = ({ user, children }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  // Persist user session (basic simulation)
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('nawth_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('nawth_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('nawth_user');
  };

  return (
    <Router>
      <ScrollToTop />
      <Routes>
        {/* Public Pages (Wrapped in Layout) */}
        <Route element={<Layout user={user} />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/services" element={<ServicesPage />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/contact" element={<ContactPage />} />
        </Route>

        {/* Auth Pages (No Header/Footer) */}
        <Route path="/login" element={
          user ? <Navigate to="/dashboard" /> : <LoginPage onLogin={handleLogin} />
        } />

        {/* Protected Dashboard */}
        <Route path="/dashboard" element={
          <ProtectedRoute user={user}>
            <Dashboard user={user} onLogout={handleLogout} />
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
}

export default App;