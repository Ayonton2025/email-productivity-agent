import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  TrendingUp,
  Calendar,
  Users,
  BarChart3,
  RefreshCw,
  ChevronRight,
  Clock,
  DollarSign,
  Target,
} from 'lucide-react';
import { insightsApi } from '../../services/api';

const InsightsDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [risks, setRisks] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [relationships, setRelationships] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [analyticsRes, risksRes, opportunitiesRes, deadlinesRes, relationshipsRes] = await Promise.all([
        insightsApi.getAnalytics(30),
        insightsApi.getRisks(),
        insightsApi.getOpportunities(),
        insightsApi.getDeadlines(7),
        insightsApi.getRelationships(),
      ]);

      setAnalytics(analyticsRes.data);
      setRisks(risksRes.data || []);
      setOpportunities(opportunitiesRes.data || []);
      setDeadlines(deadlinesRes.data || []);
      setRelationships(relationshipsRes.data);
    } catch (error) {
      console.error('Failed to load insights:', error);
    } finally {
      setLoading(false);
    }
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

  const formatDate = (dateString) => {
    if (!dateString) return 'No date';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const isOverdue = (deadline) => {
    if (!deadline) return false;
    return new Date(deadline) < new Date();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Insights Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Intelligence from your email communications</p>
        </div>
        <button
          onClick={loadAllData}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', name: 'Overview', icon: BarChart3 },
            { id: 'risks', name: 'Risks', icon: AlertTriangle },
            { id: 'opportunities', name: 'Opportunities', icon: TrendingUp },
            { id: 'deadlines', name: 'Deadlines', icon: Calendar },
            { id: 'relationships', name: 'Relationships', icon: Users },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">Active Risks</p>
                  <p className="mt-2 text-3xl font-bold text-slate-900">{risks.length}</p>
                </div>
                <div className="p-3 bg-red-100 rounded-lg">
                  <AlertTriangle className="h-6 w-6 text-red-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">Opportunities</p>
                  <p className="mt-2 text-3xl font-bold text-slate-900">{opportunities.length}</p>
                </div>
                <div className="p-3 bg-green-100 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">Upcoming Deadlines</p>
                  <p className="mt-2 text-3xl font-bold text-slate-900">{deadlines.length}</p>
                </div>
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Calendar className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">Total Contacts</p>
                  <p className="mt-2 text-3xl font-bold text-slate-900">
                    {relationships?.total_contacts || 0}
                  </p>
                </div>
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Users className="h-6 w-6 text-purple-600" />
                </div>
              </div>
            </div>
          </div>

          {/* Email Statistics */}
          {analytics && (
            <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Email Statistics (Last 30 Days)</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <p className="text-sm text-slate-500">Total Emails</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900">
                    {analytics.email_statistics?.total_emails || 0}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">By Category</p>
                  <div className="mt-2 space-y-1">
                    {Object.entries(analytics.email_statistics?.by_category || {}).slice(0, 3).map(([cat, count]) => (
                      <div key={cat} className="flex justify-between text-sm">
                        <span className="text-slate-600">{cat}</span>
                        <span className="font-medium">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm text-slate-500">By Sentiment</p>
                  <div className="mt-2 space-y-1">
                    {Object.entries(analytics.email_statistics?.by_sentiment || {}).map(([sent, count]) => (
                      <div key={sent} className="flex justify-between text-sm">
                        <span className="text-slate-600 capitalize">{sent}</span>
                        <span className="font-medium">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Recent Risks */}
          {risks.length > 0 && (
            <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Recent Risks</h2>
              <div className="space-y-3">
                {risks.slice(0, 5).map((risk) => (
                  <div 
                    key={risk.id} 
                    onClick={() => navigate(`/risks/${risk.id}`)}
                    className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
                  >
                    <AlertTriangle className={`h-5 w-5 mt-0.5 ${risk.severity === 'critical' ? 'text-red-600' : 'text-orange-600'}`} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-slate-900">{risk.title}</h3>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(risk.severity)}`}>
                          {risk.severity}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-600">{risk.description}</p>
                      <p className="mt-1 text-xs text-slate-500">{formatDate(risk.created_at)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent Opportunities */}
          {opportunities.length > 0 && (
            <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Recent Opportunities</h2>
              <div className="space-y-3">
                {opportunities.slice(0, 5).map((opp) => (
                  <div 
                    key={opp.id} 
                    onClick={() => navigate(`/opportunities/${opp.id}`)}
                    className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
                  >
                    <TrendingUp className="h-5 w-5 mt-0.5 text-green-600" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-slate-900">{opp.title}</h3>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(opp.status)}`}>
                          {opp.status}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-600">{opp.description}</p>
                      <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
                        {opp.estimated_value && (
                          <span className="flex items-center gap-1">
                            <DollarSign className="h-3 w-3" />
                            ${opp.estimated_value.toLocaleString()}
                          </span>
                        )}
                        {opp.probability && (
                          <span className="flex items-center gap-1">
                            <Target className="h-3 w-3" />
                            {opp.probability}% probability
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Risks Tab */}
      {activeTab === 'risks' && (
        <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">All Risks</h2>
          {risks.length === 0 ? (
            <div className="text-center py-12">
              <AlertTriangle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-500">No risks identified</p>
            </div>
          ) : (
            <div className="space-y-4">
              {risks.map((risk) => (
                <div 
                  key={risk.id} 
                  onClick={() => navigate(`/risks/${risk.id}`)}
                  className="p-4 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-slate-900">{risk.title}</h3>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(risk.severity)}`}>
                          {risk.severity}
                        </span>
                        <span className="px-2 py-1 rounded text-xs bg-slate-100 text-slate-700">
                          {risk.risk_type}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 mb-2">{risk.description}</p>
                      {risk.potential_impact && (
                        <p className="text-sm text-slate-500 mb-2">
                          <strong>Impact:</strong> {risk.potential_impact}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        <span>Created: {formatDate(risk.created_at)}</span>
                        {risk.urgency_score && (
                          <span>Urgency: {risk.urgency_score}/100</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Opportunities Tab */}
      {activeTab === 'opportunities' && (
        <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">All Opportunities</h2>
          {opportunities.length === 0 ? (
            <div className="text-center py-12">
              <TrendingUp className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-500">No opportunities identified</p>
            </div>
          ) : (
            <div className="space-y-4">
              {opportunities.map((opp) => (
                <div 
                  key={opp.id} 
                  onClick={() => navigate(`/opportunities/${opp.id}`)}
                  className="p-4 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-slate-900">{opp.title}</h3>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(opp.status)}`}>
                          {opp.status}
                        </span>
                        <span className="px-2 py-1 rounded text-xs bg-slate-100 text-slate-700">
                          {opp.opportunity_type}
                        </span>
                        {opp.lead_temperature && (
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            opp.lead_temperature === 'hot' ? 'bg-red-100 text-red-800' :
                            opp.lead_temperature === 'warm' ? 'bg-orange-100 text-orange-800' :
                            'bg-blue-100 text-blue-800'
                          }`}>
                            {opp.lead_temperature}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-600 mb-2">{opp.description}</p>
                      <div className="flex items-center gap-4 text-sm">
                        {opp.estimated_value && (
                          <span className="flex items-center gap-1 text-slate-700">
                            <DollarSign className="h-4 w-4" />
                            <strong>${opp.estimated_value.toLocaleString()}</strong>
                          </span>
                        )}
                        {opp.probability && (
                          <span className="flex items-center gap-1 text-slate-700">
                            <Target className="h-4 w-4" />
                            <strong>{opp.probability}%</strong> probability
                          </span>
                        )}
                        {opp.expected_close_date && (
                          <span className="flex items-center gap-1 text-slate-700">
                            <Calendar className="h-4 w-4" />
                            Close: {formatDate(opp.expected_close_date)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Deadlines Tab */}
      {activeTab === 'deadlines' && (
        <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Upcoming Deadlines (Next 7 Days)</h2>
          {deadlines.length === 0 ? (
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 text-slate-400 mx-auto mb-4" />
              <p className="text-slate-500">No upcoming deadlines</p>
            </div>
          ) : (
            <div className="space-y-4">
              {deadlines.map((commitment) => (
                <div
                  key={commitment.id}
                  className={`p-4 rounded-lg border ${
                    isOverdue(commitment.deadline)
                      ? 'border-red-200 bg-red-50'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-slate-900">{commitment.title}</h3>
                        {isOverdue(commitment.deadline) && (
                          <span className="px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
                            Overdue
                          </span>
                        )}
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          commitment.priority === 'high' ? 'bg-red-100 text-red-800' :
                          commitment.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {commitment.priority}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 mb-2">{commitment.description}</p>
                      <div className="flex items-center gap-4 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          Due: {formatDate(commitment.deadline)}
                        </span>
                        <span>Type: {commitment.commitment_type}</span>
                        {commitment.committed_by && (
                          <span>By: {commitment.committed_by}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Relationships Tab */}
      {activeTab === 'relationships' && relationships && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Companies</h2>
            {relationships.companies?.length === 0 ? (
              <p className="text-slate-500">No companies found</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {relationships.companies?.map((company) => (
                  <div 
                    key={company.id} 
                    onClick={() => navigate(`/companies/${company.id}`)}
                    className="p-4 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
                  >
                    <h3 className="font-semibold text-slate-900">{company.name}</h3>
                    <p className="text-sm text-slate-500 mt-1">{company.domain}</p>
                    <div className="mt-3 flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        company.relationship_status === 'active' ? 'bg-green-100 text-green-800' :
                        company.relationship_status === 'warming' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {company.relationship_status}
                      </span>
                      <span className="text-xs text-slate-500">
                        {company.total_contacts} contacts
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Top Contacts</h2>
            {relationships.top_contacts?.length === 0 ? (
              <p className="text-slate-500">No contacts found</p>
            ) : (
              <div className="space-y-3">
                {relationships.top_contacts?.map((contact) => (
                  <div 
                    key={contact.id} 
                    onClick={() => navigate(`/contacts/${contact.id}`)}
                    className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                        <span className="text-indigo-600 font-medium">
                          {(contact.first_name?.[0] || contact.email[0]).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-medium text-slate-900">
                          {contact.display_name || contact.email}
                        </h3>
                        <p className="text-sm text-slate-500">{contact.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          contact.relationship_status === 'active' ? 'bg-green-100 text-green-800' :
                          contact.relationship_status === 'warming' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {contact.relationship_status}
                        </span>
                        <p className="text-xs text-slate-500 mt-1">
                          Score: {Math.round(contact.relationship_score || 0)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default InsightsDashboard;
