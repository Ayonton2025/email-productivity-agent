import React, { useState } from 'react';
import { Mail, Star, Archive, Clock, AlertCircle, Calendar, ChevronLeft, ChevronRight, Paperclip } from 'lucide-react';

const EmailList = ({ emails, loading, selectedEmail, onSelectEmail }) => {
  const [currentPage, setCurrentPage] = useState(0);
  const emailsPerPage = 10;
  
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

  // Calculate pagination
  const totalPages = Math.ceil(emails.length / emailsPerPage);
  const startIndex = currentPage * emailsPerPage;
  const endIndex = startIndex + emailsPerPage;
  const currentEmails = emails.slice(startIndex, endIndex);

  // Reset page if it exceeds max pages
  React.useEffect(() => {
    if (currentPage >= totalPages && totalPages > 0) {
      setCurrentPage(totalPages - 1);
    }
  }, [emails.length, currentPage, totalPages]);

  return (
    <div className="flex-1 overflow-hidden border border-gray-200 rounded-lg bg-white flex flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-gray-200">
          {currentEmails.map((email) => (
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
                      {email.attachments && email.attachments.length > 0 && (
                        <div className="flex items-center bg-blue-50 px-2 py-0.5 rounded text-xs text-blue-700 font-medium">
                          <Paperclip className="h-3 w-3 mr-1" />
                          {email.attachments.length}
                        </div>
                      )}
                      <span className="text-xs text-gray-500 whitespace-nowrap">
                        {new Date(email.timestamp).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm font-semibold text-gray-900 mt-1">
                    {email.subject}
                  </p>
                  <p className="text-sm text-gray-500 truncate mt-1">
                    {(email.body_text || email.body || '').substring(0, 100)}...
                  </p>
                  <div className="flex items-center mt-2 space-x-2">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      email.ai_category === 'Important' || email.category === 'Important' ? 'bg-red-100 text-red-800' :
                      email.ai_category === 'To-Do' || email.category === 'To-Do' ? 'bg-blue-100 text-blue-800' :
                      email.ai_category === 'Newsletter' || email.category === 'Newsletter' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {email.ai_category || email.category || 'Uncategorized'}
                    </span>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      email.priority === 'high' ? 'bg-red-100 text-red-800' :
                      email.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {email.priority || 'Normal'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="border-t border-gray-200 bg-gray-50 px-4 py-3 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Showing {startIndex + 1} to {Math.min(endIndex, emails.length)} of {emails.length} emails
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
              disabled={currentPage === 0}
              className="p-2 rounded border border-gray-300 text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            
            <div className="flex items-center space-x-1">
              {Array.from({ length: totalPages }).map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentPage(idx)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    currentPage === idx
                      ? 'bg-indigo-600 text-white'
                      : 'border border-gray-300 text-gray-700 hover:bg-white'
                  }`}
                >
                  {idx + 1}
                </button>
              ))}
            </div>

            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages - 1, prev + 1))}
              disabled={currentPage === totalPages - 1}
              className="p-2 rounded border border-gray-300 text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailList;