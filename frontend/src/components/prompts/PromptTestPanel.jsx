import React from 'react';
import { Play } from 'lucide-react';

const PromptTestPanel = ({ input, output, testing, onInputChange, onRun }) => (
  <div className="border-t border-gray-200">
    <div className="p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-2">Test Prompt</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Test Input</label>
          <textarea
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            placeholder="Enter test email content..."
            className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            rows="3"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Output</label>
          <div className="bg-gray-50 p-3 rounded-lg border border-gray-200 min-h-[100px]">
            {testing ? (
              <div className="text-gray-500">Testing prompt...</div>
            ) : (
              <pre className="font-mono text-sm whitespace-pre-wrap">
                {output || 'Run test to see output...'}
              </pre>
            )}
          </div>
        </div>
        <button
          onClick={onRun}
          disabled={!input || testing}
          className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className="h-4 w-4 mr-2" />
          Run Test
        </button>
      </div>
    </div>
  </div>
);

export default PromptTestPanel;
