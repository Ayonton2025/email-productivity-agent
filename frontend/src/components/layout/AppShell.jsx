import React, { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'

import { useAuth } from '../../context/AuthContext'
import { EmailProvider } from '../../context/EmailContext'
import { PromptProvider } from '../../context/PromptContext'
import { EmailAccountsProvider } from '../../context/EmailAccountsContext'
import EmailAgent from '../agent/EmailAgent'
import Agents from '../agents/Agents'
import SuperAdminDashboard from '../admin/SuperAdminDashboard'
import SuperAdminFeatureRules from '../admin/SuperAdminFeatureRules'
import SuperAdminUserAccess from '../admin/SuperAdminUserAccess'
import AutoReplyRules from '../auto-reply/AutoReplyRules'
import WorkspaceAssistant from '../assistant/WorkspaceAssistant'
import DailyBriefing from '../briefings/DailyBriefing'
import Campaigns from '../campaigns/Campaigns'
import DeliverabilityCenter from '../deliverability/DeliverabilityCenter'
import DraftManager from '../drafts/DraftManager'
import EmailAccounts from '../email-accounts/EmailAccounts'
import ExecutiveCenter from '../executive/ExecutiveCenter'
import FollowUpCenter from '../followups/FollowUpCenter'
import HostedEmailCenter from '../hosted-email/HostedEmailCenter'
import Inbox from '../inbox/Inbox'
import InsightsDashboard from '../insights/InsightsDashboard'
import PromptManager from '../prompts/PromptManager'
import Relationships from '../relationships/Relationships'
import SharedInboxCenter from '../shared-inbox/SharedInboxCenter'
import Workflows from '../workflows/Workflows'
import { getNavigationGroups, isSuperAdminUser } from '../../routes/navigation'
import SidebarContent from './SidebarContent'

const AppContentWrapper = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState({})
  const { user, logout } = useAuth()
  const location = useLocation()

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

export { AppContent, AppContentWrapper }
