import React from 'react'

const RelationshipsTab = ({ relationships, navigate }) => (
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
                <span
                  className={`px-2 py-1 rounded text-xs font-medium ${
                    company.relationship_status === 'active'
                      ? 'bg-green-100 text-green-800'
                      : company.relationship_status === 'warming'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {company.relationship_status}
                </span>
                <span className="text-xs text-slate-500">{company.total_contacts} contacts</span>
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
                  <h3 className="font-medium text-slate-900">{contact.display_name || contact.email}</h3>
                  <p className="text-sm text-slate-500">{contact.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      contact.relationship_status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : contact.relationship_status === 'warming'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {contact.relationship_status}
                  </span>
                  <p className="text-xs text-slate-500 mt-1">Score: {Math.round(contact.relationship_score || 0)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  </div>
)

export default RelationshipsTab
