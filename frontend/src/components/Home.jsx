import React from 'react';
import { useAuth } from '../context/AuthContext';
import LandingPage from './landing/LandingPage';
import { AppContent } from '../App';

/**
 * Home Component
 * Routes to either the landing page (unauthenticated)
 * or the main dashboard (authenticated)
 */
export const Home = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
        <div className="loading-container">
          <div className="logo-loader">✉️</div>
          <div className="loading-spinner"></div>
          <div className="loading-text">Bylix Email</div>
          <div className="loading-subtext">Loading your workspace...</div>
        </div>
      </div>
    );
  }

  return isAuthenticated ? <AppContent /> : <LandingPage />;
};

export default Home;
