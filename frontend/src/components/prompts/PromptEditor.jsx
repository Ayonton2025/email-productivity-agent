import React from 'react'
import { Copy, Edit, Save, Settings, TestTube, Trash2 } from 'lucide-react'

import PromptHistory from './PromptHistory'
import PromptTestPanel from './PromptTestPanel'

const PromptEditor = ({
  prompt,
  setPrompt,
  editing,
  setEditing,
  showTestPanel,
  setShowTestPanel,
  testInput,
  setTestInput,
  testOutput,
  testing,
  onTest,
  onCopy,
  onDelete,
  onSave,
  loading,
  categories,
  getCategoryColor,
}) => {
  if (!prompt) return null
  const selectedPrompt = prompt
  const setSelectedPrompt = setPrompt
  const isEditing = editing
  const setIsEditing = setEditing
  const handleTestPrompt = onTest
  const copyToClipboard = onCopy
  const handleDeletePrompt = onDelete
  const handleSavePrompt = onSave
  const isTesting = testing

  return (
    <div className="lg:w-3/5 flex flex-column column-fix">
      <div className="bg-white rounded-lg border border-gray-200 flex-1 flex flex-column prompt-editor-column column-fix">
        {/* Editor Header */}
        <div className="border-b border-gray-200 p-4">
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              {isEditing ? (
                <input
                  type="text"
                  value={selectedPrompt.name}
                  onChange={(e) => setSelectedPrompt((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full text-lg font-semibold border-b border-gray-300 focus:border-indigo-500 focus:outline-none pb-1"
                />
              ) : (
                <h2 className="text-lg font-semibold text-gray-900">{selectedPrompt.name}</h2>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowTestPanel(!showTestPanel)}
                className={`inline-flex items-center px-3 py-1 rounded-lg text-sm ${
                  showTestPanel ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
                  aria-label="Delete prompt"
                  disabled={loading}
                  className="p-2 text-red-500 hover:text-red-700 rounded-lg hover:bg-red-50 disabled:opacity-50"
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
                  onChange={(e) => setSelectedPrompt((prev) => ({ ...prev, category: e.target.value }))}
                  className="border border-gray-300 rounded px-2 py-1"
                >
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
              ) : (
                <span
                  className={`inline-flex items-center px-2 py-1 rounded-full ${getCategoryColor(selectedPrompt.category)}`}
                >
                  {categories.find((c) => c.id === selectedPrompt.category)?.name || selectedPrompt.category}
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
                    onChange={(e) => setSelectedPrompt((prev) => ({ ...prev, is_active: e.target.checked }))}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Active</span>
                </label>
              ) : (
                <span
                  className={`inline-flex items-center ${selectedPrompt.is_active ? 'text-green-600' : 'text-gray-400'}`}
                >
                  {selectedPrompt.is_active ? 'Active' : 'Inactive'}
                </span>
              )}
            </div>

            <PromptHistory prompt={selectedPrompt} />
          </div>
        </div>

        {/* Editor Content */}
        <div className="flex-1 flex flex-column min-h-0">
          {isEditing ? (
            <div className="flex-1 flex flex-column">
              <div className="p-4 border-b border-gray-200">
                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <textarea
                  value={selectedPrompt.description}
                  onChange={(e) => setSelectedPrompt((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Describe what this prompt does..."
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  rows="3"
                />
              </div>

              <div className="flex-1 p-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Prompt Template</label>
                <textarea
                  value={selectedPrompt.template}
                  onChange={(e) => setSelectedPrompt((prev) => ({ ...prev, template: e.target.value }))}
                  placeholder="Enter your prompt template here..."
                  className="w-full h-full p-3 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                />
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-column">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
                <p className="text-gray-900">{selectedPrompt.description || 'No description provided.'}</p>
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

        {showTestPanel && (
          <PromptTestPanel
            input={testInput}
            output={testOutput}
            testing={isTesting}
            onInputChange={setTestInput}
            onRun={handleTestPrompt}
          />
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
                    disabled={loading}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSavePrompt}
                    disabled={loading}
                    className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4 mr-2" />
                        Save Prompt
                      </>
                    )}
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
  )
}

export default PromptEditor
