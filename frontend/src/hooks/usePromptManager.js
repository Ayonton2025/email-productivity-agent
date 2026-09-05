import { useContext, useEffect, useState } from 'react'
import { logger } from '../utils/logger.js'
import { Brain, FileText, Filter, MessageSquare, Settings, Zap } from 'lucide-react'
import { PromptContext } from '../context/PromptContext'
import { aiApi } from '../services/api'

const initialPrompt = {
  name: '',
  description: '',
  template: '',
  category: 'categorization',
  is_active: true,
}

export function usePromptManager() {
  const { prompts, createPrompt, updatePrompt, deletePrompt, testPrompt, loading } = useContext(PromptContext)
  const [selectedPrompt, setSelectedPrompt] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCategory, setFilterCategory] = useState('all')
  const [newPrompt, setNewPrompt] = useState(initialPrompt)
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
    if (prompts.length > 0 && !selectedPrompt) setSelectedPrompt(prompts[0])
  }, [prompts, selectedPrompt])

  const filteredPrompts = prompts.filter((prompt) => {
    const query = searchTerm.toLowerCase()
    const matchesSearch =
      prompt.name.toLowerCase().includes(query) ||
      prompt.description?.toLowerCase().includes(query) ||
      prompt.template.toLowerCase().includes(query)
    return matchesSearch && (filterCategory === 'all' || prompt.category === filterCategory)
  })

  const handleCreatePrompt = async () => {
    if (!newPrompt.name || !newPrompt.template) {
      alert('Please fill in all required fields')
      return
    }
    setError('')
    try {
      await createPrompt(newPrompt)
      setNewPrompt({ ...initialPrompt })
      document.getElementById('create-prompt-modal').close()
    } catch (createError) {
      logger.error('Failed to create prompt:', createError)
      setError('Failed to create prompt: ' + (createError.message || 'Unknown error'))
    }
  }

  const handleSavePrompt = async () => {
    if (!selectedPrompt) return
    setError('')
    try {
      await updatePrompt(selectedPrompt.id, selectedPrompt)
      setIsEditing(false)
    } catch (saveError) {
      logger.error('Failed to update prompt:', saveError)
      setError('Failed to update prompt: ' + (saveError.message || 'Unknown error'))
    }
  }

  const handleDeletePrompt = async (promptId) => {
    if (!confirm('Are you sure you want to delete this prompt?')) return
    setError('')
    try {
      await deletePrompt(promptId)
      if (selectedPrompt?.id === promptId)
        setSelectedPrompt(filteredPrompts.find((prompt) => prompt.id !== promptId) || null)
    } catch (deleteError) {
      logger.error('Failed to delete prompt:', deleteError)
      setError('Failed to delete prompt: ' + (deleteError.message || 'Unknown error'))
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
    } catch (testError) {
      logger.error('Failed to test prompt:', testError)
      setError('Failed to test prompt: ' + (testError.message || 'Unknown error'))
      setTestOutput('Error: ' + (testError.message || 'Failed to test prompt'))
    } finally {
      setIsTesting(false)
    }
  }

  const getCategoryIcon = (categoryId) => categories.find((category) => category.id === categoryId)?.icon || Settings
  const getCategoryColor = (categoryId) =>
    categories.find((category) => category.id === categoryId)?.color || 'bg-gray-100 text-gray-800'
  const formatTemplatePreview = (template) =>
    !template ? 'No template defined' : template.length > 100 ? `${template.substring(0, 100)}...` : template
  const copyToClipboard = (text) =>
    navigator.clipboard.writeText(text).then(() => alert('Prompt template copied to clipboard!'))

  const handleGeneratePromptDraft = async (goal) => {
    if (!goal?.trim()) return
    setAiLoading(true)
    setError('')
    try {
      const response = await aiApi.assistWorkspace({
        page: 'prompts',
        objective: goal.trim(),
        mode: 'draft',
        context: { existing_prompt_count: prompts.length },
      })
      const draft = response.data?.draft?.prompt || {}
      setAiMeta({ provider: response.data?.provider, model: response.data?.model })
      if (Object.keys(draft).length > 0) {
        setNewPrompt((previous) => ({ ...previous, ...draft }))
        document.getElementById('create-prompt-modal').showModal()
      }
    } catch (aiError) {
      setError(
        aiError?.response?.data?.detail ||
          aiError?.response?.data?.error ||
          aiError?.message ||
          'Failed to generate prompt draft'
      )
    } finally {
      setAiLoading(false)
    }
  }

  return {
    prompts,
    loading,
    selectedPrompt,
    setSelectedPrompt,
    isEditing,
    setIsEditing,
    searchTerm,
    setSearchTerm,
    filterCategory,
    setFilterCategory,
    newPrompt,
    setNewPrompt,
    showTestPanel,
    setShowTestPanel,
    testInput,
    setTestInput,
    testOutput,
    isTesting,
    error,
    aiGoal,
    setAiGoal,
    aiLoading,
    aiMeta,
    categories,
    aiQuickPrompts,
    filteredPrompts,
    handleCreatePrompt,
    handleSavePrompt,
    handleDeletePrompt,
    handleTestPrompt,
    getCategoryIcon,
    getCategoryColor,
    formatTemplatePreview,
    copyToClipboard,
    handleGeneratePromptDraft,
  }
}
