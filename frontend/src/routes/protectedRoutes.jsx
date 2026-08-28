import React from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { isSuperAdminUser } from './navigation'

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

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
    )
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />
}

// Public Route Component (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
        <div className="loading-container">
          <div className="logo-loader">✉️</div>
          <div className="loading-spinner"></div>
          <div className="loading-text">Bylix Email</div>
          <div className="loading-subtext">Loading...</div>
        </div>
      </div>
    )
  }

  return !isAuthenticated ? children : <Navigate to="/" replace />
}

// Helper function to check if user is admin
const SuperAdminRoute = ({ children }) => {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
        <div className="loading-container">
          <div className="logo-loader">✉️</div>
          <div className="loading-spinner"></div>
          <div className="loading-text">Bylix Email</div>
          <div className="loading-subtext">Checking access...</div>
        </div>
      </div>
    )
  }

  return isSuperAdminUser(user) ? children : <Navigate to="/inbox" replace />
}

// Wrapper for detail views that need sidebar

export { ProtectedRoute, PublicRoute, SuperAdminRoute }
