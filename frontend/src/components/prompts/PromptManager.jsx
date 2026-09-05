import React from 'react'
import { Plus, Sparkles } from 'lucide-react'
import { usePromptManager } from '../../hooks/usePromptManager'
import PromptEditor from './PromptEditor'
import PromptForm from './PromptForm'
import PromptList from './PromptList'

const PromptManager = () => {
  const manager = usePromptManager()
  const {
    prompts,
    loading,
    selectedPrompt,
    setSelectedPrompt,
    isEditing,
    setIsEditing,
    showTestPanel,
    setShowTestPanel,
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
    handleGeneratePromptDraft,
    setNewPrompt,
    newPrompt,
    searchTerm,
    setSearchTerm,
    filterCategory,
    setFilterCategory,
    getCategoryIcon,
    getCategoryColor,
    formatTemplatePreview,
    copyToClipboard,
    testInput,
    setTestInput,
    testOutput,
    isTesting,
  } = manager

  const openCreatePromptModal = () => {
    const modal = document.getElementById('create-prompt-modal')
    if (typeof modal?.showModal === 'function') modal.showModal()
    else modal?.setAttribute('open', '')
  }

  return (
    <div className="h-full flex flex-col space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Prompt Brain</h1>
          <p className="text-sm text-slate-500">Manage and customize AI prompt templates</p>
        </div>
        <button
          onClick={openCreatePromptModal}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white font-semibold rounded-lg"
        >
          <Plus className="h-4 w-4" />
          New Prompt
        </button>
        {(aiMeta.provider || aiMeta.model) && (
          <p className="text-[11px] text-slate-500">
            Provider: {aiMeta.provider || 'n/a'} | Model: {aiMeta.model || 'n/a'}
          </p>
        )}
      </header>
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}
      <section className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-600" />
          <p className="text-sm font-semibold text-indigo-900">AI Prompt Generator</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {aiQuickPrompts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => {
                setAiGoal(prompt)
                handleGeneratePromptDraft(prompt)
              }}
              className="rounded-full border border-indigo-200 bg-white px-3 py-1 text-xs text-indigo-700"
            >
              {prompt}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={aiGoal}
            onChange={(event) => setAiGoal(event.target.value)}
            placeholder="Describe the prompt you want..."
            className="flex-1 rounded-lg border border-indigo-200 px-3 py-2 text-sm"
          />
          <button
            onClick={() => handleGeneratePromptDraft(aiGoal)}
            disabled={!aiGoal.trim() || aiLoading}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {aiLoading ? (
              'Generating...'
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Generate
              </>
            )}
          </button>
        </div>
      </section>
      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0 prompt-manager-layout layout-fix">
        <PromptList
          {...{
            prompts,
            filteredPrompts,
            categories,
            loading,
            selectedPrompt,
            searchTerm,
            filterCategory,
            setSearchTerm,
            setFilterCategory,
            setSelectedPrompt,
            setIsEditing,
            setShowTestPanel,
            getCategoryIcon,
            getCategoryColor,
            formatTemplatePreview,
          }}
        />
        {selectedPrompt && (
          <PromptEditor
            prompt={selectedPrompt}
            categories={categories}
            loading={loading}
            isEditing={isEditing}
            setIsEditing={setIsEditing}
            showTestPanel={showTestPanel}
            setShowTestPanel={setShowTestPanel}
            setSelectedPrompt={setSelectedPrompt}
            getCategoryColor={getCategoryColor}
            copyToClipboard={copyToClipboard}
            onDelete={handleDeletePrompt}
            onSave={handleSavePrompt}
            testProps={{ testInput, setTestInput, testOutput, isTesting, onTest: handleTestPrompt }}
          />
        )}
      </div>
      <PromptForm {...{ newPrompt, setNewPrompt, categories, loading, onCreate: handleCreatePrompt }} />
    </div>
  )
}

export default PromptManager
