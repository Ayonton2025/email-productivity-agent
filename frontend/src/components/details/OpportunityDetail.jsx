import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, TrendingUp, Calendar, DollarSign, Target, RefreshCw } from 'lucide-react';
import { insightsApi } from '../../services/api';

const OpportunityDetail = () => {
  const { opportunityId } = useParams();
  const navigate = useNavigate();
  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOpportunity();
  }, [opportunityId]);

  const loadOpportunity = async () => {
    setLoading(true);
    try {
      const res = await insightsApi.getOpportunities();
      const foundOpp = res.data.find(o => o.id === opportunityId);
      setOpportunity(foundOpp);
    } catch (error) {
      console.error('Failed to load opportunity:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Not set';
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric'
    });
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'new': return 'bg-blue-100 text-blue-800';
      case 'qualified': return 'bg-purple-100 text-purple-800';
      case 'in_progress': return 'bg-yellow-100 text-yellow-800';
      case 'won': return 'bg-green-100 text-green-800';
      case 'lost': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!opportunity) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Opportunity not found</p>
        <button onClick={() => navigate('/insights')} className="mt-4 text-indigo-600 hover:text-indigo-700">
          Back to Insights
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/insights')}
          className="p-2 hover:bg-slate-100 rounded-lg"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-slate-900">{opportunity.title}</h1>
          <div className="flex items-center gap-2 mt-2">
            <span className={`px-3 py-1 rounded text-sm font-medium ${getStatusColor(opportunity.status)}`}>
              {opportunity.status}
            </span>
            <span className="px-3 py-1 rounded text-sm bg-slate-100 text-slate-700">
              {opportunity.opportunity_type}
            </span>
            {opportunity.lead_temperature && (
              <span className={`px-3 py-1 rounded text-sm font-medium ${
                opportunity.lead_temperature === 'hot' ? 'bg-red-100 text-red-800' :
                opportunity.lead_temperature === 'warm' ? 'bg-orange-100 text-orange-800' :
                'bg-blue-100 text-blue-800'
              }`}>
                {opportunity.lead_temperature}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Opportunity Details</h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-slate-500 mb-1">Description</p>
                <p className="text-slate-900">{opportunity.description || 'No description provided'}</p>
              </div>
              {opportunity.extracted_text && (
                <div>
                  <p className="text-sm text-slate-500 mb-1">Extracted Text</p>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="text-sm text-slate-700 italic">"{opportunity.extracted_text}"</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Value & Probability</h2>
            <div className="space-y-4">
              {opportunity.estimated_value && (
                <div>
                  <p className="text-sm text-slate-500">Estimated Value</p>
                  <p className="text-2xl font-bold text-green-600">${opportunity.estimated_value.toLocaleString()}</p>
                </div>
              )}
              {opportunity.probability && (
                <div>
                  <p className="text-sm text-slate-500">Probability</p>
                  <div className="flex items-center gap-2">
                    <p className="text-2xl font-bold text-slate-900">{opportunity.probability}%</p>
                    <Target className="h-5 w-5 text-indigo-600" />
                  </div>
                  <div className="mt-2 w-full bg-slate-200 rounded-full h-2">
                    <div 
                      className="bg-indigo-600 h-2 rounded-full" 
                      style={{ width: `${opportunity.probability}%` }}
                    ></div>
                  </div>
                </div>
              )}
              {opportunity.expected_close_date && (
                <div>
                  <p className="text-sm text-slate-500">Expected Close Date</p>
                  <p className="text-sm font-medium text-slate-900">{formatDate(opportunity.expected_close_date)}</p>
                </div>
              )}
              <div>
                <p className="text-sm text-slate-500">Interest Level</p>
                <p className="text-sm font-medium text-slate-900 capitalize">{opportunity.interest_level || 'Unknown'}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Created</p>
                <p className="text-sm font-medium text-slate-900">{formatDate(opportunity.created_at)}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OpportunityDetail;
