import React from 'react'
import { Zap } from 'lucide-react'

export default function CampaignBasicForm({
  activeTab,
  formData,
  handleInputChange,
  recommendedSender,
  applyRecommendedSender,
}) {
  return (
    activeTab === 'basic' && (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Name *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            placeholder="e.g., Q1 Sales Outreach"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Type</label>
          <select
            value={formData.campaign_type}
            onChange={(e) => handleInputChange('campaign_type', e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg"
          >
            <option value="cold_outreach">Cold Outreach</option>
            <option value="follow_up">Follow-up</option>
            <option value="nurture">Nurture</option>
            <option value="announcement">Announcement</option>
          </select>
        </div>
        {recommendedSender && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-900">Recommended Sender Account</p>
                <p className="text-sm text-blue-700 mt-1">{recommendedSender.email}</p>
                {!recommendedSender.send_cap_ok && (
                  <p className="text-xs text-orange-600 mt-1">⚠️ Daily send limit reached</p>
                )}
              </div>
              <button
                type="button"
                onClick={applyRecommendedSender}
                className="ml-2 px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 flex items-center gap-2 whitespace-nowrap"
              >
                <Zap size={16} />
                Use This
              </button>
            </div>
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">From Email *</label>
          <input
            type="email"
            value={formData.from_email}
            onChange={(e) => handleInputChange('from_email', e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            placeholder="sender@company.com"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">From Name</label>
          <input
            type="text"
            value={formData.from_name}
            onChange={(e) => handleInputChange('from_name', e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            placeholder="John Doe"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Daily Send Limit</label>
            <input
              type="number"
              value={formData.daily_send_limit}
              onChange={(e) => handleInputChange('daily_send_limit', parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Send Delay (minutes)</label>
            <input
              type="number"
              value={formData.send_delay_minutes}
              onChange={(e) => handleInputChange('send_delay_minutes', parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
          </div>
        </div>
      </div>
    )
  )
}
