import React from 'react'
import { Calendar, Clock } from 'lucide-react'
import { formatDate, isOverdue } from '../insightPresentation'

const DeadlinesTab = ({ deadlines }) => (
  <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
    <h2 className="text-lg font-semibold text-slate-900 mb-4">Upcoming Deadlines (Next 7 Days)</h2>
    {deadlines.length === 0 ? (
      <div className="text-center py-12">
        <Calendar className="h-12 w-12 text-slate-400 mx-auto mb-4" />
        <p className="text-slate-500">No upcoming deadlines</p>
      </div>
    ) : (
      <div className="space-y-4">
        {deadlines.map((commitment) => (
          <div
            key={commitment.id}
            className={`p-4 rounded-lg border ${
              isOverdue(commitment.deadline) ? 'border-red-200 bg-red-50' : 'border-slate-200 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold text-slate-900">{commitment.title}</h3>
                  {isOverdue(commitment.deadline) && (
                    <span className="px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">Overdue</span>
                  )}
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      commitment.priority === 'high'
                        ? 'bg-red-100 text-red-800'
                        : commitment.priority === 'medium'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    {commitment.priority}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mb-2">{commitment.description}</p>
                <div className="flex items-center gap-4 text-sm text-slate-500">
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    Due: {formatDate(commitment.deadline)}
                  </span>
                  <span>Type: {commitment.commitment_type}</span>
                  {commitment.committed_by && <span>By: {commitment.committed_by}</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
)

export default DeadlinesTab
