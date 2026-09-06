import React from 'react'
import { Upload } from 'lucide-react'

export default function CampaignLeadsPanel({
  activeTab,
  leads,
  setShowLeadsImport,
  showLeadsImport,
  handleBulkImport,
}) {
  return (
    activeTab === 'leads' && (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">Leads ({leads.length})</h3>
          <button
            onClick={() => setShowLeadsImport(!showLeadsImport)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <Upload className="h-4 w-4" />
            Import CSV
          </button>
        </div>

        {showLeadsImport && (
          <div className="p-4 border border-slate-200 rounded-lg bg-slate-50">
            <label className="block text-sm font-medium text-slate-700 mb-2">Paste CSV Data</label>
            <textarea
              className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm"
              rows="10"
              placeholder="email,first_name,last_name,company,job_title&#10;john@example.com,John,Doe,Acme Inc,CEO"
              onBlur={(e) => {
                if (e.target.value.trim()) {
                  handleBulkImport(e.target.value)
                }
              }}
            />
            <p className="text-xs text-slate-500 mt-2">
              Format: email,first_name,last_name,company,job_title (one per line)
            </p>
          </div>
        )}

        <div className="max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 sticky top-0">
              <tr>
                <th className="px-4 py-2 text-left">Email</th>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Company</th>
                <th className="px-4 py-2 text-left">Status</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead, index) => (
                <tr key={lead.id || index} className="border-b border-slate-200">
                  <td className="px-4 py-2">{lead.email}</td>
                  <td className="px-4 py-2">
                    {lead.first_name} {lead.last_name}
                  </td>
                  <td className="px-4 py-2">{lead.company}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        lead.status === 'sent'
                          ? 'bg-green-100 text-green-800'
                          : lead.status === 'replied'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {lead.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {leads.length === 0 && (
            <p className="text-sm text-slate-500 text-center py-8">No leads added yet. Import CSV or add manually.</p>
          )}
        </div>
      </div>
    )
  )
}
