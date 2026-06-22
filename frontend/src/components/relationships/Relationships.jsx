import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Building2, Search, Filter, Mail, Calendar, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { insightsApi } from '../../services/api';

const Relationships = () => {
  const [loading, setLoading] = useState(true);
  const [relationships, setRelationships] = useState(null);
  const [activeView, setActiveView] = useState('companies'); // 'companies' or 'contacts'
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    loadRelationships();
  }, []);

  const loadRelationships = async () => {
    setLoading(true);
    try {
      const res = await insightsApi.getRelationships();
      setRelationships(res.data);
    } catch (error) {
      console.error('Failed to load relationships:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-800 border-green-200';
      case 'warming': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'cold': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'ghosting': return 'bg-red-100 text-red-800 border-red-200';
      case 'dormant': return 'bg-gray-100 text-gray-800 border-gray-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getSentimentIcon = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return <TrendingUp className="h-4 w-4 text-green-600" />;
      case 'negative': return <TrendingDown className="h-4 w-4 text-red-600" />;
      default: return null;
    }
  };

  const filteredCompanies = relationships?.companies?.filter((company) => {
    const matchesSearch = !searchTerm || 
      company.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (company.domain && company.domain.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesStatus = filterStatus === 'all' || company.relationship_status === filterStatus;
    return matchesSearch && matchesStatus;
  }) || [];

  const filteredContacts = relationships?.top_contacts?.filter((contact) => {
    const matchesSearch = !searchTerm || 
      (contact.display_name || contact.email).toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || contact.relationship_status === filterStatus;
    return matchesSearch && matchesStatus;
  }) || [];

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
          <h1 className="text-3xl font-bold text-slate-900">Relationships</h1>
          <p className="mt-1 text-sm text-slate-500">Manage your contacts and companies</p>
        </div>
        <button
          onClick={loadRelationships}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500">Total Companies</p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {relationships?.total_companies || 0}
              </p>
            </div>
            <div className="p-3 bg-indigo-100 rounded-lg">
              <Building2 className="h-6 w-6 text-indigo-600" />
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

        <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500">Active Relationships</p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {relationships?.companies?.filter(c => c.relationship_status === 'active').length || 0}
              </p>
            </div>
            <div className="p-3 bg-green-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500">Decision Makers</p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {relationships?.top_contacts?.filter(c => c.is_decision_maker).length || 0}
              </p>
            </div>
            <div className="p-3 bg-yellow-100 rounded-lg">
              <Users className="h-6 w-6 text-yellow-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Tabs and Filters */}
      <div className="bg-white rounded-lg shadow border border-slate-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveView('companies')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeView === 'companies'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <Building2 className="h-4 w-4 inline mr-2" />
              Companies
            </button>
            <button
              onClick={() => setActiveView('contacts')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeView === 'contacts'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <Users className="h-4 w-4 inline mr-2" />
              Contacts
            </button>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="warming">Warming</option>
              <option value="cold">Cold</option>
              <option value="ghosting">Ghosting</option>
              <option value="dormant">Dormant</option>
            </select>
          </div>
        </div>

        {/* Companies View */}
        {activeView === 'companies' && (
          <div>
            {filteredCompanies.length === 0 ? (
              <div className="text-center py-12">
                <Building2 className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <p className="text-slate-500">No companies found</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredCompanies.map((company) => (
                  <div 
                    key={company.id} 
                    onClick={() => navigate(`/companies/${company.id}`)}
                    className="p-4 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-slate-900">{company.name}</h3>
                        {company.domain && (
                          <p className="text-sm text-slate-500 mt-1">{company.domain}</p>
                        )}
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(company.relationship_status)}`}>
                        {company.relationship_status}
                      </span>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Contacts</span>
                        <span className="font-medium">{company.total_contacts || 0}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Emails</span>
                        <span className="font-medium">{company.total_emails || 0}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Last Contact</span>
                        <span className="font-medium">{formatDate(company.last_contact_date)}</span>
                      </div>
                      {company.is_client && (
                        <span className="inline-block px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium">
                          Client
                        </span>
                      )}
                      {company.is_prospect && (
                        <span className="inline-block px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                          Prospect
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Contacts View */}
        {activeView === 'contacts' && (
          <div>
            {filteredContacts.length === 0 ? (
              <div className="text-center py-12">
                <Users className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <p className="text-slate-500">No contacts found</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredContacts.map((contact) => (
                  <div 
                    key={contact.id} 
                    onClick={() => navigate(`/contacts/${contact.id}`)}
                    className="flex items-center justify-between p-4 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-4 flex-1">
                      <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                        <span className="text-indigo-600 font-semibold text-lg">
                          {(contact.first_name?.[0] || contact.email[0]).toUpperCase()}
                        </span>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-slate-900">
                            {contact.display_name || contact.email}
                          </h3>
                          {contact.is_decision_maker && (
                            <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs font-medium">
                              Decision Maker
                            </span>
                          )}
                          {getSentimentIcon(contact.overall_sentiment)}
                        </div>
                        <p className="text-sm text-slate-500 mt-1">{contact.email}</p>
                        {contact.job_title && (
                          <p className="text-sm text-slate-600 mt-1">{contact.job_title}</p>
                        )}
                        <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            {contact.total_emails_received || 0} received
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(contact.last_contact_date)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-3 py-1 rounded text-sm font-medium border ${getStatusColor(contact.relationship_status)}`}>
                        {contact.relationship_status}
                      </span>
                      <p className="text-xs text-slate-500 mt-2">
                        Score: {Math.round(contact.relationship_score || 0)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Relationships;
