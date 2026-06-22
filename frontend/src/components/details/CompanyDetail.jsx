import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, Users, Mail, Calendar, TrendingUp, RefreshCw } from 'lucide-react';
import { insightsApi } from '../../services/api';

const CompanyDetail = () => {
  const { companyId } = useParams();
  const navigate = useNavigate();
  const [company, setCompany] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCompanyDetails();
  }, [companyId]);

  const loadCompanyDetails = async () => {
    setLoading(true);
    try {
      const res = await insightsApi.getCompanyDetails(companyId);
      setCompany(res.data.company);
      setContacts(res.data.contacts || []);
    } catch (error) {
      console.error('Failed to load company details:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!company) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Company not found</p>
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
          <h1 className="text-3xl font-bold text-slate-900">{company.name}</h1>
          {company.domain && <p className="text-slate-500 mt-1">{company.domain}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="md:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Company Information</h2>
            <div className="space-y-4">
              {company.industry && (
                <div>
                  <p className="text-sm text-slate-500">Industry</p>
                  <p className="font-medium">{company.industry}</p>
                </div>
              )}
              {company.company_size && (
                <div>
                  <p className="text-sm text-slate-500">Company Size</p>
                  <p className="font-medium">{company.company_size}</p>
                </div>
              )}
              <div>
                <p className="text-sm text-slate-500">Relationship Status</p>
                <span className={`inline-block px-3 py-1 rounded text-sm font-medium ${
                  company.relationship_status === 'active' ? 'bg-green-100 text-green-800' :
                  company.relationship_status === 'warming' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {company.relationship_status}
                </span>
              </div>
              <div className="flex items-center gap-4">
                {company.is_client && (
                  <span className="px-3 py-1 rounded text-sm font-medium bg-green-100 text-green-800">
                    Client
                  </span>
                )}
                {company.is_prospect && (
                  <span className="px-3 py-1 rounded text-sm font-medium bg-blue-100 text-blue-800">
                    Prospect
                  </span>
                )}
                {company.is_vendor && (
                  <span className="px-3 py-1 rounded text-sm font-medium bg-purple-100 text-purple-800">
                    Vendor
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Contacts */}
          <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Contacts ({contacts.length})</h2>
            {contacts.length === 0 ? (
              <p className="text-slate-500">No contacts found</p>
            ) : (
              <div className="space-y-3">
                {contacts.map((contact) => (
                  <div key={contact.id} className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:bg-slate-50">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                        <span className="text-indigo-600 font-medium">
                          {(contact.first_name?.[0] || contact.email[0]).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">
                          {contact.display_name || contact.email}
                        </p>
                        {contact.job_title && (
                          <p className="text-sm text-slate-500">{contact.job_title}</p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        contact.relationship_status === 'active' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {contact.relationship_status}
                      </span>
                      {contact.is_decision_maker && (
                        <p className="text-xs text-yellow-600 mt-1">Decision Maker</p>
                      )}
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
                <p className="text-sm text-slate-500">Total Contacts</p>
                <p className="text-2xl font-bold text-slate-900">{company.total_contacts || 0}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Total Emails</p>
                <p className="text-xl font-semibold text-slate-900">{company.total_emails || 0}</p>
              </div>
              <div>
                <p className="text-sm text-slate-500">Last Contact</p>
                <p className="text-sm font-medium text-slate-900">{formatDate(company.last_contact_date)}</p>
              </div>
              {company.revenue_impact && (
                <div>
                  <p className="text-sm text-slate-500">Revenue Impact</p>
                  <p className="text-xl font-semibold text-green-600">${company.revenue_impact.toLocaleString()}</p>
                </div>
              )}
            </div>
          </div>

          {company.notes && (
            <div className="bg-white rounded-lg shadow border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Notes</h2>
              <p className="text-sm text-slate-600">{company.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CompanyDetail;
