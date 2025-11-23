import React, { useState, useEffect, useContext } from 'react';
import { 
  Plus, 
  Save, 
  Edit, 
  Trash2, 
  Send, 
  Copy, 
  Eye, 
  EyeOff,
  Search,
  Filter,
  Clock,
  User,
  Mail,
  FileText,
  MoreVertical,
  ChevronDown
} from 'lucide-react';
import { EmailContext } from '../../context/EmailContext';

const DraftManager = () => {
  const { emails } = useContext(EmailContext);
  const [drafts, setDrafts] = useState([]);
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showPreview, setShowPreview] = useState(true);

  // Mock drafts data - in a real app, this would come from your backend
  const mockDrafts = [
    {
      id: 'draft-1',
      subject: 'Re: Q4 Project Review Meeting',
      body: `Dear Sarah,

Thank you for scheduling the Q4 project review meeting. I have reviewed the attached project report and would like to discuss the following points:

1. The budget utilization seems to be on track, but I have some questions about the Q1 resource allocation.
2. I've identified potential risks in the current timeline that we should address.

I'm available on Tuesday at 2:00 PM or Wednesday morning. Please let me know what works best for your schedule.

Best regards,
[Your Name]`,
      recipient: 'project.manager@company.com',
      context_email_id: '1',
      status: 'draft',
      tone: 'professional',
      metadata: {
        ai_generated: true,
        word_count: 98,
        sentiment: 'professional'
      },
      created_at: '2024-01-08T14:30:00Z',
      updated_at: '2024-01-08T14:30:00Z'
    },
    {
      id: 'draft-2',
      subject: 'Follow-up: Benefits Enrollment',
      body: `Hello HR Team,

I wanted to follow up on the benefits enrollment deadline. I've completed my selections but have a question about dependent coverage.

Could you please clarify if part-time dependents are eligible for coverage under the new plan?

Thank you for your assistance.

Best regards,
[Your Name]`,
      recipient: 'hr@company.com',
      context_email_id: '3',
      status: 'ready',
      tone: 'formal',
      metadata: {
        ai_generated: true,
        word_count: 65,
        sentiment: 'inquisitive'
      },
      created_at: '2024-01-08T15:45:00Z',
      updated_at: '2024-01-08T16:20:00Z'
    },
    {
      id: 'draft-3',
      subject: 'Lunch Meeting Confirmation',
      body: `Hey Mike!

The new Italian place sounds great! I'd love to discuss the marketing campaign and share some ideas I've been working on.

12:30 PM tomorrow works perfectly for me. Looking forward to it!

Cheers,
[Your Name]`,
      recipient: 'colleague@company.com',
      context_email_id: '5',
      status: 'draft',
      tone: 'casual',
      metadata: {
        ai_generated: true,
        word_count: 45,
        sentiment: 'friendly'
      },
      created_at: '2024-01-08T16:15:00Z',
      updated_at: '2024-01-08T16:15:00Z'
    }
  ];

  useEffect(() => {
    // Load drafts - in real app, this would be an API call
    setDrafts(mockDrafts);
    if (mockDrafts.length > 0 && !selectedDraft) {
      setSelectedDraft(mockDrafts[0]);
    }
  }, []);

  const filteredDrafts = drafts.filter(draft => {
    const matchesSearch = draft.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         draft.recipient.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         draft.body.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = filterStatus === 'all' || draft.status === filterStatus;
    
    return matchesSearch && matchesStatus;
  });

  const handleCreateDraft = () => {
    const newDraft = {
      id: `draft-${Date.now()}`,
      subject: '',
      body: '',
      recipient: '',
      status: 'draft',
      tone: 'professional',
      metadata: {
        ai_generated: false,
        word_count: 0,
        sentiment: 'neutral'
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    
    setDrafts(prev => [newDraft, ...prev]);
    setSelectedDraft(newDraft);
    setIsEditing(true);
  };

  const handleSaveDraft = () => {
    if (!selectedDraft) return;
    
    setDrafts(prev => 
      prev.map(draft => 
        draft.id === selectedDraft.id 
          ? { ...selectedDraft, updated_at: new Date().toISOString() }
          : draft
      )
    );
    setIsEditing(false);
  };

  const handleDeleteDraft = (draftId) => {
    setDrafts(prev => prev.filter(draft => draft.id !== draftId));
    if (selectedDraft?.id === draftId) {
      setSelectedDraft(filteredDrafts.find(draft => draft.id !== draftId) || null);
    }
  };

  const handleInputChange = (field, value) => {
    if (!selectedDraft) return;
    
    setSelectedDraft(prev => ({
      ...prev,
      [field]: value,
      metadata: {
        ...prev.metadata,
        word_count: field === 'body' ? value.split(/\s+/).filter(word => word.length > 0).length : prev.metadata.word_count
      }
    }));
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'draft': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'ready': return 'bg-green-100 text-green-800 border-green-200';
      case 'sent': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getToneColor = (tone) => {
    switch (tone) {
      case 'professional': return 'bg-purple-100 text-purple-800';
      case 'casual': return 'bg-orange-100 text-orange-800';
      case 'formal': return 'bg-indigo-100 text-indigo-800';
      case 'friendly': return 'bg-teal-100 text-teal-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Email Drafts</h1>
          <p className="text-gray-600">Create, edit, and manage your email drafts</p>
        </div>
        <button
          onClick={handleCreateDraft}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Draft
        </button>
      </div>

      {/* Stats and Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-gray-900">{drafts.length}</div>
          <div className="text-sm text-gray-600">Total Drafts</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-yellow-600">
            {drafts.filter(d => d.status === 'draft').length}
          </div>
          <div className="text-sm text-gray-600">In Progress</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-green-600">
            {drafts.filter(d => d.status === 'ready').length}
          </div>
          <div className="text-sm text-gray-600">Ready to Send</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-2xl font-bold text-blue-600">
            {drafts.filter(d => d.metadata?.ai_generated).length}
          </div>
          <div className="text-sm text-gray-600">AI Generated</div>
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        {/* Drafts List */}
        <div className={`${selectedDraft ? 'lg:w-2/5' : 'w-full'} flex flex-col`}>
          <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <input
                  type="text"
                  placeholder="Search drafts..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="all">All Status</option>
                <option value="draft">Draft</option>
                <option value="ready">Ready</option>
                <option value="sent">Sent</option>
              </select>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-white rounded-lg border border-gray-200">
            {filteredDrafts.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No drafts found</p>
                <p className="text-sm">Create your first draft to get started</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredDrafts.map((draft) => (
                  <div
                    key={draft.id}
                    onClick={() => {
                      setSelectedDraft(draft);
                      setIsEditing(false);
                    }}
                    className={`p-4 cursor-pointer transition-colors ${
                      selectedDraft?.id === draft.id
                        ? 'bg-indigo-50 border-l-4 border-indigo-500'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-gray-900 truncate">
                        {draft.subject || 'Untitled Draft'}
                      </h3>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(draft.status)}`}>
                        {draft.status}
                      </span>
                    </div>
                    
                    <div className="flex items-center text-sm text-gray-600 mb-2">
                      <User className="h-3 w-3 mr-1" />
                      <span className="truncate">{draft.recipient || 'No recipient'}</span>
                    </div>
                    
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <div className="flex items-center">
                        <Clock className="h-3 w-3 mr-1" />
                        {formatDate(draft.updated_at)}
                      </div>
                      {draft.metadata?.ai_generated && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full bg-gradient-to-r from-purple-100 to-blue-100 text-purple-800 text-xs">
                          AI
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Draft Editor */}
        {selectedDraft && (
          <div className="lg:w-3/5 flex flex-col">
            <div className="bg-white rounded-lg border border-gray-200 flex-1 flex flex-col">
              {/* Editor Header */}
              <div className="border-b border-gray-200 p-4">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    {isEditing ? (
                      <input
                        type="text"
                        value={selectedDraft.subject}
                        onChange={(e) => handleInputChange('subject', e.target.value)}
                        placeholder="Email subject..."
                        className="w-full text-lg font-semibold border-b border-gray-300 focus:border-indigo-500 focus:outline-none pb-1"
                      />
                    ) : (
                      <h2 className="text-lg font-semibold text-gray-900">
                        {selectedDraft.subject || 'Untitled Draft'}
                      </h2>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowPreview(!showPreview)}
                      className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
                    >
                      {showPreview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                    <button className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100">
                      <Copy className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteDraft(selectedDraft.id)}
                      className="p-2 text-red-500 hover:text-red-700 rounded-lg hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="flex flex-wrap gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4 text-gray-400" />
                    <span className="text-gray-600">To:</span>
                    {isEditing ? (
                      <input
                        type="text"
                        value={selectedDraft.recipient}
                        onChange={(e) => handleInputChange('recipient', e.target.value)}
                        placeholder="recipient@example.com"
                        className="border-b border-gray-300 focus:border-indigo-500 focus:outline-none flex-1 min-w-0"
                      />
                    ) : (
                      <span className="text-gray-900">{selectedDraft.recipient || 'No recipient'}</span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">Tone:</span>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${getToneColor(selectedDraft.tone)}`}>
                      {selectedDraft.tone}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">Words:</span>
                    <span className="text-gray-900">{selectedDraft.metadata?.word_count || 0}</span>
                  </div>
                </div>
              </div>

              {/* Editor Content */}
              <div className="flex-1 flex flex-col min-h-0">
                {isEditing ? (
                  <textarea
                    value={selectedDraft.body}
                    onChange={(e) => handleInputChange('body', e.target.value)}
                    placeholder="Write your email here..."
                    className="flex-1 p-4 resize-none border-none focus:outline-none focus:ring-0"
                    rows="15"
                  />
                ) : (
                  <div className="flex-1 p-4 overflow-y-auto">
                    <div className="prose max-w-none">
                      {selectedDraft.body ? (
                        <pre className="whitespace-pre-wrap font-sans text-gray-900">
                          {selectedDraft.body}
                        </pre>
                      ) : (
                        <p className="text-gray-500 italic">No content yet. Start editing to add your email content.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Editor Footer */}
              <div className="border-t border-gray-200 p-4">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Clock className="h-4 w-4" />
                    Last updated: {formatDate(selectedDraft.updated_at)}
                    {selectedDraft.metadata?.ai_generated && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full bg-gradient-to-r from-purple-100 to-blue-100 text-purple-800 text-xs">
                        AI Generated
                      </span>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    {isEditing ? (
                      <>
                        <button
                          onClick={() => setIsEditing(false)}
                          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleSaveDraft}
                          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                        >
                          <Save className="h-4 w-4 mr-2" />
                          Save Draft
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => setIsEditing(true)}
                          className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Edit
                        </button>
                        <button className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
                          <Send className="h-4 w-4 mr-2" />
                          Send
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DraftManager;