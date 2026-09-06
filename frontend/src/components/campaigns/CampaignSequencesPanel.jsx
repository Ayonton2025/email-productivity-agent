import React from 'react'
import { Plus, Trash2 } from 'lucide-react'

export default function CampaignSequencesPanel({
  activeTab,
  setShowAddSequence,
  showAddSequence,
  newSequence,
  setNewSequence,
  addSequence,
  sequences,
  removeSequence,
}) {
  return (
    activeTab === 'sequences' && (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">Email Sequences</h3>
          <button
            onClick={() => setShowAddSequence(!showAddSequence)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Add Sequence
          </button>
        </div>

        {showAddSequence && (
          <div className="p-4 border border-slate-200 rounded-lg bg-slate-50 space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Sequence Name *</label>
              <input
                type="text"
                value={newSequence.name}
                onChange={(e) => setNewSequence({ ...newSequence, name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                placeholder="e.g., Initial Outreach"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Subject Template *</label>
              <input
                type="text"
                value={newSequence.subject_template}
                onChange={(e) => setNewSequence({ ...newSequence, subject_template: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                placeholder="e.g., Quick question about {company}"
              />
              <p className="text-xs text-slate-500 mt-1">
                Use {'{name}'}, {'{company}'}, {'{job_title}'} for personalization
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Body Template *</label>
              <textarea
                value={newSequence.body_template}
                onChange={(e) => setNewSequence({ ...newSequence, body_template: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                rows="6"
                placeholder="Hi {name}, ..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Delay (days)</label>
                <input
                  type="number"
                  value={newSequence.delay_days}
                  onChange={(e) => setNewSequence({ ...newSequence, delay_days: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Delay (hours)</label>
                <input
                  type="number"
                  value={newSequence.delay_hours}
                  onChange={(e) => setNewSequence({ ...newSequence, delay_hours: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={addSequence}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Add Sequence
              </button>
              <button
                onClick={() => setShowAddSequence(false)}
                className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {sequences.map((seq, index) => (
            <div key={seq.id || index} className="p-4 border border-slate-200 rounded-lg">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-slate-500">Step {index + 1}</span>
                    <span className="font-semibold text-slate-900">{seq.name}</span>
                  </div>
                  <p className="text-sm text-slate-600 mb-1">
                    <strong>Subject:</strong> {seq.subject_template}
                  </p>
                  <p className="text-sm text-slate-500">
                    Delay: {seq.delay_days} days, {seq.delay_hours} hours
                  </p>
                </div>
                <button onClick={() => removeSequence(index, seq.id)} className="p-1 text-red-400 hover:text-red-600">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
          {sequences.length === 0 && (
            <p className="text-sm text-slate-500 text-center py-4">
              No sequences added yet. Click "Add Sequence" to get started.
            </p>
          )}
        </div>
      </div>
    )
  )
}
