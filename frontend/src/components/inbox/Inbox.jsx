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
  Eye,
  Play,
  Loader
} from 'lucide-react';
import { EmailContext } from '../../context/EmailContext';
import { emailApi, agentApi } from '../../services/api';

const Inbox = () => {
  const { 
    emails, 
    loadEmails, 
    loading, 
    selectedEmail, 
    setSelectedEmail, 
    loadMockEmails,
    setEmails 
  } = useContext(EmailContext);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  
  const [processing, setProcessing] = useState(false);
  const [agentResult, setAgentResult] = useState(null);
  const [agentError, setAgentError] = useState(null);

  useEffect(() => {
    loadMockEmails();
  }, []);

  // Archive/Unarchive email function
  const archiveEmail = async (emailId) => {
    if (!emailId) return;
    
    try {
      console.log('📦 [Inbox] Toggling archive for email:', emailId);
      
      // Update local state first for immediate UI feedback
      setEmails(prev => prev.map(email => 
        email.id === emailId 
          ? { ...email, is_archived: !email.is_archived }
          : email
      ));
      
      if (selectedEmail && selectedEmail.id === emailId) {
        setSelectedEmail(prev => ({ 
          ...prev, 
          is_archived: !prev.is_archived 
        }));
      }
      
      console.log('✅ [Inbox] Email archive toggled successfully');
      
    } catch (err) {
      console.error('❌ [Inbox] Failed to toggle archive:', err);
    }
  };

  // Star/Unstar email function
  const toggleStarEmail = async (emailId) => {
    if (!emailId) return;
    
    try {
      console.log('⭐ [Inbox] Toggling star for email:', emailId);
      
      // Update local state first for immediate UI feedback
      setEmails(prev => prev.map(email => 
        email.id === emailId 
          ? { ...email, is_starred: !email.is_starred }
          : email
      ));
      
      if (selectedEmail && selectedEmail.id === emailId) {
        setSelectedEmail(prev => ({ 
          ...prev, 
          is_starred: !prev.is_starred 
        }));
      }
      
      console.log('✅ [Inbox] Email star toggled successfully');
      
    } catch (err) {
      console.error('❌ [Inbox] Failed to toggle star:', err);
    }
  };

  const generateReply = async () => {
    if (!selectedEmail) return;
    
    setProcessing(true);
    setAgentResult(null);
    setAgentError(null);
    
    console.log('🔄 [Inbox] Generating reply for email:', {
      id: selectedEmail.id,
      subject: selectedEmail.subject,
      sender: selectedEmail.sender
    });
    
    try {
      console.log('🔍 [Inbox] Testing backend connection...');
      const healthCheck = await fetch('https://sunny-recreation-production.up.railway.app/health');
      console.log('✅ [Inbox] Backend health check:', healthCheck.status);
      
      if (!healthCheck.ok) {
        throw new Error(`Backend health check failed: ${healthCheck.status}`);
      }

      console.log('🚀 [Inbox] Calling generate-reply endpoint...');
      
      // Use the actual database ID (UUID) for the backend call
      const response = await emailApi.generateReply(selectedEmail.id);
      console.log('✅ [Inbox] Generate-reply response:', response.data);
      
      if (response.data && response.data.reply) {
        setAgentResult(response.data.reply);
        return;
      }

      // Fallback to agent process if generate-reply doesn't return expected format
      console.log('🔄 [Inbox] Trying agent process endpoint...');
      const requestData = {
        email_id: selectedEmail.id, // Using real database ID
        prompt_type: 'reply_draft',
        email_content: selectedEmail.body,
        email_subject: selectedEmail.subject,
        sender: selectedEmail.sender
      };
      
      const agentResponse = await agentApi.processEmail(requestData);
      console.log('✅ [Inbox] Agent process response:', agentResponse.data);
      
      if (agentResponse.data) {
        if (agentResponse.data.result) {
          setAgentResult(agentResponse.data.result);
        } else if (agentResponse.data.reply) {
          setAgentResult(agentResponse.data.reply);
        } else if (agentResponse.data.message) {
          setAgentResult(agentResponse.data.message);
        } else {
          setAgentResult(JSON.stringify(agentResponse.data, null, 2));
          setAgentError('Unexpected response format - showing raw data');
        }
      } else {
        throw new Error('Empty response from server');
      }
      
    } catch (err) {
      console.error('❌ [Inbox] Detailed error:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        statusText: err.response?.statusText
      });
      
      const errorDetails = err.response?.data?.detail || err.message;
      const statusCode = err.response?.status;
      
      let errorMessage = `Backend Error: ${statusCode ? `Status ${statusCode}` : 'No response'}`;
      if (errorDetails) {
        errorMessage += ` - ${errorDetails}`;
      }
      
      setAgentError(errorMessage);
      
      const mockReply = `Dear ${selectedEmail.sender.split('@')[0]},\n\nThank you for your email regarding "${selectedEmail.subject}".\n\nI have received your message and will review it carefully. Please expect a response within 24-48 hours.\n\nIf this matter requires immediate attention, please don't hesitate to contact me directly.\n\nBest regards,\nUser\n\n---\n[This is a demo reply - Backend connection needs configuration]`;
      setAgentResult(mockReply);
    } finally {
      setProcessing(false);
    }
  };

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

      <div className="mb-6 space-y-4">
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

      <div className="flex-1 flex gap-6 min-h-0">
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
                    key={email.id} // ✅ Using real database ID as key
                    onClick={() => {
                      setSelectedEmail(email); // ✅ Using the actual email object with real ID
                      setAgentResult(null);
                      setAgentError(null);
                    }}
                    className={`p-4 cursor-pointer transition-colors ${
                      selectedEmail?.id === email.id // ✅ Comparing real database IDs
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

        {selectedEmail && (
          <div className="w-1/2 flex flex-col">
            <div className="bg-white rounded-lg border border-gray-200 flex-1 flex flex-col">
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

              <div className="flex-1 p-6 overflow-y-auto">
                <div className="prose max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-gray-900">
                    {selectedEmail.body}
                  </pre>
                </div>

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

                {selectedEmail.summary && (
                  <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                      <Eye className="h-4 w-4" />
                      AI Summary
                    </h3>
                    <p className="text-gray-700">{selectedEmail.summary}</p>
                  </div>
                )}

                {agentResult && (
                  <div className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200">
                    <h3 className="font-semibold text-green-900 mb-2">AI Reply Draft</h3>
                    <div className="text-sm text-green-800 bg-white p-3 rounded border">
                      <pre className="whitespace-pre-wrap font-sans">{agentResult}</pre>
                    </div>
                    {agentError && (
                      <p className="text-xs text-orange-600 mt-2">{agentError}</p>
                    )}
                  </div>
                )}

                {agentError && !agentResult && (
                  <div className="mt-6 p-4 bg-red-50 rounded-lg border border-red-200">
                    <h3 className="font-semibold text-red-900 mb-2">Error</h3>
                    <p className="text-sm text-red-800">{agentError}</p>
                  </div>
                )}
              </div>

              <div className="border-t border-gray-200 p-4">
                <div className="flex gap-2">
                  <button
                    onClick={generateReply}
                    disabled={processing || !selectedEmail}
                    className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {processing ? <Loader className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    {processing ? 'Generating Reply...' : 'Generate AI Reply'}
                  </button>
                  
                  <button 
                    onClick={() => archiveEmail(selectedEmail.id)} // ✅ Using real database ID
                    disabled={!selectedEmail}
                    className={`px-4 py-2 border rounded-lg transition-colors flex items-center justify-center ${
                      selectedEmail?.is_archived 
                        ? 'bg-green-100 border-green-300 text-green-700 hover:bg-green-200' 
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                    title={selectedEmail?.is_archived ? "Unarchive email" : "Archive email"}
                  >
                    <Archive className="h-4 w-4" />
                  </button>
                  
                  <button 
                    onClick={() => toggleStarEmail(selectedEmail.id)} // ✅ Using real database ID
                    disabled={!selectedEmail}
                    className={`px-4 py-2 border rounded-lg transition-colors flex items-center justify-center ${
                      selectedEmail?.is_starred 
                        ? 'bg-yellow-100 border-yellow-300 text-yellow-700 hover:bg-yellow-200' 
                        : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                    title={selectedEmail?.is_starred ? "Unstar email" : "Star email"}
                  >
                    <Star className={`h-4 w-4 ${selectedEmail?.is_starred ? 'fill-current' : ''}`} />
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
