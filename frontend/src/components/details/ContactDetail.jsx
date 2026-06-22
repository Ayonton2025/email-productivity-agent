import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Mail, Calendar, TrendingUp, TrendingDown, User, Building2, RefreshCw } from 'lucide-react';
import { insightsApi } from '../../services/api';

const ContactDetail = () => {
  const { contactId } = useParams();
  const navigate = useNavigate();
  const [contact, setContact] = useState(null);
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadContactDetails();
  }, [contactId]);

  const loadContactDetails = async () => {
    setLoading(true);
    try {
      const res = await insightsApi.getContactDetails(contactId);
      setContact(res.data.contact);
      setInteractions(res.data.recent_interactions || []);
    } catch (error) {
      console.error('Failed to load contact details:', error);
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

  const getSentimentIcon = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return <TrendingUp className="h-5 w-5 text-green-600" />;
      case 'negative': return <TrendingDown className="h-5 w-5 text-red-600" />;
      default: return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Contact not found</p>
        <button onClick={() => navigate('/relationships')} className="mt-4 text-indigo-600 hover:text-indigo-700">
          Back to Relationships
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/relationships')}
          className="p-2 hover:bg-slate-100 rounded-lg"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-slate-900">
            {contact.display_name || contact.email}
          </h1>
          <p className="text-slate-500 mt-1">{contact.email}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Info Card */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Contact Information</h2>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <User className="h-5 w-5 text-slate-400" />
                <div>
                  <p className="text-sm text-slate-500">Name</p>
                  <p className="font-medium">{contact.first_name} {contact.last_name}</p>
                </div>
              </div>
              {contact.job_title && (
                <div className="flex items-center gap-3">
                  <Building2 className="h-5 w-5 text-slate-400" />
                  <div>
                    <p className="text-sm text-slate-500">Job Title</p>
                    <p className="font-medium">{contact.job_title}</p>
                  </div>
                </div>
              )}
              {contact.department && (
                <div>
                  <p className="text-sm text-slate-500">Department</p>
                  <p className="font-medium">{contact.department}</p>
                </div>
              )}
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded text-sm font-medium ${
                  contact.relationship_status === 'active' ? 'bg-green-100 text-green-800' :
                  contact.relationship_status === 'warming' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {contact.relationship_status}
                </span>
                {contact.is_decision_maker && (
                  <span className="px-3 py-1 rounded text-sm font-medium bg-yellow-100 text-yellow-800">
                    Decision Maker
                  </span>
                )}
                {getSentimentIcon(contact.overall_sentiment)}
              </div>
            </div>
          </div>

          {/* Interaction History */}
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Recent Interactions</h2>
            {interactions.length === 0 ? (
              <p className="text-slate-500">No interactions yet</p>
            ) : (
              <div className="space-y-3">
                {interactions.map((interaction) => (
                  <div key={interaction.id} className="flex items-start gap-3 p-3 rounded-lg border border-slate-200">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          interaction.direction === 'inbound' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                        }`}>
                          {interaction.direction}
                        </span>
                        <span className="text-sm font-medium">{interaction.interaction_type}</span>
                        {getSentimentIcon(interaction.sentiment)}
                      </div>
                      {interaction.subject && (
                        <p className="text-sm text-slate-600 mb-1">{interaction.subject}</p>
                      )}
                      <p className="text-xs text-slate-500">{formatDate(interaction.interaction_date)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Stats Sidebar */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Statistics</h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-slate-500">Relationship Score</p>
                <p className="text-2xl font-bold text-slate-900">{Math.round(contact.relationship_score || 0)}/100</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Emails Sent</p>
                <p className="text-xl font-semibold text-slate-900">{contact.total_emails_sent || 0}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Emails Received</p>
                <p className="text-xl font-semibold text-slate-900">{contact.total_emails_received || 0}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Last Contact</p>
                <p className="text-sm font-medium text-slate-900">{formatDate(contact.last_contact_date)}</p>
              </div>
              {contact.average_response_time_hours && (
                <div>
                  <p className="text-sm text-slate-500">Avg Response Time</p>
                  <p className="text-sm font-medium text-slate-900">{contact.average_response_time_hours.toFixed(1)} hours</p>
                </div>
              )}
            </div>
          </div>

          {contact.notes && (
            <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Notes</h2>
              <p className="text-sm text-slate-600">{contact.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ContactDetail;
