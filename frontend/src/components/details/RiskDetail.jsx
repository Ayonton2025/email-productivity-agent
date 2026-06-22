import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, Calendar, TrendingDown, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { insightsApi } from '../../services/api';

const RiskDetail = () => {
  const { riskId } = useParams();
  const navigate = useNavigate();
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRisk();
  }, [riskId]);

  const loadRisk = async () => {
    setLoading(true);
    try {
      const res = await insightsApi.getRisks();
      const foundRisk = res.data.find(r => r.id === riskId);
      setRisk(foundRisk);
    } catch (error) {
      console.error('Failed to load risk:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!risk) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Risk not found</p>
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
          <h1 className="text-3xl font-bold text-slate-900">{risk.title}</h1>
          <div className="flex items-center gap-2 mt-2">
            <span className={`px-3 py-1 rounded text-sm font-medium border ${getSeverityColor(risk.severity)}`}>
              {risk.severity}
            </span>
            <span className="px-3 py-1 rounded text-sm bg-slate-100 text-slate-700">
              {risk.risk_type}
            </span>
            <span className={`px-3 py-1 rounded text-sm font-medium ${
              risk.status === 'resolved' ? 'bg-green-100 text-green-800' :
              risk.status === 'mitigated' ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-800'
            }`}>
              {risk.status}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Risk Details</h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-slate-500 mb-1">Description</p>
                <p className="text-slate-900">{risk.description || 'No description provided'}</p>
              </div>
              {risk.potential_impact && (
                <div>
                  <p className="text-sm text-slate-500 mb-1">Potential Impact</p>
                  <p className="text-slate-900">{risk.potential_impact}</p>
                </div>
              )}
              {risk.extracted_text && (
                <div>
                  <p className="text-sm text-slate-500 mb-1">Extracted Text</p>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="text-sm text-slate-700 italic">"{risk.extracted_text}"</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Risk Information</h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-slate-500">Urgency Score</p>
                <p className="text-2xl font-bold text-slate-900">{Math.round(risk.urgency_score || 0)}/100</p>
              </div>
              {risk.revenue_impact && (
                <div>
                  <p className="text-sm text-slate-500">Revenue Impact</p>
                  <p className="text-xl font-semibold text-red-600">-${risk.revenue_impact.toLocaleString()}</p>
                </div>
              )}
              <div>
                <p className="text-sm text-slate-500">Created</p>
                <p className="text-sm font-medium text-slate-900">{formatDate(risk.created_at)}</p>
              </div>
              {risk.resolved_at && (
                <div>
                  <p className="text-sm text-slate-500">Resolved</p>
                  <p className="text-sm font-medium text-slate-900">{formatDate(risk.resolved_at)}</p>
                </div>
              )}
              <div>
                <p className="text-sm text-slate-500">Confidence</p>
                <p className="text-sm font-medium text-slate-900">{(risk.confidence_score * 100).toFixed(0)}%</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskDetail;
