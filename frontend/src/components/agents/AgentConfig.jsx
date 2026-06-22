import React, { useState } from 'react';
import { X, Sparkles } from 'lucide-react';
import { agentsApi, aiApi } from '../../services/api';

const AGENT_TYPES = [
  { value: 'sales', label: 'Sales Agent', description: 'Handles sales inquiries and lead qualification' },
  { value: 'support', label: 'Support Agent', description: 'Manages customer support requests' },
  { value: 'recruitment', label: 'Recruitment Agent', description: 'Processes job applications and recruitment' },
  { value: 'executive_assistant', label: 'Executive Assistant', description: 'Manages executive communications' },
  { value: 'legal_filter', label: 'Legal Filter', description: 'Filters and categorizes legal communications' },
  { value: 'student', label: 'Student Assistant', description: 'Helps with academic communications' },
];

const DEFAULT_SYSTEM_PROMPTS = {
  sales: 'You are a sales agent. Your role is to respond to sales inquiries professionally, qualify leads, and schedule meetings. Be friendly, helpful, and goal-oriented.',
  support: 'You are a customer support agent. Your role is to help customers resolve their issues, answer questions, and provide excellent service. Be empathetic, patient, and solution-focused.',
  recruitment: 'You are a recruitment agent. Your role is to process job applications, screen candidates, and coordinate interviews. Be professional, clear, and organized.',
  executive_assistant: 'You are an executive assistant. Your role is to manage communications, schedule meetings, and prioritize important messages. Be efficient, organized, and proactive.',
  legal_filter: 'You are a legal filter agent. Your role is to identify legal communications, flag important documents, and categorize by urgency. Be precise, careful, and thorough.',
  student: 'You are a student assistant. Your role is to help manage academic communications, deadlines, and course-related emails. Be organized, helpful, and timely.',
};

const AgentConfig = ({ agent, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: agent?.name || '',
    agent_type: agent?.agent_type || 'sales',
    description: agent?.description || '',
    system_prompt: agent?.system_prompt || DEFAULT_SYSTEM_PROMPTS[agent?.agent_type || 'sales'],
    instructions: agent?.instructions || '',
    capabilities: agent?.capabilities || [],
    subscribe_to_categories: agent?.subscribe_to_categories || [],
    subscribe_to_senders: agent?.subscribe_to_senders || [],
    subscribe_to_keywords: agent?.subscribe_to_keywords || [],
    auto_draft_replies: agent?.auto_draft_replies ?? false,
    require_approval: agent?.require_approval ?? true,
    memory_enabled: agent?.memory_enabled ?? true,
    context_window: agent?.context_window || 10,
    tags: agent?.tags || []
  });

  const [saving, setSaving] = useState(false);
  const [newCategory, setNewCategory] = useState('');
  const [newSender, setNewSender] = useState('');
  const [newKeyword, setNewKeyword] = useState('');
  const [aiGoal, setAiGoal] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiMeta, setAiMeta] = useState({ provider: null, model: null });

  const aiQuickPrompts = [
    'Create a billing support agent with strict approval rules',
    'Create a sales agent focused on demo follow-ups and warm leads'
  ];

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (field === 'agent_type' && !agent) {
      setFormData(prev => ({ ...prev, system_prompt: DEFAULT_SYSTEM_PROMPTS[value] || '' }));
    }
  };

  const addCategory = () => {
    if (newCategory && !formData.subscribe_to_categories.includes(newCategory)) {
      setFormData(prev => ({
        ...prev,
        subscribe_to_categories: [...prev.subscribe_to_categories, newCategory]
      }));
      setNewCategory('');
    }
  };

  const removeCategory = (category) => {
    setFormData(prev => ({
      ...prev,
      subscribe_to_categories: prev.subscribe_to_categories.filter(c => c !== category)
    }));
  };

  const addSender = () => {
    if (newSender && !formData.subscribe_to_senders.includes(newSender)) {
      setFormData(prev => ({
        ...prev,
        subscribe_to_senders: [...prev.subscribe_to_senders, newSender]
      }));
      setNewSender('');
    }
  };

  const removeSender = (sender) => {
    setFormData(prev => ({
      ...prev,
      subscribe_to_senders: prev.subscribe_to_senders.filter(s => s !== sender)
    }));
  };

  const addKeyword = () => {
    if (newKeyword && !formData.subscribe_to_keywords.includes(newKeyword)) {
      setFormData(prev => ({
        ...prev,
        subscribe_to_keywords: [...prev.subscribe_to_keywords, newKeyword]
      }));
      setNewKeyword('');
    }
  };

  const removeKeyword = (keyword) => {
    setFormData(prev => ({
      ...prev,
      subscribe_to_keywords: prev.subscribe_to_keywords.filter(k => k !== keyword)
    }));
  };

  const handleSave = async () => {
    if (!formData.name || !formData.system_prompt) {
      alert('Please fill in required fields (Name and System Prompt)');
      return;
    }

    setSaving(true);
    try {
      if (agent?.id) {
        await agentsApi.updateAgent(agent.id, formData);
      } else {
        await agentsApi.createAgent(formData);
      }
      onSave();
      onClose();
    } catch (error) {
      console.error('Failed to save agent:', error);
      alert('Failed to save agent');
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
        page: 'agents',
        objective: goal.trim(),
        mode: 'draft',
        context: { current_form: formData }
      });
      const draft = res.data?.draft?.agent || {};
      setAiMeta({ provider: res.data?.provider, model: res.data?.model });
      if (Object.keys(draft).length > 0) {
        setFormData((prev) => ({ ...prev, ...draft }));
      }
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.response?.data?.error || error?.message || 'Failed to generate agent draft';
      setAiError(detail);
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-slate-200 p-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-900">
            {agent?.id ? 'Edit Agent' : 'Create New Agent'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <p className="text-sm font-semibold text-indigo-900">AI Agent Builder</p>
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
                placeholder="Describe the agent you want..."
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

          {/* Basic Info */}
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-900">Basic Information</h3>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Agent Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g., Sales Assistant"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Agent Type *</label>
              <select
                value={formData.agent_type}
                onChange={(e) => handleInputChange('agent_type', e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                {AGENT_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-slate-500">
                {AGENT_TYPES.find(t => t.value === formData.agent_type)?.description}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                rows="2"
                placeholder="Describe what this agent does"
              />
            </div>
          </div>

          {/* System Prompt */}
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-900">System Prompt *</h3>
            <textarea
              value={formData.system_prompt}
              onChange={(e) => handleInputChange('system_prompt', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
              rows="6"
              placeholder="Define the agent's role and behavior..."
            />
            <p className="text-xs text-slate-500">
              This prompt defines how the agent behaves. Be specific about the agent's role, tone, and responsibilities.
            </p>
          </div>

          {/* Additional Instructions */}
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-900">Additional Instructions</h3>
            <textarea
              value={formData.instructions}
              onChange={(e) => handleInputChange('instructions', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              rows="3"
              placeholder="Any additional instructions or guidelines..."
            />
          </div>

          {/* Subscription Settings */}
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-900">Email Subscription</h3>
            <p className="text-sm text-slate-600">Configure which emails this agent should process</p>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Categories</label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addCategory()}
                  className="flex-1 px-3 py-2 border border-slate-300 rounded-lg"
                  placeholder="e.g., Important, Finance"
                />
                <button
                  onClick={addCategory}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.subscribe_to_categories.map(cat => (
                  <span key={cat} className="px-2 py-1 bg-indigo-100 text-indigo-800 rounded text-sm flex items-center gap-1">
                    {cat}
                    <button onClick={() => removeCategory(cat)} className="text-indigo-600 hover:text-indigo-800">×</button>
                  </span>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Senders</label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={newSender}
                  onChange={(e) => setNewSender(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addSender()}
                  className="flex-1 px-3 py-2 border border-slate-300 rounded-lg"
                  placeholder="e.g., @company.com, john@example.com"
                />
                <button
                  onClick={addSender}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.subscribe_to_senders.map(sender => (
                  <span key={sender} className="px-2 py-1 bg-indigo-100 text-indigo-800 rounded text-sm flex items-center gap-1">
                    {sender}
                    <button onClick={() => removeSender(sender)} className="text-indigo-600 hover:text-indigo-800">×</button>
                  </span>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Keywords</label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
                  className="flex-1 px-3 py-2 border border-slate-300 rounded-lg"
                  placeholder="e.g., invoice, urgent, meeting"
                />
                <button
                  onClick={addKeyword}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.subscribe_to_keywords.map(keyword => (
                  <span key={keyword} className="px-2 py-1 bg-indigo-100 text-indigo-800 rounded text-sm flex items-center gap-1">
                    {keyword}
                    <button onClick={() => removeKeyword(keyword)} className="text-indigo-600 hover:text-indigo-800">×</button>
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Behavior Settings */}
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-900">Behavior Settings</h3>
            <div className="space-y-3">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.auto_draft_replies}
                  onChange={(e) => handleInputChange('auto_draft_replies', e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm text-slate-700">Automatically draft replies</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.require_approval}
                  onChange={(e) => handleInputChange('require_approval', e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm text-slate-700">Require human approval before sending</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.memory_enabled}
                  onChange={(e) => handleInputChange('memory_enabled', e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm text-slate-700">Enable memory (remember past interactions)</span>
              </label>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Context Window</label>
                <input
                  type="number"
                  value={formData.context_window}
                  onChange={(e) => handleInputChange('context_window', parseInt(e.target.value) || 10)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  min="1"
                  max="50"
                />
                <p className="mt-1 text-xs text-slate-500">Number of previous emails to consider (1-50)</p>
              </div>
            </div>
          </div>
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
            {saving ? 'Saving...' : agent?.id ? 'Update Agent' : 'Create Agent'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AgentConfig;
