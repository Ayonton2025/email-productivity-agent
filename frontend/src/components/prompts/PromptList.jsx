import React from 'react'
import { Brain, CheckCircle, Search, Settings } from 'lucide-react'

const PromptList = ({
  selectedPrompt,
  setSelectedPrompt,
  setIsEditing,
  setShowTestPanel,
  filteredPrompts,
  systemPrompts,
  userPrompts,
  loading,
  searchTerm,
  setSearchTerm,
  filterCategory,
  setFilterCategory,
  categories,
  getCategoryColor,
  getCategoryIcon,
  formatTemplatePreview,
}) => (
  <div className={`${selectedPrompt ? 'lg:w-2/5' : 'w-full'} flex flex-column column-fix`}>
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
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4"></div>
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
          {/* System Prompts Section */}
          {systemPrompts.length > 0 && (
            <div className="p-3 bg-gray-50 border-b">
              <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Settings className="h-4 w-4" />
                System Prompts
              </h3>
            </div>
          )}
          {systemPrompts.map((prompt) => {
            const CategoryIcon = getCategoryIcon(prompt.category)
            return (
              <div
                key={prompt.id}
                onClick={() => {
                  setSelectedPrompt(prompt)
                  setIsEditing(false)
                  setShowTestPanel(false)
                }}
                className={`p-4 cursor-pointer transition-colors ${
                  selectedPrompt?.id === prompt.id ? 'bg-indigo-50 border-l-4 border-indigo-500' : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <CategoryIcon className={`h-4 w-4 ${getCategoryColor(prompt.category).split(' ')[1]}`} />
                    <h3 className="font-semibold text-gray-900">{prompt.name}</h3>
                  </div>
                  <div className="flex items-center gap-1">
                    {prompt.is_active && <CheckCircle className="h-4 w-4 text-green-500" />}
                    <span className="inline-flex items-center px-2 py-1 rounded-full bg-orange-100 text-orange-800 text-xs">
                      System
                    </span>
                  </div>
                </div>

                <p className="text-sm text-gray-600 mb-2 line-clamp-2">{prompt.description || 'No description'}</p>

                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-full ${getCategoryColor(prompt.category)}`}
                  >
                    {categories.find((c) => c.id === prompt.category)?.name || prompt.category}
                  </span>
                  <span>v{prompt.version}</span>
                </div>

                <div className="mt-2 text-xs text-gray-400 font-mono">{formatTemplatePreview(prompt.template)}</div>
              </div>
            )
          })}

          {/* User Prompts Section */}
          {userPrompts.length > 0 && (
            <div className="p-3 bg-gray-50 border-b border-t">
              <h3 className="text-sm font-medium text-gray-700">Your Prompts</h3>
            </div>
          )}
          {userPrompts.map((prompt) => {
            const CategoryIcon = getCategoryIcon(prompt.category)
            return (
              <div
                key={prompt.id}
                onClick={() => {
                  setSelectedPrompt(prompt)
                  setIsEditing(false)
                  setShowTestPanel(false)
                }}
                className={`p-4 cursor-pointer transition-colors ${
                  selectedPrompt?.id === prompt.id ? 'bg-indigo-50 border-l-4 border-indigo-500' : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <CategoryIcon className={`h-4 w-4 ${getCategoryColor(prompt.category).split(' ')[1]}`} />
                    <h3 className="font-semibold text-gray-900">{prompt.name}</h3>
                  </div>
                  <div className="flex items-center gap-1">
                    {prompt.is_active && <CheckCircle className="h-4 w-4 text-green-500" />}
                  </div>
                </div>

                <p className="text-sm text-gray-600 mb-2 line-clamp-2">{prompt.description || 'No description'}</p>

                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-full ${getCategoryColor(prompt.category)}`}
                  >
                    {categories.find((c) => c.id === prompt.category)?.name || prompt.category}
                  </span>
                  <span>v{prompt.version}</span>
                </div>

                <div className="mt-2 text-xs text-gray-400 font-mono">{formatTemplatePreview(prompt.template)}</div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  </div>
)

export default PromptList
