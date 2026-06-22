import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Mail, Settings, MessageSquare, FileText, Menu, X, User, LogOut, Zap, BarChart3, Users, Workflow, Bot, Send, CalendarClock, Reply, AtSign, Inbox as InboxIcon, Gauge, Crown, ChevronRight, ShieldCheck, Sparkles, Briefcase, FolderKanban, SlidersHorizontal } from 'lucide-react';

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
import AutoReplyRules from './components/auto-reply/AutoReplyRules';
import InsightsDashboard from './components/insights/InsightsDashboard';
import Relationships from './components/relationships/Relationships';
import Workflows from './components/workflows/Workflows';
import Agents from './components/agents/Agents';
import Campaigns from './components/campaigns/Campaigns';
import ContactDetail from './components/details/ContactDetail';
import CompanyDetail from './components/details/CompanyDetail';
import RiskDetail from './components/details/RiskDetail';
import OpportunityDetail from './components/details/OpportunityDetail';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import VerifyEmail from './components/auth/VerifyEmail';
import ForgotPassword from './components/auth/ForgotPassword';
import ResetPassword from './components/auth/ResetPassword';
import OAuthCallback from './components/auth/OAuthCallback';
import LandingPage from './components/landing/LandingPage';
import Home from './components/Home';
import BillingUpgrade from './components/billing/BillingUpgrade';
import SuperAdminDashboard from './components/admin/SuperAdminDashboard';
import SuperAdminUserAccess from './components/admin/SuperAdminUserAccess';
import SuperAdminFeatureRules from './components/admin/SuperAdminFeatureRules';
import DailyBriefing from './components/briefings/DailyBriefing';
import FollowUpCenter from './components/followups/FollowUpCenter';
import HostedEmailCenter from './components/hosted-email/HostedEmailCenter';
import WorkspaceAssistant from './components/assistant/WorkspaceAssistant';
import SharedInboxCenter from './components/shared-inbox/SharedInboxCenter';
import DeliverabilityCenter from './components/deliverability/DeliverabilityCenter';
import ExecutiveCenter from './components/executive/ExecutiveCenter';

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
          <div className="loading-text">Bylix Email</div>
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
          <div className="loading-text">Bylix Email</div>
          <div className="loading-subtext">Loading...</div>
        </div>
      </div>
    );
  }
  
  return !isAuthenticated ? children : <Navigate to="/" replace />;
};

// Helper function to check if user is admin
const isSuperAdminUser = (user) =>
  Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);

// Main navigation structure with organized groups and dropdowns
const getNavigationGroups = (isAdmin) => {
  const groups = [
    {
      name: 'Inbox',
      icon: InboxIcon,
      expanded: false,
      items: [
        { id: 'inbox', name: 'Inbox', icon: Mail },
      ]
    },
    {
      name: 'Intelligence',
      icon: Sparkles,
      expanded: false,
      items: [
        { id: 'insights', name: 'Insights', icon: BarChart3 },
        { id: 'relationships', name: 'Relationships', icon: Users },
        { id: 'executive', name: 'Executive AI', icon: Crown },
      ]
    },
    {
      name: 'Automation',
      icon: Workflow,
      expanded: false,
      items: [
        { id: 'workflows', name: 'Workflows', icon: Workflow },
        { id: 'agents', name: 'Agents', icon: Bot },
        { id: 'campaigns', name: 'Campaigns', icon: Send },
        { id: 'auto-reply', name: 'Auto-Reply', icon: Zap },
        { id: 'followups', name: 'Follow-Ups', icon: Reply },
      ]
    },
    {
      name: 'Operations',
      icon: Briefcase,
      expanded: false,
      items: [
        { id: 'briefings', name: 'Daily Briefing', icon: CalendarClock },
        { id: 'shared-inbox', name: 'Shared Inbox', icon: InboxIcon },
        { id: 'deliverability', name: 'Deliverability', icon: Gauge },
        { id: 'hosted-email', name: 'Hosted Email', icon: AtSign },
      ]
    },
    {
      name: 'Workspace',
      icon: FolderKanban,
      expanded: false,
      items: [
        { id: 'email-accounts', name: 'Email Accounts', icon: Mail },
        { id: 'agent', name: 'Email Agent', icon: MessageSquare },
        { id: 'drafts', name: 'Drafts', icon: FileText },
        { id: 'prompts', name: 'Prompt Brain', icon: Settings },
      ]
    }
  ];

  if (isAdmin) {
    groups.push({
      name: 'Admin',
      icon: ShieldCheck,
      expanded: false,
      items: [
        { id: 'admin-dashboard', name: 'Dashboard', icon: BarChart3 },
        { id: 'admin-llm', name: 'LLM Ops', icon: Settings },
        { id: 'admin-user-access', name: 'User Access', icon: ShieldCheck },
        { id: 'admin-feature-rules', name: 'Feature Rules', icon: SlidersHorizontal },
      ]
    });
  }

  return groups;
};
const SuperAdminRoute = ({ children }) => {
  const { user, loading } = useAuth();

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
    );
  }

  return isSuperAdminUser(user) ? children : <Navigate to="/inbox" replace />;
};

// Wrapper for detail views that need sidebar
const AppContentWrapper = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState({});
  const { user, logout } = useAuth();
  const location = useLocation();
  
  const isAdmin = isSuperAdminUser(user);
  const navigationGroups = getNavigationGroups(isAdmin);

  return (
    <EmailProvider>
      <PromptProvider>
        <EmailAccountsProvider>
          <div className="app-container">
            {/* Desktop sidebar */}
            <div className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 lg:z-40">
              <SidebarContent
                navigationGroups={navigationGroups}
                activeTab=""
                setActiveTab={() => {}}
                expandedGroups={expandedGroups}
                setExpandedGroups={setExpandedGroups}
                user={user}
                logout={logout}
              />
            </div>

            {/* Main content */}
            <div className="lg:pl-64 flex flex-col flex-1 bg-slate-100 min-h-screen">
              <main className="flex-1 min-h-0">
                <div className="py-4 sm:py-6">
                  <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
                    {children}
                  </div>
                </div>
              </main>
            </div>
            <WorkspaceAssistant page="details" />
          </div>
        </EmailAccountsProvider>
      </PromptProvider>
    </EmailProvider>
  );
};

// Main App Content with Router
const AppContent = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('inbox');
  const [expandedGroups, setExpandedGroups] = useState({});
  const { user, logout } = useAuth();
  const location = useLocation();

  const isAdmin = isSuperAdminUser(user);
  const navigationGroups = getNavigationGroups(isAdmin);

  const renderContent = () => {
    switch (activeTab) {
      case 'inbox':
        return <Inbox />;
      case 'insights':
        return <InsightsDashboard />;
      case 'relationships':
        return <Relationships />;
      case 'workflows':
        return <Workflows />;
      case 'agents':
        return <Agents />;
      case 'campaigns':
        return <Campaigns />;
      case 'briefings':
        return <DailyBriefing />;
      case 'followups':
        return <FollowUpCenter />;
      case 'hosted-email':
        return <HostedEmailCenter />;
      case 'shared-inbox':
        return <SharedInboxCenter />;
      case 'deliverability':
        return <DeliverabilityCenter />;
      case 'executive':
        return <ExecutiveCenter />;
      case 'agent':
        return <EmailAgent />;
      case 'drafts':
        return <DraftManager />;
      case 'auto-reply':
        return <AutoReplyRules />;
      case 'email-accounts':
        return <EmailAccounts />;
      case 'prompts':
        return <PromptManager />;
      case 'admin-dashboard':
        return <SuperAdminDashboard view="dashboard" />;
      case 'admin-llm':
        return <SuperAdminDashboard view="llm" />;
      case 'admin-user-access':
        return <SuperAdminUserAccess />;
      case 'admin-feature-rules':
        return <SuperAdminFeatureRules />;
      case 'super-admin':
        return <SuperAdminDashboard />;
      default:
        return <Inbox />;
    }
  };

  // Close sidebar when route changes
  useEffect(() => {
    setSidebarOpen(false);
  }, [location]);

  // Allow deep-linking to tabs via URL hash (e.g. "/#email-accounts")
  useEffect(() => {
    const hashTab = (location.hash || '').replace('#', '');
    if (!hashTab) return;

    const allNavItems = navigationGroups.flatMap((g) => g.items || []);
    const validTabIds = new Set(allNavItems.map(n => n.id));
    if (validTabIds.has(hashTab)) {
      setActiveTab(hashTab);
    }
    // IMPORTANT: only react to hash changes.
    // If we also depend on `activeTab`, a stale hash (e.g. #email-accounts)
    // will force the UI back to that tab when the user clicks other tabs.
  }, [location.hash]);

  useEffect(() => {
    const allNavItems = navigationGroups.flatMap((g) => g.items || []);
    const activeItem = allNavItems.find((x) => x.id === activeTab);
    const label = activeItem?.name || 'Inbox';
    document.title = `${label} | Bylix Email`;
  }, [activeTab, navigationGroups]);

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
                    navigationGroups={navigationGroups}
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    expandedGroups={expandedGroups}
                    setExpandedGroups={setExpandedGroups}
                    user={user}
                    logout={logout}
                    onItemClick={() => setSidebarOpen(false)}
                  />
                </div>
              </div>
            </div>

            {/* Desktop sidebar */}
            <div className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 lg:z-40">
              <SidebarContent
                navigationGroups={navigationGroups}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                expandedGroups={expandedGroups}
                setExpandedGroups={setExpandedGroups}
                user={user}
                logout={logout}
              />
            </div>

            {/* Main content */}
            <div className="lg:pl-64 flex flex-col flex-1 bg-slate-100 min-h-screen">
              <div className="sticky top-0 z-10 lg:hidden pl-1 pt-1 sm:pl-3 sm:pt-3 bg-slate-100 border-b border-slate-200">
                <button
                  type="button"
                  className="-ml-0.5 -mt-0.5 h-12 w-12 inline-flex items-center justify-center rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                  onClick={() => setSidebarOpen(true)}
                >
                  <Menu className="h-6 w-6" />
                </button>
              </div>

              <main className="flex-1 min-h-0">
                <div className="py-4 sm:py-6">
                  <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
                    {renderContent()}
                  </div>
                </div>
              </main>
            </div>
            <WorkspaceAssistant page={activeTab || 'default'} />
          </div>
        </EmailAccountsProvider>
      </PromptProvider>
    </EmailProvider>
  );
};

// Sidebar Component with Grouped Navigation
const SidebarContent = ({ navigationGroups, activeTab, setActiveTab, expandedGroups, setExpandedGroups, user, logout, onItemClick }) => {
  const [hoverGroup, setHoverGroup] = React.useState(null);
  const isTouch = React.useRef(false);

  // Detect touch device on mount
  React.useEffect(() => {
    isTouch.current = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  }, []);

  const toggleGroup = (groupName) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupName]: !prev[groupName]
    }));
  };

  const handleGroupInteraction = (groupName) => {
    if (isTouch.current) {
      // On touch devices, click toggles
      toggleGroup(groupName);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 border-r border-slate-200 bg-white overflow-visible relative z-40">
      <div className="flex-1 flex flex-col pt-5 pb-4 overflow-visible">
        <div className="flex items-center flex-shrink-0 px-4">
          <Mail className="h-8 w-8 text-indigo-600" />
          <h1 className="ml-3 text-xl font-semibold text-slate-900">Bylix Email</h1>
        </div>

        {/* User Info */}
        {user && (
          <div className="px-4 py-3 border-b border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-indigo-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">
                  {user.full_name || user.email}
                </p>
                <p className="text-xs text-slate-500 truncate">{user.email}</p>
              </div>
            </div>
          </div>
        )}

        <nav className="mt-4 flex-1 px-3 space-y-1">
          {navigationGroups.map((group) => (
            <div
              key={group.name}
              className="space-y-1 relative"
              onMouseEnter={() => !isTouch.current && setHoverGroup(group.name)}
              onMouseLeave={() => setHoverGroup(null)}
            >
              {/* Group Header */}
              {group.items.length > 1 ? (
                <button
                  onClick={() => handleGroupInteraction(group.name)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors group/header"
                >
                  <span className="uppercase tracking-wider flex items-center gap-2">
                    {group.icon ? <group.icon className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    {group.name}
                  </span>
                  <ChevronRight
                    className={`h-4 w-4 transition-transform ${
                      (isTouch.current && expandedGroups[group.name]) || (!isTouch.current && hoverGroup === group.name) ? 'rotate-90' : ''
                    }`}
                  />
                </button>
              ) : (
                <div className="px-3 py-2 text-xs font-semibold text-slate-600 uppercase tracking-wider flex items-center gap-2">
                  {group.icon ? <group.icon className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                  {group.name}
                </div>
              )}

              {/* Group Items */}
              {(group.items.length === 1 || (isTouch.current && expandedGroups[group.name])) && (
                <div className="space-y-1 ml-0">
                  {group.items.map((item) => {
                    const Icon = item.icon || Mail;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          setActiveTab(item.id);
                          onItemClick?.();
                        }}
                        className={`group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg w-full text-left transition-colors ${
                          activeTab === item.id
                            ? 'bg-indigo-600 text-white'
                            : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                        }`}
                      >
                        <Icon
                          className={`flex-shrink-0 h-5 w-5 mr-3 ${
                            activeTab === item.id ? 'text-white' : 'text-slate-500'
                          }`}
                        />
                        {item.name}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Desktop fly-out submenu */}
              {!isTouch.current && group.items.length > 1 && hoverGroup === group.name && (
                <div className="absolute left-full top-0 ml-3 w-64 rounded-xl border border-slate-200 bg-white shadow-xl p-2 z-50 animate-flyoutIn">
                  <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    {group.name}
                  </div>
                  <div className="mt-1 space-y-1">
                    {group.items.map((item) => {
                      const Icon = item.icon || Mail;
                      return (
                        <button
                          key={`${group.name}-${item.id}`}
                          type="button"
                          onClick={() => {
                            setActiveTab(item.id);
                            onItemClick?.();
                            setHoverGroup(null);
                          }}
                          className={`group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg w-full text-left transition-colors ${
                            activeTab === item.id
                              ? 'bg-indigo-600 text-white'
                              : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                          }`}
                        >
                          <Icon
                            className={`flex-shrink-0 h-5 w-5 mr-3 ${
                              activeTab === item.id ? 'text-white' : 'text-slate-500'
                            }`}
                          />
                          {item.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ))}
        </nav>
      </div>

      {/* Logout Button */}
      {user && (
        <div className="flex-shrink-0 flex border-t border-slate-200 p-4">
          <button
            type="button"
            onClick={logout}
            className="flex-shrink-0 w-full group flex items-center px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            <LogOut className="h-5 w-5 text-slate-500 group-hover:text-slate-700" />
            <span className="ml-3 text-sm font-medium">Sign out</span>
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
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/landing" element={
            <PublicRoute>
              <LandingPage />
            </PublicRoute>
          } />
          <Route path="/billing/upgrade" element={
            <ProtectedRoute>
              <BillingUpgrade />
            </ProtectedRoute>
          } />
          <Route path="/admin/super" element={
            <ProtectedRoute>
              <SuperAdminRoute>
                <SuperAdminDashboard />
              </SuperAdminRoute>
            </ProtectedRoute>
          } />
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
          <Route path="/oauth/callback" element={
            <OAuthCallback />
          } />

          {/* Protected Routes */}
          <Route path="/" element={<Home />} />
          <Route path="/inbox" element={
            <ProtectedRoute>
              <AppContent />
            </ProtectedRoute>
          } />
          
          {/* Detail Routes */}
          <Route path="/contacts/:contactId" element={
            <ProtectedRoute>
              <AppContentWrapper>
                <ContactDetail />
              </AppContentWrapper>
            </ProtectedRoute>
          } />
          <Route path="/companies/:companyId" element={
            <ProtectedRoute>
              <AppContentWrapper>
                <CompanyDetail />
              </AppContentWrapper>
            </ProtectedRoute>
          } />
          <Route path="/risks/:riskId" element={
            <ProtectedRoute>
              <AppContentWrapper>
                <RiskDetail />
              </AppContentWrapper>
            </ProtectedRoute>
          } />
          <Route path="/opportunities/:opportunityId" element={
            <ProtectedRoute>
              <AppContentWrapper>
                <OpportunityDetail />
              </AppContentWrapper>
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
export { AppContent };
