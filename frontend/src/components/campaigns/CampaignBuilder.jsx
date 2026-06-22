import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, ChevronDown, ChevronUp, Upload, Sparkles, Zap } from 'lucide-react';
import { campaignsApi, aiApi } from '../../services/api';

const CampaignBuilder = ({ campaign, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: campaign?.name || '',
    description: campaign?.description || '',
    campaign_type: campaign?.campaign_type || 'cold_outreach',
    from_email: campaign?.from_email || '',
    from_name: campaign?.from_name || '',
    reply_to: campaign?.reply_to || '',
    daily_send_limit: campaign?.daily_send_limit || 50,
    send_delay_minutes: campaign?.send_delay_minutes || 5,
    timezone: campaign?.timezone || 'UTC',
    send_hours: campaign?.send_hours || [],
    warm_up_enabled: campaign?.warm_up_enabled ?? false,
    warm_up_emails_per_day: campaign?.warm_up_emails_per_day || 5,
    ab_test_enabled: campaign?.ab_test_enabled ?? false,
    ab_test_split: campaign?.ab_test_split || 0.5,
    tags: campaign?.tags || []
  });

  const [sequences, setSequences] = useState(campaign?.sequences || []);
  const [newSequence, setNewSequence] = useState({
    name: '',
    subject_template: '',
    body_template: '',
    delay_days: 0,
    delay_hours: 0,
    send_if_opened: false,
    send_if_clicked: false,
    send_if_replied: false,
    stop_if_replied: true
  });

  const [leads, setLeads] = useState([]);
  const [showAddSequence, setShowAddSequence] = useState(false);
  const [showLeadsImport, setShowLeadsImport] = useState(false);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('basic'); // basic, sequences, leads
  const [aiGoal, setAiGoal] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiMeta, setAiMeta] = useState({ provider: null, model: null });
  const [loadingRecommended, setLoadingRecommended] = useState(false);
  const [recommendedSender, setRecommendedSender] = useState(null);

  const aiQuickPrompts = [
    'Create a 3-step cold outreach campaign for SaaS founders',
    'Build a follow-up campaign for warm leads with 2 sequences'
  ];

  useEffect(() => {
    if (campaign?.id) {
      loadLeads();
    }
    // Load recommended sender on mount
    loadRecommendedSender();
  }, [campaign?.id]);

  const loadRecommendedSender = async () => {
    try {
      const res = await campaignsApi.getRecommendedSender();
      if (res.data?.success && res.data?.recommended) {
        setRecommendedSender(res.data.recommended);
      }
    } catch (error) {
      console.error('Failed to load recommended sender:', error);
    }
  };

  const applyRecommendedSender = () => {
    if (!recommendedSender) return;
    setFormData(prev => ({
      ...prev,
      from_email: recommendedSender.email,
      from_name: recommendedSender.from_name,
      reply_to: recommendedSender.reply_to
    }));
  };

  const loadLeads = async () => {
    try {
      const res = await campaignsApi.getLeads(campaign.id);
      setLeads(res.data || []);
    } catch (error) {
      console.error('Failed to load leads:', error);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const addSequence = async () => {
    if (!newSequence.name || !newSequence.subject_template || !newSequence.body_template) {
      alert('Please fill in all required sequence fields');
      return;
    }

    if (campaign?.id) {
      try {
        const sequence = await campaignsApi.createSequence(campaign.id, {
          ...newSequence,
          step_order: sequences.length + 1
        });
        setSequences([...sequences, sequence.data]);
      } catch (error) {
        console.error('Failed to create sequence:', error);
        alert('Failed to create sequence');
        return;
      }
    } else {
      const sequence = {
        ...newSequence,
        step_order: sequences.length + 1,
        id: `temp-${Date.now()}`
      };
      setSequences([...sequences, sequence]);
    }

    setNewSequence({
      name: '',
      subject_template: '',
      body_template: '',
      delay_days: 0,
      delay_hours: 0,
      send_if_opened: false,
      send_if_clicked: false,
      send_if_replied: false,
      stop_if_replied: true
    });
    setShowAddSequence(false);
  };

  const removeSequence = async (index, sequenceId) => {
    if (sequenceId && !sequenceId.toString().startsWith('temp-')) {
      // TODO: Delete from API if needed
    }
    setSequences(sequences.filter((_, i) => i !== index));
  };

  const handleBulkImport = async (csvText) => {
    // Parse CSV
    const lines = csvText.split('\n').filter(line => line.trim());
    const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
    const importedLeads = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',').map(v => v.trim());
      const lead = {
        email: values[headers.indexOf('email')] || '',
        first_name: values[headers.indexOf('first_name')] || values[headers.indexOf('firstname')] || '',
        last_name: values[headers.indexOf('last_name')] || values[headers.indexOf('lastname')] || '',
        company: values[headers.indexOf('company')] || '',
        job_title: values[headers.indexOf('job_title')] || values[headers.indexOf('jobtitle')] || '',
        custom_fields: {}
      };
      if (lead.email) importedLeads.push(lead);
    }

    if (campaign?.id && importedLeads.length > 0) {
      try {
        await campaignsApi.bulkCreateLeads(campaign.id, importedLeads);
        await loadLeads();
        setShowLeadsImport(false);
        alert(`Imported ${importedLeads.length} leads`);
      } catch (error) {
        console.error('Failed to import leads:', error);
        alert('Failed to import leads');
      }
    } else {
      setLeads([...leads, ...importedLeads]);
      setShowLeadsImport(false);
    }
  };

  const handleSave = async () => {
    if (!formData.name || !formData.from_email) {
      alert('Please fill in required fields (Name and From Email)');
      return;
    }

    setSaving(true);
    try {
      let savedCampaign;
      if (campaign?.id) {
        savedCampaign = await campaignsApi.updateCampaign(campaign.id, formData);
      } else {
        savedCampaign = await campaignsApi.createCampaign(formData);
        
        // Create sequences
        for (const seq of sequences) {
          await campaignsApi.createSequence(savedCampaign.id, {
            ...seq,
            campaign_id: savedCampaign.id
          });
        }

        // Import leads if any
        if (leads.length > 0) {
          await campaignsApi.bulkCreateLeads(savedCampaign.id, leads);
        }
      }

      onSave();
      onClose();
    } catch (error) {
      console.error('Failed to save campaign:', error);
      alert('Failed to save campaign');
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateAIDraft = async (goal) => {
    if (!goal?.trim()) return;
    setAiLoading(true);
    setAiError('');
    try {
      const res = await aiApi.assistWorkspace({
        page: 'campaigns',
        objective: goal.trim(),
        mode: 'draft',
        context: {
          existing_sequences: sequences.length,
          existing_leads: leads.length,
          current_form: formData
        }
      });
      const draft = res.data?.draft || {};
      setAiMeta({ provider: res.data?.provider, model: res.data?.model });
      if (draft.campaign) {
        setFormData((prev) => ({ ...prev, ...draft.campaign }));
      }
      if (Array.isArray(draft.sequences) && draft.sequences.length > 0) {
        setSequences(draft.sequences.map((seq, idx) => ({ ...seq, step_order: idx + 1, id: `temp-ai-${Date.now()}-${idx}` })));
      }
      if (Array.isArray(draft.leads) && draft.leads.length > 0) {
        setLeads(draft.leads);
      }
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.response?.data?.error || error?.message || 'Failed to generate campaign draft';
      setAiError(detail);
    } finally {
      setAiLoading(false);
    }
  };

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
            {['basic', 'sequences', 'leads'].map(tab => (
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
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <p className="text-sm font-semibold text-indigo-900">AI Campaign Builder</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {aiQuickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => {
                    setAiGoal(prompt);
                    handleGenerateAIDraft(prompt);
                  }}
                  className="rounded-full border border-indigo-200 bg-white px-3 py-1 text-xs text-indigo-700 hover:bg-indigo-100"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={aiGoal}
                onChange={(e) => setAiGoal(e.target.value)}
                placeholder="Describe the campaign you want..."
                className="flex-1 rounded-lg border border-indigo-200 px-3 py-2 text-sm"
              />
              <button
                onClick={() => handleGenerateAIDraft(aiGoal)}
                disabled={aiLoading || !aiGoal.trim()}
                className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {aiLoading ? 'Generating...' : 'Generate'}
              </button>
            </div>
            {aiError && (
              <div className="text-xs text-red-600 space-y-1">
                <p>{aiError}</p>
                {String(aiError).includes('No LLM providers configured') && <a href="/admin/super" className="underline">Configure LLM Providers</a>}
              </div>
            )}
            {(aiMeta.provider || aiMeta.model) && (
              <p className="text-[11px] text-slate-500">Provider: {aiMeta.provider || 'n/a'} | Model: {aiMeta.model || 'n/a'}</p>
            )}
          </div>

          {/* Basic Tab */}
          {activeTab === 'basic' && (
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
          )}

          {/* Sequences Tab */}
          {activeTab === 'sequences' && (
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
                    <p className="text-xs text-slate-500 mt-1">Use {'{name}'}, {'{company}'}, {'{job_title}'} for personalization</p>
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
                    <button onClick={addSequence} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
                      Add Sequence
                    </button>
                    <button onClick={() => setShowAddSequence(false)} className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50">
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
                        <p className="text-sm text-slate-600 mb-1"><strong>Subject:</strong> {seq.subject_template}</p>
                        <p className="text-sm text-slate-500">Delay: {seq.delay_days} days, {seq.delay_hours} hours</p>
                      </div>
                      <button
                        onClick={() => removeSequence(index, seq.id)}
                        className="p-1 text-red-400 hover:text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
                {sequences.length === 0 && (
                  <p className="text-sm text-slate-500 text-center py-4">No sequences added yet. Click "Add Sequence" to get started.</p>
                )}
              </div>
            </div>
          )}

          {/* Leads Tab */}
          {activeTab === 'leads' && (
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
                        handleBulkImport(e.target.value);
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
                        <td className="px-4 py-2">{lead.first_name} {lead.last_name}</td>
                        <td className="px-4 py-2">{lead.company}</td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            lead.status === 'sent' ? 'bg-green-100 text-green-800' :
                            lead.status === 'replied' ? 'bg-blue-100 text-blue-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
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
          )}
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
  );
};

export default CampaignBuilder;
