import React, { useState } from 'react';
import { X, Plus, Trash2, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { workflowsApi, aiApi } from '../../services/api';

const WorkflowBuilder = ({ workflow, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: workflow?.name || '',
    description: workflow?.description || '',
    trigger_type: workflow?.trigger_type || 'email_received',
    trigger_conditions: workflow?.trigger_conditions || {
      category: '',
      sender: '',
      subject_contains: '',
      ai_condition: ''
    },
    run_on_match: workflow?.run_on_match ?? true,
    require_approval: workflow?.require_approval ?? false,
    tags: workflow?.tags || []
  });

  const [steps, setSteps] = useState(workflow?.steps || []);
  const [newStep, setNewStep] = useState({
    step_type: 'action',
    name: '',
    action_type: 'send_email',
    action_config: {},
    condition_type: 'field_match',
    condition_config: {},
    delay_seconds: 0
  });

  const [showAddStep, setShowAddStep] = useState(false);
  const [saving, setSaving] = useState(false);
  const [aiGoal, setAiGoal] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiMeta, setAiMeta] = useState({ provider: null, model: null });

  const aiQuickPrompts = [
    'Create a workflow to tag invoice emails and draft a reply',
    'Build an approval-required workflow for urgent VIP senders'
  ];

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleConditionChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      trigger_conditions: { ...prev.trigger_conditions, [field]: value }
    }));
  };

  const addStep = () => {
    if (!newStep.name) {
      alert('Please enter a step name');
      return;
    }

    const step = {
      ...newStep,
      step_order: steps.length + 1,
      id: `temp-${Date.now()}`
    };
    setSteps([...steps, step]);
    setNewStep({
      step_type: 'action',
      name: '',
      action_type: 'send_email',
      action_config: {},
      condition_type: 'field_match',
      condition_config: {},
      delay_seconds: 0
    });
    setShowAddStep(false);
  };

  const removeStep = (index) => {
    setSteps(steps.filter((_, i) => i !== index));
  };

  const moveStep = (index, direction) => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === steps.length - 1) return;

    const newSteps = [...steps];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    [newSteps[index], newSteps[targetIndex]] = [newSteps[targetIndex], newSteps[index]];
    newSteps[index].step_order = index + 1;
    newSteps[targetIndex].step_order = targetIndex + 1;
    setSteps(newSteps);
  };

  const handleSave = async () => {
    if (!formData.name) {
      alert('Please enter a workflow name');
      return;
    }

    setSaving(true);
    try {
      let savedWorkflow;
      if (workflow?.id) {
        // Update existing
        savedWorkflow = await workflowsApi.updateWorkflow(workflow.id, formData);
      } else {
        // Create new
        savedWorkflow = await workflowsApi.createWorkflow(formData);
      }

      // Save steps
      for (const step of steps) {
        if (step.id?.startsWith('temp-')) {
          // New step
          await workflowsApi.createStep(savedWorkflow.id, {
            ...step,
            workflow_id: savedWorkflow.id
          });
        } else {
          // Update existing step
          await workflowsApi.updateStep(step.id, step);
        }
      }

      onSave();
      onClose();
    } catch (error) {
      console.error('Failed to save workflow:', error);
      alert('Failed to save workflow');
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
        page: 'workflows',
        objective: goal.trim(),
        mode: 'draft',
        context: {
          current_form: formData,
          existing_steps: steps.length
        }
      });
      const draft = res.data?.draft || {};
      setAiMeta({ provider: res.data?.provider, model: res.data?.model });
      if (draft.workflow) {
        setFormData((prev) => ({ ...prev, ...draft.workflow }));
      }
      if (Array.isArray(draft.steps) && draft.steps.length > 0) {
        setSteps(draft.steps.map((step, idx) => ({ ...step, step_order: idx + 1, id: `temp-ai-${Date.now()}-${idx}` })));
      }
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.response?.data?.error || error?.message || 'Failed to generate workflow draft';
      setAiError(detail);
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-slate-200 p-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-900">
            {workflow?.id ? 'Edit Workflow' : 'Create New Workflow'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-600" />
              <p className="text-sm font-semibold text-indigo-900">AI Workflow Builder</p>
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
                placeholder="Describe the workflow you want..."
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
              <label className="block text-sm font-medium text-slate-700 mb-1">Workflow Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                placeholder="e.g., Auto-reply to invoices"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                rows="2"
                placeholder="Describe what this workflow does"
              />
            </div>
          </div>

          {/* Trigger Configuration */}
          <div className="space-y-4">
            <h3 className="font-semibold text-slate-900">Trigger Conditions</h3>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Trigger Type</label>
              <select
                value={formData.trigger_type}
                onChange={(e) => handleInputChange('trigger_type', e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="email_received">Email Received</option>
                <option value="email_sent">Email Sent</option>
                <option value="schedule">Schedule</option>
                <option value="manual">Manual</option>
              </select>
            </div>

            {formData.trigger_type === 'email_received' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                  <input
                    type="text"
                    value={formData.trigger_conditions.category || ''}
                    onChange={(e) => handleConditionChange('category', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                    placeholder="e.g., Finance, Important"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Sender Contains</label>
                  <input
                    type="text"
                    value={formData.trigger_conditions.sender || ''}
                    onChange={(e) => handleConditionChange('sender', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                    placeholder="e.g., @company.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Subject Contains</label>
                  <input
                    type="text"
                    value={formData.trigger_conditions.subject_contains || ''}
                    onChange={(e) => handleConditionChange('subject_contains', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                    placeholder="e.g., invoice, payment"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">AI Condition (Advanced)</label>
                  <textarea
                    value={formData.trigger_conditions.ai_condition || ''}
                    onChange={(e) => handleConditionChange('ai_condition', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                    rows="2"
                    placeholder="e.g., Email contains payment request"
                  />
                </div>
              </div>
            )}

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.run_on_match}
                  onChange={(e) => handleInputChange('run_on_match', e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm text-slate-700">Run automatically when conditions match</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.require_approval}
                  onChange={(e) => handleInputChange('require_approval', e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm text-slate-700">Require approval before execution</span>
              </label>
            </div>
          </div>

          {/* Workflow Steps */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-900">Workflow Steps</h3>
              <button
                onClick={() => setShowAddStep(!showAddStep)}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                <Plus className="h-4 w-4" />
                Add Step
              </button>
            </div>

            {showAddStep && (
              <div className="p-4 border border-slate-200 rounded-lg bg-slate-50">
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Step Name *</label>
                    <input
                      type="text"
                      value={newStep.name}
                      onChange={(e) => setNewStep({ ...newStep, name: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                      placeholder="e.g., Send Reply"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Step Type</label>
                    <select
                      value={newStep.step_type}
                      onChange={(e) => setNewStep({ ...newStep, step_type: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                    >
                      <option value="action">Action</option>
                      <option value="condition">Condition</option>
                      <option value="delay">Delay</option>
                      <option value="integration">Integration</option>
                    </select>
                  </div>
                  {newStep.step_type === 'action' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Action Type</label>
                      <select
                        value={newStep.action_type}
                        onChange={(e) => setNewStep({ ...newStep, action_type: e.target.value })}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                      >
                        <option value="send_email">Send Email</option>
                        <option value="create_draft">Create Draft</option>
                        <option value="tag">Tag Email</option>
                        <option value="archive">Archive Email</option>
                        <option value="notify">Send Notification</option>
                      </select>
                    </div>
                  )}
                  {newStep.step_type === 'delay' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Delay (seconds)</label>
                      <input
                        type="number"
                        value={newStep.delay_seconds}
                        onChange={(e) => setNewStep({ ...newStep, delay_seconds: parseInt(e.target.value) || 0 })}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                      />
                    </div>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={addStep}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                    >
                      Add Step
                    </button>
                    <button
                      onClick={() => setShowAddStep(false)}
                      className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-2">
              {steps.map((step, index) => (
                <div key={step.id || index} className="p-4 border border-slate-200 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-500">{index + 1}.</span>
                    <div>
                      <p className="font-medium text-slate-900">{step.name}</p>
                      <p className="text-sm text-slate-500">{step.step_type} - {step.action_type || step.condition_type || 'delay'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => moveStep(index, 'up')}
                      disabled={index === 0}
                      className="p-1 text-slate-400 hover:text-slate-600 disabled:opacity-30"
                    >
                      <ChevronUp className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => moveStep(index, 'down')}
                      disabled={index === steps.length - 1}
                      className="p-1 text-slate-400 hover:text-slate-600 disabled:opacity-30"
                    >
                      <ChevronDown className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => removeStep(index)}
                      className="p-1 text-red-400 hover:text-red-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
              {steps.length === 0 && (
                <p className="text-sm text-slate-500 text-center py-4">No steps added yet. Click "Add Step" to get started.</p>
              )}
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
            {saving ? 'Saving...' : workflow?.id ? 'Update Workflow' : 'Create Workflow'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default WorkflowBuilder;
