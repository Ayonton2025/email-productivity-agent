import React from 'react'
import { AlertTriangle, TrendingUp, Calendar, Users, DollarSign, Target } from 'lucide-react'
import { getSeverityColor, getStatusColor, formatDate } from '../insightPresentation'

const OverviewTab = ({ analytics, risks, opportunities, deadlines, relationships, navigate }) => (
  <div className="space-y-6">
    {/* Stats Cards */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Active Risks</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{risks.length}</p>
          </div>
          <div className="p-3 bg-red-100 rounded-lg">
            <AlertTriangle className="h-6 w-6 text-red-600" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Opportunities</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{opportunities.length}</p>
          </div>
          <div className="p-3 bg-green-100 rounded-lg">
            <TrendingUp className="h-6 w-6 text-green-600" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Upcoming Deadlines</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{deadlines.length}</p>
          </div>
          <div className="p-3 bg-blue-100 rounded-lg">
            <Calendar className="h-6 w-6 text-blue-600" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Total Contacts</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{relationships?.total_contacts || 0}</p>
          </div>
          <div className="p-3 bg-purple-100 rounded-lg">
            <Users className="h-6 w-6 text-purple-600" />
          </div>
        </div>
      </div>
    </div>

    {/* Email Statistics */}
    {analytics && (
      <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Email Statistics (Last 30 Days)</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-slate-500">Total Emails</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{analytics.email_statistics?.total_emails || 0}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">By Category</p>
            <div className="mt-2 space-y-1">
              {Object.entries(analytics.email_statistics?.by_category || {})
                .slice(0, 3)
                .map(([cat, count]) => (
                  <div key={cat} className="flex justify-between text-sm">
                    <span className="text-slate-600">{cat}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
            </div>
          </div>
          <div>
            <p className="text-sm text-slate-500">By Sentiment</p>
            <div className="mt-2 space-y-1">
              {Object.entries(analytics.email_statistics?.by_sentiment || {}).map(([sent, count]) => (
                <div key={sent} className="flex justify-between text-sm">
                  <span className="text-slate-600 capitalize">{sent}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )}

    {/* Recent Risks */}
    {risks.length > 0 && (
      <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Recent Risks</h2>
        <div className="space-y-3">
          {risks.slice(0, 5).map((risk) => (
            <div
              key={risk.id}
              onClick={() => navigate(`/risks/${risk.id}`)}
              className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
            >
              <AlertTriangle
                className={`h-5 w-5 mt-0.5 ${risk.severity === 'critical' ? 'text-red-600' : 'text-orange-600'}`}
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-slate-900">{risk.title}</h3>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(risk.severity)}`}>
                    {risk.severity}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{risk.description}</p>
                <p className="mt-1 text-xs text-slate-500">{formatDate(risk.created_at)}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}

    {/* Recent Opportunities */}
    {opportunities.length > 0 && (
      <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Recent Opportunities</h2>
        <div className="space-y-3">
          {opportunities.slice(0, 5).map((opp) => (
            <div
              key={opp.id}
              onClick={() => navigate(`/opportunities/${opp.id}`)}
              className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
            >
              <TrendingUp className="h-5 w-5 mt-0.5 text-green-600" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-slate-900">{opp.title}</h3>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(opp.status)}`}>
                    {opp.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{opp.description}</p>
                <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
                  {opp.estimated_value && (
                    <span className="flex items-center gap-1">
                      <DollarSign className="h-3 w-3" />${opp.estimated_value.toLocaleString()}
                    </span>
                  )}
                  {opp.probability && (
                    <span className="flex items-center gap-1">
                      <Target className="h-3 w-3" />
                      {opp.probability}% probability
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
)

export default OverviewTab
