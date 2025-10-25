import React, { useState } from 'react';
import LandingPage from './LandingPage';
import { Dashboard, LoginPage } from './DashboardPage';

// Enum for managing different views/pages
const AppState = {
  LANDING: 'LANDING',
  LOGIN: 'LOGIN',
  DASHBOARD: 'DASHBOARD',
};

function App() {
  // The app starts on the landing page
  const [appState, setAppState] = useState(AppState.LANDING);
  const [user, setUser] = useState(null);

  const handleAccessDashboard = () => {
    // If user is already logged in, go straight to dashboard
    if (user) {
      setAppState(AppState.DASHBOARD);
    } else {
      setAppState(AppState.LOGIN);
    }
  };
  
  const handleLogin = (userData) => {
    setUser(userData);
    setAppState(AppState.DASHBOARD);
  };
  
  const handleLogout = () => {
    setUser(null);
    // After logging out, user goes back to the main landing page
    setAppState(AppState.LANDING);
  };

  // Render component based on the current state
  switch (appState) {
    case AppState.LOGIN:
      return <LoginPage onLogin={handleLogin} />;
    
    case AppState.DASHBOARD:
      return <Dashboard user={user} onLogout={handleLogout} />;
      
    case AppState.LANDING:
    default:
      return <LandingPage onAccessDashboard={handleAccessDashboard} />;
  }
}

export default App;
