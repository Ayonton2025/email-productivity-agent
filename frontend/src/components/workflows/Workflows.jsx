import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Workflow, Plus, Play, Pause, Trash2, Edit, ChevronRight, Zap, RefreshCw } from 'lucide-react';
import { workflowsApi } from '../../services/api';
import { FeatureLockBanner } from '../premium/PremiumPrompt';
import { useSubscription } from '../../hooks/useSubscription';
import { useAuth } from '../../context/AuthContext';
import WorkflowBuilder from './WorkflowBuilder';

const Workflows = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  const { hasFeatureAccess } = useSubscription();
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState(null);

  useEffect(() => {
    loadWorkflows();
  }, []);

  const loadWorkflows = async () => {
    setLoading(true);
    try {
      const res = await workflowsApi.getWorkflows();
      setWorkflows(res.data || []);
    } catch (error) {
      console.error('Failed to load workflows:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (workflowId) => {
    if (!window.confirm('Are you sure you want to delete this workflow?')) return;
    try {
      await workflowsApi.deleteWorkflow(workflowId);
      await loadWorkflows();
    } catch (error) {
      console.error('Failed to delete workflow:', error);
      alert('Failed to delete workflow');
    }
  };

  const handleToggleActive = async (workflow) => {
    try {
      await workflowsApi.updateWorkflow(workflow.id, { is_active: !workflow.is_active });
      await loadWorkflows();
    } catch (error) {
      console.error('Failed to update workflow:', error);
    }
  };

  return (
    <div className="space-y-6">
      {!hasFeatureAccess('advancedWorkflows') && (
        <FeatureLockBanner
          featureName="Advanced Workflows"
          requiredPlan="plus"
          onUpgradeClick={() => navigate('/billing/upgrade?plan=plus')}
        />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Workflows</h1>
          <p className="mt-1 text-sm text-slate-500">Automate your email tasks with no-code workflows</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadWorkflows}
            className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          {!isSuperAdmin && (
            <button
              onClick={() => navigate('/billing/upgrade')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg text-sm font-medium hover:from-indigo-700 hover:to-purple-700 transition-all transform hover:scale-105"
            >
              ⭐ Upgrade
            </button>
          )}
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Workflow
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : workflows.length === 0 ? (
        <div className="bg-white rounded-lg shadow border border-slate-200 p-12 text-center">
          <Workflow className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No workflows yet</h3>
          <p className="text-slate-500 mb-6">Create your first workflow to automate email tasks</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Create Workflow
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {workflows.map((workflow) => (
            <div key={workflow.id} className="bg-white rounded-lg shadow border border-slate-200 p-6 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-100 rounded-lg">
                    <Zap className="h-5 w-5 text-indigo-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900">{workflow.name}</h3>
                    <p className="text-sm text-slate-500">{workflow.trigger_type}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  workflow.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {workflow.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              {workflow.description && (
                <p className="text-sm text-slate-600 mb-4">{workflow.description}</p>
              )}
              <div className="flex items-center justify-between text-sm text-slate-500 mb-4">
                <span>Runs: {workflow.total_runs || 0}</span>
                <span>Success: {workflow.successful_runs || 0}</span>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setEditingWorkflow(workflow)}
                  className="flex-1 px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  <Edit className="h-4 w-4 inline mr-1" />
                  Edit
                </button>
                <button 
                  onClick={() => handleToggleActive(workflow)}
                  className="px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  {workflow.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </button>
                <button 
                  onClick={() => handleDelete(workflow.id)}
                  className="px-3 py-2 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {(showCreateModal || editingWorkflow) && (
        <WorkflowBuilder
          workflow={editingWorkflow}
          onClose={() => {
            setShowCreateModal(false);
            setEditingWorkflow(null);
          }}
          onSave={loadWorkflows}
        />
      )}
    </div>
  );
};

export default Workflows;
