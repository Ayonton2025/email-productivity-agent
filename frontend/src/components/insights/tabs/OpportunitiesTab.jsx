import React from 'react'
import { TrendingUp, DollarSign, Target, Calendar } from 'lucide-react'
import { getStatusColor, formatDate } from '../insightPresentation'

const OpportunitiesTab = ({ opportunities, navigate }) => (
  <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
    <h2 className="text-lg font-semibold text-slate-900 mb-4">All Opportunities</h2>
    {opportunities.length === 0 ? (
      <div className="text-center py-12">
        <TrendingUp className="h-12 w-12 text-slate-400 mx-auto mb-4" />
        <p className="text-slate-500">No opportunities identified</p>
      </div>
    ) : (
      <div className="space-y-4">
        {opportunities.map((opp) => (
          <div
            key={opp.id}
            onClick={() => navigate(`/opportunities/${opp.id}`)}
            className="p-4 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold text-slate-900">{opp.title}</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(opp.status)}`}>
                    {opp.status}
                  </span>
                  <span className="px-2 py-1 rounded text-xs bg-slate-100 text-slate-700">{opp.opportunity_type}</span>
                  {opp.lead_temperature && (
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        opp.lead_temperature === 'hot'
                          ? 'bg-red-100 text-red-800'
                          : opp.lead_temperature === 'warm'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {opp.lead_temperature}
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-600 mb-2">{opp.description}</p>
                <div className="flex items-center gap-4 text-sm">
                  {opp.estimated_value && (
                    <span className="flex items-center gap-1 text-slate-700">
                      <DollarSign className="h-4 w-4" />
                      <strong>${opp.estimated_value.toLocaleString()}</strong>
                    </span>
                  )}
                  {opp.probability && (
                    <span className="flex items-center gap-1 text-slate-700">
                      <Target className="h-4 w-4" />
                      <strong>{opp.probability}%</strong> probability
                    </span>
                  )}
                  {opp.expected_close_date && (
                    <span className="flex items-center gap-1 text-slate-700">
                      <Calendar className="h-4 w-4" />
                      Close: {formatDate(opp.expected_close_date)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
)

export default OpportunitiesTab
