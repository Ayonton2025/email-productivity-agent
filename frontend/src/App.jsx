import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Navigate, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'

// Context Providers
import { AuthProvider, useAuth } from './context/AuthContext'
import { EmailProvider } from './context/EmailContext'
import { PromptProvider } from './context/PromptContext'
import { EmailAccountsProvider } from './context/EmailAccountsContext'

// Components
import Inbox from './components/inbox/Inbox'
import PromptManager from './components/prompts/PromptManager'
import EmailAgent from './components/agent/EmailAgent'
import DraftManager from './components/drafts/DraftManager'
import EmailAccounts from './components/email-accounts/EmailAccounts'
import AutoReplyRules from './components/auto-reply/AutoReplyRules'
import InsightsDashboard from './components/insights/InsightsDashboard'
import Relationships from './components/relationships/Relationships'
import Workflows from './components/workflows/Workflows'
import Agents from './components/agents/Agents'
import Campaigns from './components/campaigns/Campaigns'
import SuperAdminDashboard from './components/admin/SuperAdminDashboard'
import SuperAdminUserAccess from './components/admin/SuperAdminUserAccess'
import SuperAdminFeatureRules from './components/admin/SuperAdminFeatureRules'
import DailyBriefing from './components/briefings/DailyBriefing'
import FollowUpCenter from './components/followups/FollowUpCenter'
import HostedEmailCenter from './components/hosted-email/HostedEmailCenter'
import WorkspaceAssistant from './components/assistant/WorkspaceAssistant'
import SharedInboxCenter from './components/shared-inbox/SharedInboxCenter'
import DeliverabilityCenter from './components/deliverability/DeliverabilityCenter'
import ExecutiveCenter from './components/executive/ExecutiveCenter'
import AuthLoadingScreen from './components/auth/AuthLoadingScreen'
import SidebarContent from './components/layout/SidebarContent'
import { getNavigationGroups } from './navigation'
import ApplicationRoutes from './routes'

import './styles/globals.css'

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return <AuthLoadingScreen message="Loading your workspace..." />
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />
}

// Public Route Component (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return <AuthLoadingScreen />
  }

  return !isAuthenticated ? children : <Navigate to="/" replace />
}

const isSuperAdminUser = (user) => Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser)

const SuperAdminRoute = ({ children }) => {
  const { user, loading } = useAuth()

  if (loading) {
    return <AuthLoadingScreen message="Checking access..." />
  }

  return isSuperAdminUser(user) ? children : <Navigate to="/inbox" replace />
}

// Wrapper for detail views that need sidebar
const AppContentWrapper = ({ children }) => {
  const [expandedGroups, setExpandedGroups] = useState({})
  const { user, logout } = useAuth()

  const isAdmin = isSuperAdminUser(user)
  const navigationGroups = getNavigationGroups(isAdmin)

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
                  <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">{children}</div>
                </div>
              </main>
            </div>
            <WorkspaceAssistant page="details" />
          </div>
        </EmailAccountsProvider>
      </PromptProvider>
    </EmailProvider>
  )
}

// Main App Content with Router
const AppContent = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('inbox')
  const [expandedGroups, setExpandedGroups] = useState({})
  const { user, logout } = useAuth()
  const location = useLocation()

  const isAdmin = isSuperAdminUser(user)
  const navigationGroups = getNavigationGroups(isAdmin)

  const renderContent = () => {
    switch (activeTab) {
      case 'inbox':
        return <Inbox />
      case 'insights':
        return <InsightsDashboard />
      case 'relationships':
        return <Relationships />
      case 'workflows':
        return <Workflows />
      case 'agents':
        return <Agents />
      case 'campaigns':
        return <Campaigns />
      case 'briefings':
        return <DailyBriefing />
      case 'followups':
        return <FollowUpCenter />
      case 'hosted-email':
        return <HostedEmailCenter />
      case 'shared-inbox':
        return <SharedInboxCenter />
      case 'deliverability':
        return <DeliverabilityCenter />
      case 'executive':
        return <ExecutiveCenter />
      case 'agent':
        return <EmailAgent />
      case 'drafts':
        return <DraftManager />
      case 'auto-reply':
        return <AutoReplyRules />
      case 'email-accounts':
        return <EmailAccounts />
      case 'prompts':
        return <PromptManager />
      case 'admin-dashboard':
        return <SuperAdminDashboard view="dashboard" />
      case 'admin-llm':
        return <SuperAdminDashboard view="llm" />
      case 'admin-user-access':
        return <SuperAdminUserAccess />
      case 'admin-feature-rules':
        return <SuperAdminFeatureRules />
      case 'super-admin':
        return <SuperAdminDashboard />
      default:
        return <Inbox />
    }
  }

  // Close sidebar when route changes
  useEffect(() => {
    setSidebarOpen(false)
  }, [location])

  // Allow deep-linking to tabs via URL hash (e.g. "/#email-accounts")
  useEffect(() => {
    const hashTab = (location.hash || '').replace('#', '')
    if (!hashTab) return

    const allNavItems = navigationGroups.flatMap((g) => g.items || [])
    const validTabIds = new Set(allNavItems.map((n) => n.id))
    if (validTabIds.has(hashTab)) {
      setActiveTab(hashTab)
    }
    // IMPORTANT: only react to hash changes.
    // If we also depend on `activeTab`, a stale hash (e.g. #email-accounts)
    // will force the UI back to that tab when the user clicks other tabs.
  }, [location.hash])

  useEffect(() => {
    const allNavItems = navigationGroups.flatMap((g) => g.items || [])
    const activeItem = allNavItems.find((x) => x.id === activeTab)
    const label = activeItem?.name || 'Inbox'
    document.title = `${label} | Bylix Email`
  }, [activeTab, navigationGroups])

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
                  <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">{renderContent()}</div>
                </div>
              </main>
            </div>
            <WorkspaceAssistant page={activeTab || 'default'} />
          </div>
        </EmailAccountsProvider>
      </PromptProvider>
    </EmailProvider>
  )
}

// Sidebar Component with Grouped Navigation
const LoadingScreen = () => (
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
)

function App() {
  const [isLoading, setIsLoading] = useState(true)

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 2000)
    return () => clearTimeout(timer)
  }, [])

  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <AuthProvider>
      <Router>
        <ApplicationRoutes
          AppContent={AppContent}
          AppContentWrapper={AppContentWrapper}
          ProtectedRoute={ProtectedRoute}
          PublicRoute={PublicRoute}
          SuperAdminRoute={SuperAdminRoute}
        />
      </Router>
    </AuthProvider>
  )
}

export default App
export { AppContent }
