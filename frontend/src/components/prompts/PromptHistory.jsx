import React from 'react'

const PromptHistory = ({ prompt }) => (
  <div className="text-sm text-gray-600" aria-label="Prompt version history">
    Current version: <span className="font-medium text-gray-900">v{prompt.version}</span>
  </div>
)

export default PromptHistory
