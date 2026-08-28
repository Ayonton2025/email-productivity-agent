import { logger } from '../../utils/logger.js'
import React, { useState, useEffect, useContext } from 'react'
import { Plus, Filter, Zap, Brain, MessageSquare, FileText, Settings } from 'lucide-react'
import { PromptContext } from '../../context/PromptContext'
import { aiApi } from '../../services/api'
import PromptAIDraft from './PromptAIDraft'
import PromptEditor from './PromptEditor'
import PromptList from './PromptList'

const PromptManager = () => {
  const { prompts, createPrompt, updatePrompt, deletePrompt, testPrompt, loading } = useContext(PromptContext)
  const [selectedPrompt, setSelectedPrompt] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCategory, setFilterCategory] = useState('all')
  const [newPrompt, setNewPrompt] = useState({
    name: '',
    description: '',
    template: '',
    category: 'categorization',
    is_active: true,
  })
  const [showTestPanel, setShowTestPanel] = useState(false)
  const [testInput, setTestInput] = useState('')
  const [testOutput, setTestOutput] = useState('')
  const [isTesting, setIsTesting] = useState(false)
  const [error, setError] = useState('')
  const [aiGoal, setAiGoal] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiMeta, setAiMeta] = useState({ provider: null, model: null })

  const categories = [
    { id: 'categorization', name: 'Categorization', icon: Filter, color: 'bg-blue-100 text-blue-800' },
    { id: 'action_extraction', name: 'Action Extraction', icon: Zap, color: 'bg-green-100 text-green-800' },
    { id: 'reply_draft', name: 'Reply Drafting', icon: MessageSquare, color: 'bg-purple-100 text-purple-800' },
    { id: 'summary', name: 'Summarization', icon: FileText, color: 'bg-orange-100 text-orange-800' },
    { id: 'analysis', name: 'Analysis', icon: Brain, color: 'bg-indigo-100 text-indigo-800' },
  ]
  const aiQuickPrompts = [
    'Create a concise reply_draft prompt for enterprise email threads',
    'Create an action_extraction prompt focused on deadlines and owners',
  ]

  useEffect(() => {
    if (prompts.length > 0 && !selectedPrompt) {
      setSelectedPrompt(prompts[0])
    }
  }, [prompts, selectedPrompt])

  const filteredPrompts = prompts.filter((prompt) => {
    const matchesSearch =
      prompt.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prompt.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prompt.template.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesCategory = filterCategory === 'all' || prompt.category === filterCategory

    return matchesSearch && matchesCategory
  })

  const handleCreatePrompt = async () => {
    if (!newPrompt.name || !newPrompt.template) {
      alert('Please fill in all required fields')
      return
    }

    setError('')

    try {
      await createPrompt(newPrompt)
      setNewPrompt({
        name: '',
        description: '',
        template: '',
        category: 'categorization',
        is_active: true,
      })
      // Close the modal
      document.getElementById('create-prompt-modal').close()
    } catch (error) {
      logger.error('Failed to create prompt:', error)
      setError('Failed to create prompt: ' + (error.message || 'Unknown error'))
    }
  }

  const handleSavePrompt = async () => {
    if (!selectedPrompt) return

    setError('')

    try {
      await updatePrompt(selectedPrompt.id, selectedPrompt)
      setIsEditing(false)
    } catch (error) {
      logger.error('Failed to update prompt:', error)
      setError('Failed to update prompt: ' + (error.message || 'Unknown error'))
    }
  }

  const handleDeletePrompt = async (promptId) => {
    if (!confirm('Are you sure you want to delete this prompt?')) return

    setError('')

    try {
      await deletePrompt(promptId)
      if (selectedPrompt?.id === promptId) {
        setSelectedPrompt(filteredPrompts.find((p) => p.id !== promptId) || null)
      }
    } catch (error) {
      logger.error('Failed to delete prompt:', error)
      setError('Failed to delete prompt: ' + (error.message || 'Unknown error'))
    }
  }

  const handleTestPrompt = async () => {
    if (!selectedPrompt || !testInput) return

    setIsTesting(true)
    setError('')
    setTestOutput('Testing prompt...')

    try {
      const result = await testPrompt(selectedPrompt.id, testInput)
      setTestOutput(result.output || 'No output generated')
    } catch (error) {
      logger.error('Failed to test prompt:', error)
      setError('Failed to test prompt: ' + (error.message || 'Unknown error'))
      setTestOutput('Error: ' + (error.message || 'Failed to test prompt'))
    } finally {
      setIsTesting(false)
    }
  }

  const getCategoryIcon = (categoryId) => {
    const category = categories.find((c) => c.id === categoryId)
    return category ? category.icon : Settings
  }

  const getCategoryColor = (categoryId) => {
    const category = categories.find((c) => c.id === categoryId)
    return category ? category.color : 'bg-gray-100 text-gray-800'
  }

  const formatTemplatePreview = (template) => {
    if (!template) return 'No template defined'
    return template.length > 100 ? template.substring(0, 100) + '...' : template
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Prompt template copied to clipboard!')
    })
  }

  const handleGeneratePromptDraft = async (goal) => {
    if (!goal?.trim()) return
    setAiLoading(true)
    setError('')
    try {
      const res = await aiApi.assistWorkspace({
        page: 'prompts',
        objective: goal.trim(),
        mode: 'draft',
        context: { existing_prompt_count: prompts.length },
      })
      const draft = res.data?.draft?.prompt || {}
      setAiMeta({ provider: res.data?.provider, model: res.data?.model })
      if (Object.keys(draft).length > 0) {
        setNewPrompt((prev) => ({ ...prev, ...draft }))
        document.getElementById('create-prompt-modal').showModal()
      }
    } catch (aiErr) {
      const detail =
        aiErr?.response?.data?.detail ||
        aiErr?.response?.data?.error ||
        aiErr?.message ||
        'Failed to generate prompt draft'
      setError(detail)
    } finally {
      setAiLoading(false)
    }
  }

  // Separate system and user prompts
  const systemPrompts = prompts.filter((p) => p.is_system)
  const userPrompts = prompts.filter((p) => !p.is_system)

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Prompt Brain</h1>
          <p className="text-sm text-slate-500">Manage and customize AI prompt templates</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => document.getElementById('create-prompt-modal').showModal()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            <Plus className="h-4 w-4" />
            New Prompt
          </button>
        </div>
        {(aiMeta.provider || aiMeta.model) && (
          <p className="text-[11px] text-slate-500">
            Provider: {aiMeta.provider || 'n/a'} | Model: {aiMeta.model || 'n/a'}
          </p>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      <PromptAIDraft
        goal={aiGoal}
        loading={aiLoading}
        meta={aiMeta}
        quickPrompts={aiQuickPrompts}
        onGoalChange={setAiGoal}
        onGenerate={(goal) => {
          setAiGoal(goal)
          handleGeneratePromptDraft(goal)
        }}
      />

      {/* UPDATED: Added layout-fix and column-fix classes for independent column heights */}
      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0 prompt-manager-layout layout-fix">
        <PromptList
          selectedPrompt={selectedPrompt}
          setSelectedPrompt={setSelectedPrompt}
          setIsEditing={setIsEditing}
          setShowTestPanel={setShowTestPanel}
          filteredPrompts={filteredPrompts}
          systemPrompts={systemPrompts}
          userPrompts={userPrompts}
          loading={loading}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          filterCategory={filterCategory}
          setFilterCategory={setFilterCategory}
          categories={categories}
          getCategoryColor={getCategoryColor}
          getCategoryIcon={getCategoryIcon}
          formatTemplatePreview={formatTemplatePreview}
        />
        <PromptEditor
          prompt={selectedPrompt}
          setPrompt={setSelectedPrompt}
          editing={isEditing}
          setEditing={setIsEditing}
          showTestPanel={showTestPanel}
          setShowTestPanel={setShowTestPanel}
          testInput={testInput}
          setTestInput={setTestInput}
          testOutput={testOutput}
          testing={isTesting}
          onTest={handleTestPrompt}
          onCopy={copyToClipboard}
          onDelete={handleDeletePrompt}
          onSave={handleSavePrompt}
          loading={loading}
          categories={categories}
          getCategoryColor={getCategoryColor}
        />
      </div>

      {/* Create Prompt Modal */}
      <dialog id="create-prompt-modal" className="modal">
        <div className="modal-box max-w-2xl">
          <h3 className="font-bold text-lg mb-4">Create New Prompt</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input
                type="text"
                value={newPrompt.name}
                onChange={(e) => setNewPrompt((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Enter prompt name..."
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={newPrompt.description}
                onChange={(e) => setNewPrompt((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Describe what this prompt does..."
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                rows="3"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category *</label>
              <select
                value={newPrompt.category}
                onChange={(e) => setNewPrompt((prev) => ({ ...prev, category: e.target.value }))}
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Template *</label>
              <textarea
                value={newPrompt.template}
                onChange={(e) => setNewPrompt((prev) => ({ ...prev, template: e.target.value }))}
                placeholder="Enter your prompt template..."
                className="w-full p-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                rows="8"
              />
            </div>
          </div>

          <div className="modal-action">
            <form method="dialog">
              <button className="btn btn-ghost mr-2" disabled={loading}>
                Cancel
              </button>
            </form>
            <button
              onClick={handleCreatePrompt}
              disabled={!newPrompt.name || !newPrompt.template || loading}
              className="btn btn-primary"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Creating...
                </>
              ) : (
                'Create Prompt'
              )}
            </button>
          </div>
        </div>

        <form method="dialog" className="modal-backdrop">
          <button>close</button>
        </form>
      </dialog>
    </div>
  )
}

export default PromptManager
