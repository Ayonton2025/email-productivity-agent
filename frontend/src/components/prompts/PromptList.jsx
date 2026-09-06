import React from 'react'
import { Brain, Search, Settings } from 'lucide-react'
import PromptCard from './PromptCard'

const PromptList = ({
  filteredPrompts,
  categories,
  loading,
  selectedPrompt,
  searchTerm,
  filterCategory,
  setSearchTerm,
  setFilterCategory,
  onSelect,
  setIsEditing,
  setShowTestPanel,
  getCategoryIcon,
  getCategoryColor,
  formatTemplatePreview,
}) => {
  const systemPrompts = filteredPrompts.filter((prompt) => prompt.is_system)
  const userPrompts = filteredPrompts.filter((prompt) => !prompt.is_system)
  const renderSection = (title, sectionPrompts, system = false) => (
    <>
      {sectionPrompts.length > 0 && (
        <div className="p-3 bg-gray-50 border-b border-t">
          <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
            {system && <Settings className="h-4 w-4" />}
            {title}
          </h3>
        </div>
      )}
      {sectionPrompts.map((prompt) => (
        <PromptCard
          key={prompt.id}
          prompt={prompt}
          categories={categories}
          selected={selectedPrompt?.id === prompt.id}
          getCategoryIcon={getCategoryIcon}
          getCategoryColor={getCategoryColor}
          formatTemplatePreview={formatTemplatePreview}
          onSelect={(nextPrompt) => {
            onSelect(nextPrompt)
            setIsEditing(false)
            setShowTestPanel(false)
          }}
        />
      ))}
    </>
  )

  return (
    <div className={`${selectedPrompt ? 'lg:w-2/5' : 'w-full'} flex flex-column column-fix`}>
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <input
              type="text"
              placeholder="Search prompts..."
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <select
            value={filterCategory}
            onChange={(event) => setFilterCategory(event.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="all">All Categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto bg-white rounded-lg border border-gray-200 prompt-list-column column-fix">
        {loading ? (
          <div className="text-center py-12 text-gray-500">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4" />
            <p>Loading prompts...</p>
          </div>
        ) : filteredPrompts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Brain className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No prompts found</p>
            <p className="text-sm">Create your first prompt to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {renderSection('System Prompts', systemPrompts, true)}
            {renderSection('Your Prompts', userPrompts)}
          </div>
        )}
      </div>
    </div>
  )
}

export default PromptList
