import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Mail, Settings, MessageSquare, FileText, Menu, X, User, LogOut } from 'lucide-react';

// Context Providers
import { AuthProvider, useAuth } from './context/AuthContext';
import { EmailProvider } from './context/EmailContext';
import { PromptProvider } from './context/PromptContext';
import { EmailAccountsProvider } from './context/EmailAccountsContext';

// Components
import Inbox from './components/inbox/Inbox';
import PromptManager from './components/prompts/PromptManager';
import EmailAgent from './components/agent/EmailAgent';
import DraftManager from './components/drafts/DraftManager';
import EmailAccounts from './components/email-accounts/EmailAccounts';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import VerifyEmail from './components/auth/VerifyEmail';
import ForgotPassword from './components/auth/ForgotPassword';
import ResetPassword from './components/auth/ResetPassword';

import './styles/globals.css';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
        <div className="loading-container">
          <div className="logo-loader">✉️</div>
          <div className="loading-spinner"></div>
          <div className="loading-text">InboxAI</div>
          <div className="loading-subtext">Loading your workspace...</div>
        </div>
      </div>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

// Public Route Component (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
        <div className="loading-container">
          <div className="logo-loader">✉️</div>
          <div className="loading-spinner"></div>
          <div className="loading-text">InboxAI</div>
          <div className="loading-subtext">Loading...</div>
        </div>
      </div>
    );
  }
  
  return !isAuthenticated ? children : <Navigate to="/" replace />;
};

// Main App Content with Router
const AppContent = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('inbox');
  const { user, logout } = useAuth();
  const location = useLocation();

  const navigation = [
    { id: 'inbox', name: 'Inbox', icon: Mail },
    { id: 'agent', name: 'Email Agent', icon: MessageSquare },
    { id: 'drafts', name: 'Drafts', icon: FileText },
    { id: 'email-accounts', name: 'Email Accounts', icon: Mail },
    { id: 'prompts', name: 'Prompt Brain', icon: Settings },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'inbox':
        return <Inbox />;
      case 'agent':
        return <EmailAgent />;
      case 'drafts':
        return <DraftManager />;
      case 'email-accounts':
        return <EmailAccounts />;
      case 'prompts':
        return <PromptManager />;
      default:
        return <Inbox />;
    }
  };

  // Close sidebar when route changes
  useEffect(() => {
    setSidebarOpen(false);
  }, [location]);

  return (
    <EmailProvider>
      <PromptProvider>
        <EmailAccountsProvider>
          <div className="app-container">
            {/* Mobile sidebar */}
            <div className={`lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
              <div className="fixed inset-0 flex z-40">
                <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
                <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white">
                  <div className="absolute top-0 right-0 -mr-12 pt-2">
                    <button
                      className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                      onClick={() => setSidebarOpen(false)}
                    >
                      <X className="h-6 w-6 text-white" />
                    </button>
                  </div>
                  <SidebarContent
                    navigation={navigation}
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    user={user}
                    logout={logout}
                    onItemClick={() => setSidebarOpen(false)}
                  />
                </div>
              </div>
            </div>

            {/* Desktop sidebar */}
            <div className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0">
              <SidebarContent
                navigation={navigation}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                user={user}
                logout={logout}
              />
            </div>

            {/* Main content */}
            <div className="lg:pl-64 flex flex-col flex-1">
              <div className="sticky top-0 z-10 lg:hidden pl-1 pt-1 sm:pl-3 sm:pt-3 bg-gray-100">
                <button
                  className="-ml-0.5 -mt-0.5 h-12 w-12 inline-flex items-center justify-center rounded-md text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
                  onClick={() => setSidebarOpen(true)}
                >
                  <Menu className="h-6 w-6" />
                </button>
              </div>

              <main className="flex-1">
                <div className="py-6">
                  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    {renderContent()}
                  </div>
                </div>
              </main>
            </div>
          </div>
        </EmailAccountsProvider>
      </PromptProvider>
    </EmailProvider>
  );
};

// Sidebar Component
const SidebarContent = ({ navigation, activeTab, setActiveTab, user, logout, onItemClick }) => {
  return (
    <div className="flex-1 flex flex-col min-h-0 border-r border-gray-200 bg-white">
      <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
        <div className="flex items-center flex-shrink-0 px-4">
          <Mail className="h-8 w-8 text-indigo-600" />
          <h1 className="ml-3 text-xl font-semibold text-gray-900">InboxAI</h1>
        </div>

        {/* User Info */}
        {user && (
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-indigo-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user.full_name || user.email}
                </p>
                <p className="text-xs text-gray-500 truncate">{user.email}</p>
              </div>
            </div>
          </div>
        )}

        <nav className="mt-4 flex-1 px-4 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  onItemClick && onItemClick();
                }}
                className={`group flex items-center px-3 py-2 text-sm font-medium rounded-md w-full text-left ${
                  activeTab === item.id
                    ? 'bg-indigo-50 text-indigo-700 border-indigo-500 border'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon className={`flex-shrink-0 h-5 w-5 mr-3 ${
                  activeTab === item.id ? 'text-indigo-500' : 'text-gray-400'
                }`} />
                {item.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Logout Button */}
      {user && (
        <div className="flex-shrink-0 flex border-t border-gray-200 p-4">
          <button
            onClick={logout}
            className="flex-shrink-0 w-full group block"
          >
            <div className="flex items-center">
              <LogOut className="h-5 w-5 text-gray-400 group-hover:text-gray-500" />
              <span className="ml-3 text-sm font-medium text-gray-700 group-hover:text-gray-900">
                Sign out
              </span>
            </div>
          </button>
        </div>
      )}
    </div>
  );
};

// Main App Component
function App() {
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
          <div className="loading-text">InboxAI</div>
          <div className="loading-subtext">Your AI-powered email workspace is loading...</div>
          <div className="loading-features">
            <div className="feature-pill">🤖 Smart AI Assistant</div>
            <div className="feature-pill">⚡ Instant Processing</div>
            <div className="feature-pill">🎯 Intelligent Organization</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={
            <PublicRoute>
              <Login />
            </PublicRoute>
          } />
          <Route path="/register" element={
            <PublicRoute>
              <Register />
            </PublicRoute>
          } />
          <Route path="/verify-email" element={
            <PublicRoute>
              <VerifyEmail />
            </PublicRoute>
          } />
          <Route path="/forgot-password" element={
            <PublicRoute>
              <ForgotPassword />
            </PublicRoute>
          } />
          <Route path="/reset-password" element={
            <PublicRoute>
              <ResetPassword />
            </PublicRoute>
          } />

          {/* Protected Routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <AppContent />
            </ProtectedRoute>
          } />

          {/* Catch all route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;