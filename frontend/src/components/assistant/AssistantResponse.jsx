import React from 'react'

export default function AssistantResponse({ response, confirmExecute, confirming, setResponse, setPendingExecution }) {
  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-sm font-medium text-slate-900">{response.assistant_message || 'Done.'}</p>
      <p className="text-[11px] text-slate-500">
        Provider: {response.provider || 'n/a'} | Model: {response.model || 'n/a'}
      </p>
      {Array.isArray(response.suggested_actions) && response.suggested_actions.length > 0 && (
        <ul className="list-disc space-y-1 pl-4 text-xs text-slate-600">
          {response.suggested_actions.slice(0, 4).map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
      )}
      {response.execution?.created && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-2 text-xs text-emerald-800">
          <p className="font-semibold">Executed successfully</p>
          <pre className="mt-1 whitespace-pre-wrap">{JSON.stringify(response.execution.created, null, 2)}</pre>
        </div>
      )}
      {response.requires_confirmation && (
        <div className="space-y-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-2 text-xs text-amber-900">
          <p className="font-semibold">Approval Required</p>
          <p>Review preview below and confirm to apply DB changes.</p>
          <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-[11px] text-slate-700">
            {JSON.stringify(response.draft || {}, null, 2)}
          </pre>
          <div className="flex gap-2">
            <button
              onClick={confirmExecute}
              disabled={confirming}
              className="rounded bg-emerald-600 px-2 py-1 text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {confirming ? 'Confirming...' : 'Confirm Execute'}
            </button>
            <button
              onClick={() => {
                setResponse(null)
                setPendingExecution(null)
              }}
              className="rounded bg-slate-200 px-2 py-1 text-slate-700 hover:bg-slate-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
