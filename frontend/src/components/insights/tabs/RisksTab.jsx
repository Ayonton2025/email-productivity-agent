import React from 'react'
import { AlertTriangle } from 'lucide-react'
import { getSeverityColor, formatDate } from '../insightPresentation'

const RisksTab = ({ risks, navigate }) => (
  <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
    <h2 className="text-lg font-semibold text-slate-900 mb-4">All Risks</h2>
    {risks.length === 0 ? (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
        <p className="text-slate-500">No risks identified</p>
      </div>
    ) : (
      <div className="space-y-4">
        {risks.map((risk) => (
          <div
            key={risk.id}
            onClick={() => navigate(`/risks/${risk.id}`)}
            className="p-4 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold text-slate-900">{risk.title}</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(risk.severity)}`}>
                    {risk.severity}
                  </span>
                  <span className="px-2 py-1 rounded text-xs bg-slate-100 text-slate-700">{risk.risk_type}</span>
                </div>
                <p className="text-sm text-slate-600 mb-2">{risk.description}</p>
                {risk.potential_impact && (
                  <p className="text-sm text-slate-500 mb-2">
                    <strong>Impact:</strong> {risk.potential_impact}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span>Created: {formatDate(risk.created_at)}</span>
                  {risk.urgency_score && <span>Urgency: {risk.urgency_score}/100</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
)

export default RisksTab
