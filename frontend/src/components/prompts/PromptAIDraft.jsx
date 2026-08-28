import React from 'react';
import { Sparkles } from 'lucide-react';

const PromptAIDraft = ({ goal, loading, meta, quickPrompts, onGoalChange, onGenerate }) => (
  <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 space-y-3">
    <div className="flex items-center gap-2">
      <Sparkles className="h-4 w-4 text-indigo-600" />
      <p className="text-sm font-semibold text-indigo-900">AI Prompt Generator</p>
    </div>
    {meta && (
      <p className="text-[11px] text-slate-500">
        Provider: {meta.provider || 'n/a'} | Model: {meta.model || 'n/a'}
      </p>
    )}
    <div className="flex flex-wrap gap-2">
      {quickPrompts.map((prompt) => (
        <button
          key={prompt}
          onClick={() => onGenerate(prompt)}
          className="rounded-full border border-indigo-200 bg-white px-3 py-1 text-xs text-indigo-700 hover:bg-indigo-100"
        >
          {prompt}
        </button>
      ))}
    </div>
    <div className="flex gap-2">
      <input
        type="text"
        value={goal}
        onChange={(event) => onGoalChange(event.target.value)}
        placeholder="Describe the prompt you want..."
        className="flex-1 rounded-lg border border-indigo-200 px-3 py-2 text-sm text-slate-900 placeholder-slate-500"
      />
      <button
        onClick={() => onGenerate(goal)}
        disabled={!goal.trim() || loading}
        className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
      >
        {loading ? (
          'Generating...'
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Generate
          </>
        )}
      </button>
    </div>
  </div>
);

export default PromptAIDraft;
