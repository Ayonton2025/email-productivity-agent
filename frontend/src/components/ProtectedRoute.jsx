import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  React.useEffect(() => {
    console.log('🔒 [ProtectedRoute] Checking authentication:', {
      isAuthenticated,
      loading,
      currentPath: location.pathname
    });

    if (!loading && !isAuthenticated) {
      console.log('🚫 [ProtectedRoute] User not authenticated, redirecting to login');
      // Store the attempted URL for redirect after login
      const redirectUrl = location.pathname + location.search;
      if (redirectUrl !== '/login') {
        sessionStorage.setItem('redirectUrl', redirectUrl);
      }
      navigate('/login', { replace: true });
    }
  }, [isAuthenticated, loading, navigate, location]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-indigo-50 to-purple-100">
        <div className="loading-container">
          <div className="logo-loader">🔒</div>
          <div className="loading-spinner"></div>
          <div className="loading-text">Checking Authentication</div>
          <div className="loading-subtext">Please wait while we verify your session...</div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-indigo-50 to-purple-100">
        <div className="loading-container">
          <div className="logo-loader">🚫</div>
          <div className="loading-text">Access Denied</div>
          <div className="loading-subtext">Redirecting to login page...</div>
        </div>
      </div>
    );
  }

  console.log('✅ [ProtectedRoute] User authenticated, rendering children');
  return children;
};

export default ProtectedRoute;