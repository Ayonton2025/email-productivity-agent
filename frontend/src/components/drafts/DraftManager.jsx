import React, { useState, useEffect } from 'react';
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
  Clock,
  User,
  Mail,
  FileText,
} from 'lucide-react';
import { draftApi } from '../../services/api';

const DraftManager = () => {
  const [drafts, setDrafts] = useState([]);
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showPreview, setShowPreview] = useState(true);
  const [loading, setLoading] = useState(true);

  const normalizeDraft = (draft) => {
    const metadata = draft?.metadata || {};
    return {
      ...draft,
      subject: draft?.subject || '',
      body: draft?.body || '',
      recipient: draft?.recipient || '',
      status: metadata.status || 'draft',
      tone: metadata.tone || 'professional',
      metadata: {
        ai_generated: Boolean(metadata.ai_generated),
        word_count: metadata.word_count ?? (draft?.body || '').split(/\s+/).filter(Boolean).length,
        sentiment: metadata.sentiment || 'neutral',
        ...metadata,
      },
    };
  };

  const loadDrafts = async () => {
    setLoading(true);
    try {
      const res = await draftApi.getDrafts();
      const list = Array.isArray(res?.data) ? res.data.map(normalizeDraft) : [];
      setDrafts(list);
      setSelectedDraft((prev) => {
        if (!list.length) return null;
        if (!prev) return list[0];
        return list.find((d) => d.id === prev.id) || list[0];
      });
    } catch (error) {
      console.error('Failed to load drafts:', error);
      setDrafts([]);
      setSelectedDraft(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDrafts();
  }, []);

  const filteredDrafts = drafts.filter(draft => {
    const matchesSearch = draft.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         draft.recipient.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         draft.body.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = filterStatus === 'all' || draft.status === filterStatus;
    
    return matchesSearch && matchesStatus;
  });

  const handleCreateDraft = async () => {
    try {
      const now = new Date().toISOString();
      const payload = {
        subject: 'Untitled Draft',
        body: '',
        recipient: '',
        metadata: {
          status: 'draft',
          tone: 'professional',
          ai_generated: false,
          word_count: 0,
          sentiment: 'neutral',
        },
      };
      const res = await draftApi.createDraft(payload);
      const created = normalizeDraft(res?.data || { ...payload, id: `temp-${Date.now()}`, created_at: now, updated_at: now });
      setDrafts((prev) => [created, ...prev]);
      setSelectedDraft(created);
      setIsEditing(true);
    } catch (error) {
      console.error('Failed to create draft:', error);
      alert('Failed to create draft');
    }
  };

  const handleSaveDraft = async () => {
    if (!selectedDraft) return;

    try {
      const metadata = {
        ...(selectedDraft.metadata || {}),
        status: selectedDraft.status || 'draft',
        tone: selectedDraft.tone || 'professional',
      };
      const payload = {
        subject: selectedDraft.subject || 'Untitled Draft',
        body: selectedDraft.body || '',
        recipient: selectedDraft.recipient || '',
        metadata,
      };
      const res = await draftApi.updateDraft(selectedDraft.id, payload);
      const updated = normalizeDraft(res?.data || { ...selectedDraft, ...payload, updated_at: new Date().toISOString() });

      setDrafts((prev) => prev.map((draft) => (draft.id === updated.id ? updated : draft)));
      setSelectedDraft(updated);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save draft:', error);
      alert('Failed to save draft');
    }
  };

  const handleDeleteDraft = async (draftId) => {
    try {
      await draftApi.deleteDraft(draftId);
      setDrafts((prev) => {
        const remaining = prev.filter((draft) => draft.id !== draftId);
        if (selectedDraft?.id === draftId) {
          setSelectedDraft(remaining.length ? remaining[0] : null);
        }
        return remaining;
      });
    } catch (error) {
      console.error('Failed to delete draft:', error);
      alert('Failed to delete draft');
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
            {loading ? (
              <div className="text-center py-12 text-gray-500">
                <p>Loading drafts...</p>
              </div>
            ) : filteredDrafts.length === 0 ? (
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
