import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import ServicesPage from './pages/ServicesPage';
import SignalsPage from './pages/SignalsPage';
import ContactPage from './pages/ContactPage';
import { Dashboard, LoginPage } from './DashboardPage';

<<<<<<< HEAD
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

=======
const AppState = {
  LANDING: 'LANDING',
  LOGIN: 'LOGIN',
  DASHBOARD: 'DASHBOARD',
};

function App() {
  const [appState, setAppState] = useState(AppState.LANDING);
  const [user, setUser] = useState(null);

  const handleAccessDashboard = () => {
    if (user) {
      setAppState(AppState.DASHBOARD);
    } else {
      setAppState(AppState.LOGIN);
    }
  };
  
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('nawth_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
<<<<<<< HEAD
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
=======
    setAppState(AppState.LANDING);
  };

  // NEW: Handler to go back to the landing page
  const handleBackToLanding = () => {
    setAppState(AppState.LANDING);
  };

  switch (appState) {
    case AppState.LOGIN:
      // Pass the new onBack prop here
      return <LoginPage onLogin={handleLogin} onBack={handleBackToLanding} />;
    
    case AppState.DASHBOARD:
      return <Dashboard user={user} onLogout={handleLogout} />;
      
    case AppState.LANDING:
    default:
      return <LandingPage onAccessDashboard={handleAccessDashboard} />;
  }
>>>>>>> 03b255c (v3: upgraded trading engine, improved performance tracking, refactored backtesting module)
}

export default App;