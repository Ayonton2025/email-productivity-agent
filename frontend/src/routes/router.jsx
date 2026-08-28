import React, { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import AuthProvider from '../providers/AuthProvider';
import ThemeProvider from '../providers/ThemeProvider';
import { AppContent, AppContentWrapper } from '../components/layout/AppShell';
import SuperAdminDashboard from '../components/admin/SuperAdminDashboard';
import BillingUpgrade from '../components/billing/BillingUpgrade';
import CompanyDetail from '../components/details/CompanyDetail';
import ContactDetail from '../components/details/ContactDetail';
import OpportunityDetail from '../components/details/OpportunityDetail';
import RiskDetail from '../components/details/RiskDetail';
import ForgotPassword from '../components/auth/ForgotPassword';
import Login from '../components/auth/Login';
import OAuthCallback from '../components/auth/OAuthCallback';
import Register from '../components/auth/Register';
import ResetPassword from '../components/auth/ResetPassword';
import VerifyEmail from '../components/auth/VerifyEmail';
import Home from '../components/Home';
import LandingPage from '../components/landing/LandingPage';
import { ProtectedRoute, PublicRoute, SuperAdminRoute } from './protectedRoutes';

function AppRouter() {
  const [isLoading, setIsLoading] = useState(true);

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  // Loading screen
  if (isLoading) {
    return (
      <div className="app-container">
        <div className="loading-container">
          <div className="logo-loader">✉️</div>
          <div className="loading-spinner"></div>
          <div className="loading-text">Bylix Email</div>
          <div className="loading-subtext">Your Email Intelligence Platform is loading...</div>
          <div className="loading-features">
            <div className="feature-pill">🤖 Smart Workplace</div>
            <div className="feature-pill">⚡ Instant Processing</div>
            <div className="feature-pill">🎯 Intelligent Organization</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route
              path="/landing"
              element={
                <PublicRoute>
                  <LandingPage />
                </PublicRoute>
              }
            />
            <Route
              path="/billing/upgrade"
              element={
                <ProtectedRoute>
                  <BillingUpgrade />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/super"
              element={
                <ProtectedRoute>
                  <SuperAdminRoute>
                    <SuperAdminDashboard />
                  </SuperAdminRoute>
                </ProtectedRoute>
              }
            />
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <Login />
                </PublicRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicRoute>
                  <Register />
                </PublicRoute>
              }
            />
            <Route
              path="/verify-email"
              element={
                <PublicRoute>
                  <VerifyEmail />
                </PublicRoute>
              }
            />
            <Route
              path="/forgot-password"
              element={
                <PublicRoute>
                  <ForgotPassword />
                </PublicRoute>
              }
            />
            <Route
              path="/reset-password"
              element={
                <PublicRoute>
                  <ResetPassword />
                </PublicRoute>
              }
            />
            <Route path="/oauth/callback" element={<OAuthCallback />} />

            {/* Protected Routes */}
            <Route path="/" element={<Home />} />
            <Route
              path="/inbox"
              element={
                <ProtectedRoute>
                  <AppContent />
                </ProtectedRoute>
              }
            />

            {/* Detail Routes */}
            <Route
              path="/contacts/:contactId"
              element={
                <ProtectedRoute>
                  <AppContentWrapper>
                    <ContactDetail />
                  </AppContentWrapper>
                </ProtectedRoute>
              }
            />
            <Route
              path="/companies/:companyId"
              element={
                <ProtectedRoute>
                  <AppContentWrapper>
                    <CompanyDetail />
                  </AppContentWrapper>
                </ProtectedRoute>
              }
            />
            <Route
              path="/risks/:riskId"
              element={
                <ProtectedRoute>
                  <AppContentWrapper>
                    <RiskDetail />
                  </AppContentWrapper>
                </ProtectedRoute>
              }
            />
            <Route
              path="/opportunities/:opportunityId"
              element={
                <ProtectedRoute>
                  <AppContentWrapper>
                    <OpportunityDetail />
                  </AppContentWrapper>
                </ProtectedRoute>
              }
            />

            {/* Catch all route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default AppRouter;
