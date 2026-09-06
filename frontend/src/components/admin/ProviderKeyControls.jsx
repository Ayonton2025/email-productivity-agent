import React from 'react'
export default function ProviderKeyControls({
  newKeys,
  p,
  setNewKeys,
  rotateKey,
  runSingleProviderHealthCheck,
  providerChecks,
  runSingleProviderTest,
  saveState,
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        type="password"
        value={newKeys[p.provider] || ''}
        onChange={(e) => setNewKeys((prev) => ({ ...prev, [p.provider]: e.target.value }))}
        placeholder="Paste new API key (hidden)"
        className="flex-1 min-w-[220px] max-w-full rounded border border-slate-300 px-2 py-1 text-xs text-slate-900"
      />
      <button
        onClick={() => rotateKey(p.provider)}
        className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700"
      >
        Add/Rotate Key
      </button>
      <button
        onClick={() => runSingleProviderHealthCheck(p.provider)}
        disabled={providerChecks[p.provider]?.status === 'checking'}
        className="rounded bg-slate-900 px-3 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {providerChecks[p.provider]?.status === 'checking' && providerChecks[p.provider]?.type === 'health'
          ? 'Checking...'
          : 'Check'}
      </button>
      <button
        onClick={() => runSingleProviderTest(p.provider)}
        disabled={providerChecks[p.provider]?.status === 'checking'}
        className="rounded bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
      >
        {providerChecks[p.provider]?.status === 'checking' && providerChecks[p.provider]?.type === 'test'
          ? 'Testing...'
          : 'Test'}
      </button>
      <span className="text-xs text-slate-500">
        {saveState[p.provider] === 'saving'
          ? 'Saving...'
          : saveState[p.provider] === 'saved'
            ? 'Saved'
            : saveState[p.provider] === 'deleting'
              ? 'Deleting...'
              : saveState[p.provider] === 'deleted'
                ? 'Deleted'
                : saveState[p.provider] || ''}
      </span>
    </div>
  )
}
