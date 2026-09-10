import { logger } from '../../utils/logger.js'
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, TrendingUp, Calendar, Users, BarChart3, RefreshCw } from 'lucide-react'
import { insightsApi } from '../../services/api'
import OverviewTab from './tabs/OverviewTab'
import RisksTab from './tabs/RisksTab'
import OpportunitiesTab from './tabs/OpportunitiesTab'
import DeadlinesTab from './tabs/DeadlinesTab'
import RelationshipsTab from './tabs/RelationshipsTab'

const InsightsDashboard = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [risks, setRisks] = useState([])
  const [opportunities, setOpportunities] = useState([])
  const [deadlines, setDeadlines] = useState([])
  const [relationships, setRelationships] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    loadAllData()
  }, [])

  const loadAllData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [analyticsRes, risksRes, opportunitiesRes, deadlinesRes, relationshipsRes] = await Promise.all([
        insightsApi.getAnalytics(30),
        insightsApi.getRisks(),
        insightsApi.getOpportunities(),
        insightsApi.getDeadlines(7),
        insightsApi.getRelationships(),
      ])

      setAnalytics(analyticsRes.data)
      setRisks(risksRes.data || [])
      setOpportunities(opportunitiesRes.data || [])
      setDeadlines(deadlinesRes.data || [])
      setRelationships(relationshipsRes.data)
    } catch (error) {
      logger.error('Failed to load insights:', error)
      setError('Unable to load insights. Please try refreshing.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div role="status" aria-label="Loading insights" className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Insights Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Intelligence from your email communications</p>
        </div>
        <button
          onClick={loadAllData}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 p-4 text-red-800">
          {error}
        </p>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', name: 'Overview', icon: BarChart3 },
            { id: 'risks', name: 'Risks', icon: AlertTriangle },
            { id: 'opportunities', name: 'Opportunities', icon: TrendingUp },
            { id: 'deadlines', name: 'Deadlines', icon: Calendar },
            { id: 'relationships', name: 'Relationships', icon: Users },
          ].map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.name}
              </button>
            )
          })}
        </nav>
      </div>

      {activeTab === 'overview' && (
        <OverviewTab
          analytics={analytics}
          risks={risks}
          opportunities={opportunities}
          deadlines={deadlines}
          relationships={relationships}
          navigate={navigate}
        />
      )}

      {activeTab === 'risks' && <RisksTab risks={risks} navigate={navigate} />}

      {activeTab === 'opportunities' && <OpportunitiesTab opportunities={opportunities} navigate={navigate} />}

      {activeTab === 'deadlines' && <DeadlinesTab deadlines={deadlines} />}

      {activeTab === 'relationships' && relationships && (
        <RelationshipsTab relationships={relationships} navigate={navigate} />
      )}
    </div>
  )
}

export default InsightsDashboard
