import React from 'react';
import { Mail, Star, Archive, Clock, AlertCircle, Calendar } from 'lucide-react';

const EmailList = ({ emails, loading, selectedEmail, onSelectEmail }) => {
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading emails...</p>
        </div>
      </div>
    );
  }

  if (emails.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Mail className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No emails</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by loading some mock emails.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto border border-gray-200 rounded-lg bg-white">
      <div className="divide-y divide-gray-200">
        {emails.map((email) => (
          <div
            key={email.id}
            onClick={() => onSelectEmail(email)}
            className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
              selectedEmail?.id === email.id ? 'bg-indigo-50 border-r-4 border-indigo-500' : ''
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {email.sender}
                  </p>
                  <div className="flex items-center space-x-2 ml-2">
                    {!email.is_read && (
                      <span className="inline-block h-2 w-2 rounded-full bg-blue-600"></span>
                    )}
                    <span className="text-xs text-gray-500">
                      {new Date(email.timestamp).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <p className="text-sm font-semibold text-gray-900 mt-1">
                  {email.subject}
                </p>
                <p className="text-sm text-gray-500 truncate mt-1">
                  {email.body.substring(0, 100)}...
                </p>
                <div className="flex items-center mt-2 space-x-2">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    email.category === 'Important' ? 'bg-red-100 text-red-800' :
                    email.category === 'To-Do' ? 'bg-blue-100 text-blue-800' :
                    email.category === 'Newsletter' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {email.category}
                  </span>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    email.priority === 'high' ? 'bg-red-100 text-red-800' :
                    email.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {email.priority}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EmailList;