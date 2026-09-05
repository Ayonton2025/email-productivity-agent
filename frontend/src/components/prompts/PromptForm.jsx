import React from 'react'

const PromptForm = ({ newPrompt, setNewPrompt, categories, loading, onCreate }) => (
  <dialog id="create-prompt-modal" className="modal">
    <div className="modal-box max-w-2xl">
      <h3 className="font-bold text-lg mb-4">Create New Prompt</h3>
      <div className="space-y-4">
        <label className="block text-sm font-medium text-gray-700">
          Name *
          <input
            type="text"
            value={newPrompt.name}
            onChange={(event) => setNewPrompt((previous) => ({ ...previous, name: event.target.value }))}
            placeholder="Enter prompt name..."
            className="w-full p-2 mt-1 border border-gray-300 rounded-lg"
          />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Description
          <textarea
            value={newPrompt.description}
            onChange={(event) => setNewPrompt((previous) => ({ ...previous, description: event.target.value }))}
            placeholder="Describe what this prompt does..."
            className="w-full p-2 mt-1 border border-gray-300 rounded-lg"
            rows="3"
          />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Category *
          <select
            value={newPrompt.category}
            onChange={(event) => setNewPrompt((previous) => ({ ...previous, category: event.target.value }))}
            className="w-full p-2 mt-1 border border-gray-300 rounded-lg"
          >
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Template *
          <textarea
            value={newPrompt.template}
            onChange={(event) => setNewPrompt((previous) => ({ ...previous, template: event.target.value }))}
            placeholder="Enter your prompt template..."
            className="w-full p-2 mt-1 border border-gray-300 rounded-lg font-mono text-sm"
            rows="8"
          />
        </label>
      </div>
      <div className="modal-action">
        <form method="dialog">
          <button className="btn btn-ghost mr-2" disabled={loading}>
            Cancel
          </button>
        </form>
        <button
          onClick={onCreate}
          disabled={!newPrompt.name || !newPrompt.template || loading}
          className="btn btn-primary"
        >
          {loading ? 'Creating...' : 'Create Prompt'}
        </button>
      </div>
    </div>
    <form method="dialog" className="modal-backdrop">
      <button>close</button>
    </form>
  </dialog>
)

export default PromptForm
