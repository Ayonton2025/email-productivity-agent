import { Navigate, Route, Routes } from 'react-router-dom'

import BillingUpgrade from './components/billing/BillingUpgrade'
import CompanyDetail from './components/details/CompanyDetail'
import ContactDetail from './components/details/ContactDetail'
import OpportunityDetail from './components/details/OpportunityDetail'
import RiskDetail from './components/details/RiskDetail'
import ForgotPassword from './components/auth/ForgotPassword'
import Login from './components/auth/Login'
import OAuthCallback from './components/auth/OAuthCallback'
import Register from './components/auth/Register'
import ResetPassword from './components/auth/ResetPassword'
import VerifyEmail from './components/auth/VerifyEmail'
import Home from './components/Home'
import LandingPage from './components/landing/LandingPage'
import SuperAdminDashboard from './components/admin/SuperAdminDashboard'

export default function ApplicationRoutes({
  AppContent,
  AppContentWrapper,
  ProtectedRoute,
  PublicRoute,
  SuperAdminRoute,
}) {
  return (
    <Routes>
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
      <Route path="/" element={<Home />} />
      <Route
        path="/inbox"
        element={
          <ProtectedRoute>
            <AppContent />
          </ProtectedRoute>
        }
      />
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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
