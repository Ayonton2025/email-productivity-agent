import CampaignDraftPanel from './CampaignDraftPanel'
import CampaignBasicForm from './CampaignBasicForm'
import CampaignSequencesPanel from './CampaignSequencesPanel'
import CampaignLeadsPanel from './CampaignLeadsPanel'

import React from 'react'
import { X } from 'lucide-react'

import { useCampaignBuilder } from './useCampaignBuilder'
const CampaignBuilder = ({ campaign, onClose, onSave }) => {
  const {
    formData,
    sequences,
    newSequence,
    setNewSequence,
    leads,
    showAddSequence,
    setShowAddSequence,
    showLeadsImport,
    setShowLeadsImport,
    saving,
    activeTab,
    setActiveTab,
    aiGoal,
    setAiGoal,
    aiLoading,
    aiError,
    aiMeta,
    recommendedSender,
    aiQuickPrompts,
    applyRecommendedSender,
    handleInputChange,
    addSequence,
    removeSequence,
    handleBulkImport,
    handleSave,
    handleGenerateAIDraft,
  } = useCampaignBuilder({ campaign, onClose, onSave })
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-slate-200 p-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-900">
            {campaign?.id ? 'Edit Campaign' : 'Create New Campaign'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-200 px-6">
          <nav className="-mb-px flex space-x-8">
            {['basic', 'sequences', 'leads'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6 space-y-6">
          <CampaignDraftPanel
            aiQuickPrompts={aiQuickPrompts}
            setAiGoal={setAiGoal}
            handleGenerateAIDraft={handleGenerateAIDraft}
            aiGoal={aiGoal}
            aiLoading={aiLoading}
            aiError={aiError}
            aiMeta={aiMeta}
          />

          {/* Basic Tab */}
          <CampaignBasicForm
            activeTab={activeTab}
            formData={formData}
            handleInputChange={handleInputChange}
            recommendedSender={recommendedSender}
            applyRecommendedSender={applyRecommendedSender}
          />

          {/* Sequences Tab */}
          <CampaignSequencesPanel
            activeTab={activeTab}
            setShowAddSequence={setShowAddSequence}
            showAddSequence={showAddSequence}
            newSequence={newSequence}
            setNewSequence={setNewSequence}
            addSequence={addSequence}
            sequences={sequences}
            removeSequence={removeSequence}
          />

          {/* Leads Tab */}
          <CampaignLeadsPanel
            activeTab={activeTab}
            leads={leads}
            setShowLeadsImport={setShowLeadsImport}
            showLeadsImport={showLeadsImport}
            handleBulkImport={handleBulkImport}
          />
        </div>

        <div className="sticky bottom-0 bg-white border-t border-slate-200 p-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : campaign?.id ? 'Update Campaign' : 'Create Campaign'}
          </button>
        </div>
      </div>
    </div>
  )
}
export default CampaignBuilder
