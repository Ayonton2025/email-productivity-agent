import React from 'react'
import { Sparkles } from 'lucide-react'

export default function WorkflowDraftPanel({
  aiQuickPrompts,
  setAiGoal,
  handleGenerateAIDraft,
  aiGoal,
  aiLoading,
  aiError,
  aiMeta,
}) {
  return (
    <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-indigo-600" />
        <p className="text-sm font-semibold text-indigo-900">AI Workflow Builder</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {aiQuickPrompts.map((prompt) => (
          <button
            key={prompt}
            onClick={() => {
              setAiGoal(prompt)
              handleGenerateAIDraft(prompt)
            }}
            className="rounded-full border border-indigo-200 bg-white px-3 py-1 text-xs text-indigo-700 hover:bg-indigo-100"
          >
            {prompt}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={aiGoal}
          onChange={(e) => setAiGoal(e.target.value)}
          placeholder="Describe the workflow you want..."
          className="flex-1 rounded-lg border border-indigo-200 px-3 py-2 text-sm"
        />
        <button
          onClick={() => handleGenerateAIDraft(aiGoal)}
          disabled={aiLoading || !aiGoal.trim()}
          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {aiLoading ? 'Generating...' : 'Generate'}
        </button>
      </div>
      {aiError && (
        <div className="text-xs text-red-600 space-y-1">
          <p>{aiError}</p>
          {String(aiError).includes('No LLM providers configured') && (
            <a href="/admin/super" className="underline">
              Configure LLM Providers
            </a>
          )}
        </div>
      )}
      {(aiMeta.provider || aiMeta.model) && (
        <p className="text-[11px] text-slate-500">
          Provider: {aiMeta.provider || 'n/a'} | Model: {aiMeta.model || 'n/a'}
        </p>
      )}
    </div>
  )
}
