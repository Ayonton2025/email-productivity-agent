import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Plus, Play, Pause, Trash2, Edit, BarChart3, Users, RefreshCw } from 'lucide-react';
import { campaignsApi } from '../../services/api';
import { FeatureLockBanner } from '../premium/PremiumPrompt';
import { useSubscription } from '../../hooks/useSubscription';
import { useAuth } from '../../context/AuthContext';
import CampaignBuilder from './CampaignBuilder';

const Campaigns = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  const { hasFeatureAccess } = useSubscription();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState(null);

  useEffect(() => {
    loadCampaigns();
  }, []);

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const res = await campaignsApi.getCampaigns();
      setCampaigns(res.data || []);
    } catch (error) {
      console.error('Failed to load campaigns:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (campaignId) => {
    if (!window.confirm('Are you sure you want to delete this campaign?')) return;
    try {
      await campaignsApi.deleteCampaign(campaignId);
      await loadCampaigns();
    } catch (error) {
      console.error('Failed to delete campaign:', error);
      alert('Failed to delete campaign');
    }
  };

  const handleStart = async (campaignId) => {
    try {
      await campaignsApi.startCampaign(campaignId);
      await loadCampaigns();
    } catch (error) {
      console.error('Failed to start campaign:', error);
    }
  };

  const handlePause = async (campaignId) => {
    try {
      await campaignsApi.pauseCampaign(campaignId);
      await loadCampaigns();
    } catch (error) {
      console.error('Failed to pause campaign:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'bg-green-100 text-green-800';
      case 'paused': return 'bg-yellow-100 text-yellow-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'draft': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const calculateOpenRate = (campaign) => {
    if (!campaign.emails_sent || campaign.emails_sent === 0) return 0;
    return ((campaign.emails_opened / campaign.emails_sent) * 100).toFixed(1);
  };

  const calculateReplyRate = (campaign) => {
    if (!campaign.emails_sent || campaign.emails_sent === 0) return 0;
    return ((campaign.replies_received / campaign.emails_sent) * 100).toFixed(1);
  };

  return (
    <div className="space-y-6">
      {!hasFeatureAccess('campaigns') && (
        <FeatureLockBanner
          featureName="Email Campaigns"
          requiredPlan="plus"
          onUpgradeClick={() => navigate('/billing/upgrade?plan=plus')}
        />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Email Campaigns</h1>
          <p className="mt-1 text-sm text-slate-500">Manage your cold email and outreach campaigns</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadCampaigns}
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
            Create Campaign
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : campaigns.length === 0 ? (
        <div className="bg-white rounded-lg shadow border border-slate-200 p-12 text-center">
          <Mail className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No campaigns yet</h3>
          <p className="text-slate-500 mb-6">Create your first email campaign to start reaching out</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Create Campaign
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns.map((campaign) => (
            <div key={campaign.id} className="bg-white rounded-lg shadow border border-slate-200 p-6 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-indigo-100 rounded-lg">
                      <Mail className="h-5 w-5 text-indigo-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-slate-900">{campaign.name}</h3>
                      <p className="text-sm text-slate-500">{campaign.campaign_type}</p>
                    </div>
                    <span className={`px-3 py-1 rounded text-sm font-medium ${getStatusColor(campaign.status)}`}>
                      {campaign.status}
                    </span>
                  </div>
                  {campaign.description && (
                    <p className="text-sm text-slate-600 mb-4">{campaign.description}</p>
                  )}
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="h-4 w-4 text-slate-500" />
                    <span className="text-xs text-slate-500">Leads</span>
                  </div>
                  <p className="text-lg font-semibold text-slate-900">{campaign.total_leads || 0}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Mail className="h-4 w-4 text-slate-500" />
                    <span className="text-xs text-slate-500">Sent</span>
                  </div>
                  <p className="text-lg font-semibold text-slate-900">{campaign.emails_sent || 0}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <BarChart3 className="h-4 w-4 text-slate-500" />
                    <span className="text-xs text-slate-500">Open Rate</span>
                  </div>
                  <p className="text-lg font-semibold text-slate-900">{calculateOpenRate(campaign)}%</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <BarChart3 className="h-4 w-4 text-slate-500" />
                    <span className="text-xs text-slate-500">Reply Rate</span>
                  </div>
                  <p className="text-lg font-semibold text-slate-900">{calculateReplyRate(campaign)}%</p>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-4 border-t border-slate-200">
                <button 
                  onClick={() => setEditingCampaign(campaign)}
                  className="flex-1 px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  <Edit className="h-4 w-4 inline mr-1" />
                  Edit
                </button>
                <button className="px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50">
                  <BarChart3 className="h-4 w-4" />
                </button>
                <button 
                  onClick={() => campaign.status === 'running' ? handlePause(campaign.id) : handleStart(campaign.id)}
                  className="px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  {campaign.status === 'running' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </button>
                <button 
                  onClick={() => handleDelete(campaign.id)}
                  className="px-3 py-2 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {(showCreateModal || editingCampaign) && (
        <CampaignBuilder
          campaign={editingCampaign}
          onClose={() => {
            setShowCreateModal(false);
            setEditingCampaign(null);
          }}
          onSave={loadCampaigns}
        />
      )}
    </div>
  );
};

export default Campaigns;
