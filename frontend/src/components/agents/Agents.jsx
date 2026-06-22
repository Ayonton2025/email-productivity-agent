import React, { useState, useEffect } from 'react';
import { Bot, Plus, Play, Pause, Trash2, Edit, Settings, Activity, RefreshCw } from 'lucide-react';
import { agentsApi } from '../../services/api';
import AgentConfig from './AgentConfig';

const Agents = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState(null);

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    setLoading(true);
    try {
      const res = await agentsApi.getAgents();
      setAgents(res.data || []);
    } catch (error) {
      console.error('Failed to load agents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (agentId) => {
    if (!window.confirm('Are you sure you want to delete this agent?')) return;
    try {
      await agentsApi.deleteAgent(agentId);
      await loadAgents();
    } catch (error) {
      console.error('Failed to delete agent:', error);
      alert('Failed to delete agent');
    }
  };

  const handleToggleActive = async (agent) => {
    try {
      await agentsApi.updateAgent(agent.id, { is_active: !agent.is_active });
      await loadAgents();
    } catch (error) {
      console.error('Failed to update agent:', error);
    }
  };

  const agentTypes = {
    sales: { label: 'Sales Agent', color: 'bg-blue-100 text-blue-800' },
    support: { label: 'Support Agent', color: 'bg-green-100 text-green-800' },
    recruitment: { label: 'Recruitment Agent', color: 'bg-purple-100 text-purple-800' },
    executive_assistant: { label: 'Executive Assistant', color: 'bg-indigo-100 text-indigo-800' },
    legal_filter: { label: 'Legal Filter', color: 'bg-red-100 text-red-800' },
    student: { label: 'Student Assistant', color: 'bg-yellow-100 text-yellow-800' },
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Autonomous Agents</h1>
          <p className="mt-1 text-sm text-slate-500">Long-lived AI agents that work for you</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadAgents}
            className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Agent
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : agents.length === 0 ? (
        <div className="bg-white rounded-lg shadow border border-slate-200 p-12 text-center">
          <Bot className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No agents yet</h3>
          <p className="text-slate-500 mb-6">Create your first autonomous agent to handle emails automatically</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Create Agent
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div key={agent.id} className="bg-white rounded-lg shadow border border-slate-200 p-6 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-indigo-100 rounded-lg">
                    <Bot className="h-5 w-5 text-indigo-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900">{agent.name}</h3>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${agentTypes[agent.agent_type]?.color || 'bg-gray-100 text-gray-800'}`}>
                      {agentTypes[agent.agent_type]?.label || agent.agent_type}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {agent.is_running && (
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  )}
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    agent.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {agent.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
              {agent.description && (
                <p className="text-sm text-slate-600 mb-4">{agent.description}</p>
              )}
              <div className="flex items-center justify-between text-sm text-slate-500 mb-4">
                <span className="flex items-center gap-1">
                  <Activity className="h-4 w-4" />
                  Processed: {agent.emails_processed || 0}
                </span>
                <span>Drafted: {agent.replies_drafted || 0}</span>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setEditingAgent(agent)}
                  className="flex-1 px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  <Edit className="h-4 w-4 inline mr-1" />
                  Edit
                </button>
                <button 
                  onClick={() => handleToggleActive(agent)}
                  className="px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  {agent.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </button>
                <button 
                  onClick={() => handleDelete(agent.id)}
                  className="px-3 py-2 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {(showCreateModal || editingAgent) && (
        <AgentConfig
          agent={editingAgent}
          onClose={() => {
            setShowCreateModal(false);
            setEditingAgent(null);
          }}
          onSave={loadAgents}
        />
      )}
    </div>
  );
};

export default Agents;
