import React, { useState, useEffect, useContext } from 'react';
import { 
  Search, 
  Filter, 
  RefreshCw, 
  Mail, 
  Star, 
  Archive, 
  Clock, 
  AlertCircle,
  Calendar, 
  CheckCircle, 
  MessageSquare, 
  Plus,
  Eye
} from 'lucide-react';
import { EmailContext } from '../../context/EmailContext';

const Inbox = () => {
  const { emails, loadEmails, loading, selectedEmail, setSelectedEmail, loadMockEmails } = useContext(EmailContext);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [sortBy, setSortBy] = useState('newest');

  useEffect(() => {
    loadMockEmails();
  }, []);

  const categories = ['all', 'Important', 'Newsletter', 'Spam', 'To-Do'];
  
  const filteredEmails = emails.filter(email => {
    const matchesSearch = email.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         email.sender.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         email.body.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = filterCategory === 'all' || email.category === filterCategory;
    
    return matchesSearch && matchesCategory;
  });

  const sortedEmails = [...filteredEmails].sort((a, b) => {
    if (sortBy === 'newest') {
      return new Date(b.timestamp) - new Date(a.timestamp);
    } else if (sortBy === 'oldest') {
      return new Date(a.timestamp) - new Date(b.timestamp);
    } else if (sortBy === 'sender') {
      return a.sender.localeCompare(b.sender);
    }
    return 0;
  });

  const getCategoryStats = () => {
    const stats = {
      all: emails.length,
      Important: emails.filter(e => e.category === 'Important').length,
      Newsletter: emails.filter(e => e.category === 'Newsletter').length,
      Spam: emails.filter(e => e.category === 'Spam').length,
      'To-Do': emails.filter(e => e.category === 'To-Do').length,
    };
    return stats;
  };

  const categoryStats = getCategoryStats();

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case 'high': return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'medium': return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'low': return <CheckCircle className="h-4 w-4 text-green-500" />;
      default: return <Mail className="h-4 w-4 text-gray-400" />;
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inbox</h1>
          <p className="text-gray-600">Manage and process your emails with AI</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={loadMockEmails}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Load Mock Inbox
          </button>
          <button
            onClick={loadEmails}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats and Filters */}
      <div className="mb-6 space-y-4">
        {/* Category Quick Stats */}
        <div className="flex space-x-4 overflow-x-auto pb-2">
          {categories.map(category => (
            <button
              key={category}
              onClick={() => setFilterCategory(category)}
              className={`flex items-center px-4 py-2 rounded-lg border whitespace-nowrap ${
                filterCategory === category
                  ? 'bg-indigo-50 border-indigo-500 text-indigo-700'
                  : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span className="font-medium capitalize">{category}</span>
              <span className="ml-2 px-2 py-1 text-xs bg-gray-100 rounded-full">
                {categoryStats[category]}
              </span>
            </button>
          ))}
        </div>

        {/* Search and Sort */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <input
              type="text"
              placeholder="Search emails..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="sender">By Sender</option>
          </select>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-6 min-h-0">
        {/* Email List */}
        <div className={`${selectedEmail ? 'w-1/2' : 'w-full'} flex flex-col`}>
          <div className="flex-1 overflow-y-auto bg-white rounded-lg border border-gray-200">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
              </div>
            ) : sortedEmails.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Mail className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No emails found</p>
                <p className="text-sm">Load mock data to get started</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {sortedEmails.map((email) => (
                  <div
                    key={email.id}
                    onClick={() => setSelectedEmail(email)}
                    className={`p-4 cursor-pointer transition-colors ${
                      selectedEmail?.id === email.id
                        ? 'bg-indigo-50 border-l-4 border-indigo-500'
                        : 'hover:bg-gray-50'
                    } ${!email.is_read ? 'bg-blue-50' : ''}`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        {getPriorityIcon(email.priority)}
                        <h3 className="font-semibold text-gray-900 truncate">
                          {email.subject}
                        </h3>
                      </div>
                      <div className="flex items-center gap-2">
                        {!email.is_read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        )}
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          email.category === 'Important' ? 'bg-red-100 text-red-800' :
                          email.category === 'To-Do' ? 'bg-green-100 text-green-800' :
                          email.category === 'Newsletter' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {email.category}
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex items-center text-sm text-gray-600 mb-2">
                      <span className="truncate">{email.sender}</span>
                    </div>
                    
                    <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                      {email.body}
                    </p>
                    
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{formatDate(email.timestamp)}</span>
                      {email.action_items && email.action_items.length > 0 && (
                        <span className="inline-flex items-center gap-1">
                          <MessageSquare className="h-3 w-3" />
                          {email.action_items.length} action(s)
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Email Detail */}
        {selectedEmail && (
          <div className="w-1/2 flex flex-col">
            <div className="bg-white rounded-lg border border-gray-200 flex-1 flex flex-col">
              {/* Email Header */}
              <div className="border-b border-gray-200 p-6">
                <div className="flex justify-between items-start mb-4">
                  <h2 className="text-xl font-bold text-gray-900">
                    {selectedEmail.subject}
                  </h2>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                      selectedEmail.category === 'Important' ? 'bg-red-100 text-red-800' :
                      selectedEmail.category === 'To-Do' ? 'bg-green-100 text-green-800' :
                      selectedEmail.category === 'Newsletter' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {selectedEmail.category}
                    </span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <div>
                    <span className="font-medium">From: </span>
                    {selectedEmail.sender}
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {formatDate(selectedEmail.timestamp)}
                    </span>
                    {getPriorityIcon(selectedEmail.priority)}
                  </div>
                </div>
              </div>

              {/* Email Body */}
              <div className="flex-1 p-6 overflow-y-auto">
                <div className="prose max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-gray-900">
                    {selectedEmail.body}
                  </pre>
                </div>

                {/* Action Items */}
                {selectedEmail.action_items && selectedEmail.action_items.length > 0 && (
                  <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h3 className="font-semibold text-gray-900 mb-3">Action Items</h3>
                    <div className="space-y-2">
                      {selectedEmail.action_items.map((item, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-white rounded border">
                          <div>
                            <span className="font-medium text-gray-900">{item.task}</span>
                            {item.deadline && (
                              <p className="text-sm text-gray-600">
                                Due: {new Date(item.deadline).toLocaleDateString()}
                              </p>
                            )}
                          </div>
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            item.priority === 'high' ? 'bg-red-100 text-red-800' :
                            item.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {item.priority || 'medium'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI Summary */}
                {selectedEmail.summary && (
                  <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                      <Eye className="h-4 w-4" />
                      AI Summary
                    </h3>
                    <p className="text-gray-700">{selectedEmail.summary}</p>
                  </div>
                )}
              </div>

              {/* Email Actions */}
              <div className="border-t border-gray-200 p-4">
                <div className="flex gap-2">
                  <button className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
                    Reply
                  </button>
                  <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
                    <Archive className="h-4 w-4" />
                  </button>
                  <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
                    <Star className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Inbox;