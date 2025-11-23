import React, { useState, useEffect, useContext } from 'react';
import {
  Plus,
  Save,
  Edit,
  Trash2,
  Copy,
  CheckCircle,
  XCircle,
  Search,
  Filter,
  Code,
  Eye,
  EyeOff,
  Zap,
  Brain,
  MessageSquare,
  FileText,
  Settings,
  ChevronDown,
  Play,
  TestTube
} from 'lucide-react';
import { PromptContext } from '../../context/PromptContext';

const PromptManager = () => {
  const { prompts, createPrompt, updatePrompt, deletePrompt } = useContext(PromptContext);
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [newPrompt, setNewPrompt] = useState({
    name: '',
    description: '',
    template: '',
    category: 'categorization',
    is_active: true
  });
  const [showTestPanel, setShowTestPanel] = useState(false);
  const [testInput, setTestInput] = useState('');
  const [testOutput, setTestOutput] = useState('');
  const [isTesting, setIsTesting] = useState(false);

  const categories = [
    { id: 'categorization', name: 'Categorization', icon: Filter, color: 'bg-blue-100 text-blue-800' },
    { id: 'action_extraction', name: 'Action Extraction', icon: Zap, color: 'bg-green-100 text-green-800' },
    { id: 'reply_draft', name: 'Reply Drafting', icon: MessageSquare, color: 'bg-purple-100 text-purple-800' },
    { id: 'summary', name: 'Summarization', icon: FileText, color: 'bg-orange-100 text-orange-800' },
    { id: 'analysis', name: 'Analysis', icon: Brain, color: 'bg-indigo-100 text-indigo-800' }
  ];

  useEffect(() => {
    if (prompts.length > 0 && !selectedPrompt) {
      setSelectedPrompt(prompts[0]);
    }
  }, [prompts, selectedPrompt]);

  const filteredPrompts = prompts.filter(prompt => {
    const matchesSearch = prompt.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         prompt.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         prompt.template.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = filterCategory === 'all' || prompt.category === filterCategory;
    
    return matchesSearch && matchesCategory;
  });

  const handleCreatePrompt = async () => {
    if (!newPrompt.name || !newPrompt.template) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      await createPrompt(newPrompt);
      setNewPrompt({
        name: '',
        description: '',
        template: '',
        category: 'categorization',
        is_active: true
      });
    } catch (error) {
      console.error('Failed to create prompt:', error);
      alert('Failed to create prompt');
    }
  };

  const handleSavePrompt = async () => {
    if (!selectedPrompt) return;

    try {
      await updatePrompt(selectedPrompt.id, selectedPrompt);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update prompt:', error);
      alert('Failed to update prompt');
    }
  };

  const handleDeletePrompt = async (promptId) => {
    if (!confirm('Are you sure you want to delete this prompt?')) return;

    try {
      await deletePrompt(promptId);
      if (selectedPrompt?.id === promptId) {
        setSelectedPrompt(filteredPrompts.find(p => p.id !== promptId) || null);
      }
    } catch (error) {
      console.error('Failed to delete prompt:', error);
      alert('Failed to delete prompt');
    }
  };

  const handleTestPrompt = async () => {
    if (!selectedPrompt || !testInput) return;

    setIsTesting(true);
    setTestOutput('Testing prompt...');

    // Simulate API call to test the prompt
    setTimeout(() => {
      const mockResponses = {
        categorization: 'Important',
        action_extraction: '{"tasks": [{"task": "Review project report", "deadline": "2024-01-12", "priority": "high"}]}',
        reply_draft: 'Thank you for your email. I will review this and get back to you shortly.',
        summary: 'This email discusses project review requirements and budget considerations for Q4.',
        analysis: '{"sentiment": "professional", "urgency": "high", "key_topics": ["project review", "budget", "timeline"]}'
      };

      setTestOutput(mockResponses[selectedPrompt.category] || 'Test completed successfully.');
      setIsTesting(false);
    }, 2000);
  };

  const getCategoryIcon = (categoryId) => {
    const category = categories.find(c => c.id === categoryId);
    return category ? category.icon : Settings;
  };

  const getCategoryColor = (categoryId) => {
    const category = categories.find(c => c.id === categoryId);
    return category ? category.color : 'bg-gray-100 text-gray-800';
  };

  const formatTemplatePreview = (template) => {
    if (!template) return 'No template defined';
    return template.length > 100 ? template.substring(0, 100) + '...' : template;
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Prompt template copied to clipboard!');
    });
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Prompt Brain</h1>
          <p className="text-gray-600">Manage and customize AI prompt templates</p>
        </div>
        <button
          onClick={() => document.getElementById('create-prompt-modal').showModal()}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Prompt
        </button>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        {/* Prompts List */}
        <div className={`${selectedPrompt ? 'lg:w-2/5' : 'w-full'} flex flex-col`}>
          <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <input
                  type="text"
                  placeholder="Search prompts..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="all">All Categories</option>
                {categories.map(category => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto bg-white rounded-lg border border-gray-200">
            {filteredPrompts.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Brain className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No prompts found</p>
                <p className="text-sm">Create your first prompt to get started</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredPrompts.map((prompt) => {
                  const CategoryIcon = getCategoryIcon(prompt.category);
                  return (
                    <div
                      key={prompt.id}
                      onClick={() => {
                        setSelectedPrompt(prompt);
                        setIsEditing(false);
                        setShowTestPanel(false);
                      }}
                      className={`p-4 cursor-pointer transition-colors ${
                        selectedPrompt?.id === prompt.id
                          ? 'bg-indigo-50 border-l-4 border-indigo-500'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <CategoryIcon className={`h-4 w-4 ${getCategoryColor(prompt.category).split(' ')[1]}`} />
                          <h3 className="font-semibold text-gray-900">
                            {prompt.name}
                          </h3>
                        </div>
                        <div className="flex items-center gap-1">
                          {prompt.is_active && (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          )}
                          {prompt.is_system && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full bg-gray-100 text-gray-800 text-xs">
                              System
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                        {prompt.description || 'No description'}
                      </p>
                      
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full ${getCategoryColor(prompt.category)}`}>
                          {categories.find(c => c.id === prompt.category)?.name || prompt.category}
                        </span>
                        <span>v{prompt.version}</span>
                      </div>
                      
                      <div className="mt-2 text-xs text-gray-400 font-mono">
                        {formatTemplatePreview(prompt.template)}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Prompt Editor */}
        {selectedPrompt && (
          <div className="lg:w-3/5 flex flex-col">
            <div className="bg-white rounded-lg border border-gray-200 flex-1 flex flex-col">
              {/* Editor Header */}
              <div className="border-b border-gray-200 p-4">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    {isEditing ? (
                      <input
                        type="text"
                        value={selectedPrompt.name}
                        onChange={(e) => setSelectedPrompt(prev => ({ ...prev, name: e.target.value }))}
                        className="w-full text-lg font-semibold border-b border-gray-300 focus:border-indigo-500 focus:outline-none pb-1"
                      />
                    ) : (
                      <h2 className="text-lg font-semibold text-gray-900">
                        {selectedPrompt.name}
                      </h2>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowTestPanel(!showTestPanel)}
                      className={`inline-flex items-center px-3 py-1 rounded-lg text-sm ${
                        showTestPanel 
                          ? 'bg-purple-100 text-purple-800' 
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      <TestTube className="h-4 w-4 mr-1" />
                      Test
                    </button>
                    <button
                      onClick={() => copyToClipboard(selectedPrompt.template)}
                      className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                    {!selectedPrompt.is_system && (
                      <button
                        onClick={() => handleDeletePrompt(selectedPrompt.id)}
                        className="p-2 text-red-500 hover:text-red-700 rounded-lg hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">Category:</span>
                    {isEditing ? (
                      <select
                        value={selectedPrompt.category}
                        onChange={(e) => setSelectedPrompt(prev => ({ ...prev, category: e.target.value }))}
                        className="border border-gray-300 rounded px-2 py-1"
                      >
                        {categories.map(category => (
                          <option key={category.id} value={category.id}>
                            {category.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className={`inline-flex items-center px-2 py-1 rounded-full ${getCategoryColor(selectedPrompt.category)}`}>
                        {categories.find(c => c.id === selectedPrompt.category)?.name || selectedPrompt.category}
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">Status:</span>
                    {isEditing ? (
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={selectedPrompt.is_active}
                          onChange={(e) => setSelectedPrompt(prev => ({ ...prev, is_active: e.target.checked }))}
                          className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span>Active</span>
                      </label>
                    ) : (
                      <span className={`inline-flex items-center ${selectedPrompt.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                        {selectedPrompt.is_active ? 'Active' : 'Inactive'}
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">Version:</span>
                    <span className="text-gray-900">v{selectedPrompt.version}</span>
                  </div>
                </div>
              </div>

              {/* Editor Content */}
              <div className="flex-1 flex flex-col min-h-0">
                {isEditing ? (
                  <div className="flex-1 flex flex-col">
                    <div className="p-4 border-b border-gray-200">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description
                      </label>
                      <textarea
                        value={selectedPrompt.description}
                        onChange={(e) => setSelectedPrompt(prev => ({ ...prev, description: e.target.value }))}
                        placeholder="Describe what this prompt does..."
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        rows="3"
                      />
                    </div>
                    
                    <div className="flex-1 p-4">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Prompt Template
                      </label>
                      <textarea
                        value={selectedPrompt.template}
                        onChange={(e) => setSelectedPrompt(prev => ({ ...prev, template: e.target.value }))}
                        placeholder="Enter your prompt template here..."
                        className="w-full h-full p-3 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col">
                    <div className="p-4 border-b border-gray-200">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
                      <p className="text-gray-900">
                        {selectedPrompt.description || 'No description provided.'}
                      </p>
                    </div>
                    
                    <div className="flex-1 p-4 overflow-y-auto">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">Template</h3>
                      <pre className="bg-gray-50 p-4 rounded-lg border border-gray-200 font-mono text-sm whitespace-pre-wrap overflow-x-auto">
                        {selectedPrompt.template}
                      </pre>
                    </div>
                  </div>
                )}
              </div>

              {/* Test Panel */}
              {showTestPanel && (
                <div className="border-t border-gray-200">
                  <div className="p-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Test Prompt</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Test Input</label>
                        <textarea
                          value={testInput}
                          onChange={(e) => setTestInput(e.target.value)}
                          placeholder="Enter test email content..."
                          className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                          rows="3"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Output</label>
                        <div className="bg-gray-50 p-3 rounded-lg border border-gray-200 min-h-[100px]">
                          {isTesting ? (
                            <div className="flex items-center gap-2 text-gray-500">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
                              Testing prompt...
                            </div>
                          ) : (
                            <pre className="font-mono text-sm whitespace-pre-wrap">
                              {testOutput || 'Run test to see output...'}
                            </pre>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={handleTestPrompt}
                        disabled={!testInput || isTesting}
                        className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Play className="h-4 w-4 mr-2" />
                        Run Test
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Editor Footer */}
              <div className="border-t border-gray-200 p-4">
                <div className="flex justify-between items-center">
                  <div className="text-sm text-gray-600">
                    {selectedPrompt.is_system && (
                      <span className="inline-flex items-center text-orange-600">
                        <Settings className="h-4 w-4 mr-1" />
                        System Prompt
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
                          onClick={handleSavePrompt}
                          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                        >
                          <Save className="h-4 w-4 mr-2" />
                          Save Prompt
                        </button>
                      </>
                    ) : (
                      !selectedPrompt.is_system && (
                        <button
                          onClick={() => setIsEditing(true)}
                          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Edit Prompt
                        </button>
                      )
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create Prompt Modal */}
      <dialog id="create-prompt-modal" className="modal">
        <div className="modal-box max-w-2xl">
          <h3 className="font-bold text-lg mb-4">Create New Prompt</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <input
                type="text"
                value={newPrompt.name}
                onChange={(e) => setNewPrompt(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Enter prompt name..."
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={newPrompt.description}
                onChange={(e) => setNewPrompt(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Describe what this prompt does..."
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                rows="3"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category *
              </label>
              <select
                value={newPrompt.category}
                onChange={(e) => setNewPrompt(prev => ({ ...prev, category: e.target.value }))}
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                {categories.map(category => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Template *
              </label>
              <textarea
                value={newPrompt.template}
                onChange={(e) => setNewPrompt(prev => ({ ...prev, template: e.target.value }))}
                placeholder="Enter your prompt template..."
                className="w-full p-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                rows="8"
              />
            </div>
          </div>
          
          <div className="modal-action">
            <form method="dialog">
              <button className="btn btn-ghost mr-2">Cancel</button>
            </form>
            <button
              onClick={handleCreatePrompt}
              disabled={!newPrompt.name || !newPrompt.template}
              className="btn btn-primary"
            >
              Create Prompt
            </button>
          </div>
        </div>
        
        <form method="dialog" className="modal-backdrop">
          <button>close</button>
        </form>
      </dialog>
    </div>
  );
};

export default PromptManager;