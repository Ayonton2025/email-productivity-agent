import ProviderKeyControls from './ProviderKeyControls'

import React from 'react'

export default function ProviderList({
  llmProviders,
  patchProvider,
  setLlmProviders,
  setConfirmDelete,
  newKeys,
  setNewKeys,
  rotateKey,
  runSingleProviderHealthCheck,
  providerChecks,
  runSingleProviderTest,
  saveState,
  setProviderChecks,
}) {
  return (
    <div className="space-y-3">
      {llmProviders.map((p) => (
        <div key={p.provider} className="rounded-lg border border-slate-200 p-3 space-y-3 min-w-0">
          {p.decryption_failures > 0 && (
            <div className="text-sm text-red-700 bg-amber-50 border border-amber-100 p-2 rounded">
              <strong>Decryption issues:</strong> {p.decryption_failures} key(s) failed to decrypt. Update the server
              `ENCRYPTION_KEY` or re-add keys.
            </div>
          )}
          <div className="flex flex-wrap items-center gap-3">
            {/* Live Status Circle */}
            <div className="flex items-center gap-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  p.is_healthy
                    ? 'bg-emerald-500 animate-pulse'
                    : p.last_error
                      ? 'bg-red-500 animate-pulse'
                      : 'bg-slate-300'
                }`}
                title={p.last_error || 'Status indicator'}
              />
              <span className="font-semibold text-slate-900">{p.display_name}</span>
            </div>
            <span className="text-xs rounded px-2 py-1 bg-indigo-100 text-indigo-800 font-medium">{p.provider}</span>
            <span
              className={`text-xs rounded px-3 py-1 font-semibold ${
                p.is_healthy
                  ? 'bg-emerald-100 text-emerald-900'
                  : p.last_error
                    ? 'bg-orange-100 text-orange-900'
                    : 'bg-slate-200 text-slate-900'
              }`}
            >
              {p.is_healthy ? '✓ Healthy' : p.last_error ? '⚠ Issue detected' : '○ Not checked'}
            </span>
            {p.last_error && (
              <span className="text-xs font-medium text-red-700 bg-red-50 px-2 py-1 rounded break-all">
                Reason: {p.last_error}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-2 min-w-0">
            <label className="text-xs text-slate-600 flex items-center gap-2">
              <input
                type="checkbox"
                checked={!!p.is_enabled}
                onChange={(e) => patchProvider(p.provider, { is_enabled: e.target.checked })}
              />
              Enabled
            </label>
            <input
              value={p.model || ''}
              onChange={(e) =>
                setLlmProviders((prev) =>
                  prev.map((x) => (x.provider === p.provider ? { ...x, model: e.target.value } : x))
                )
              }
              onBlur={(e) => patchProvider(p.provider, { model: e.target.value })}
              placeholder="Model"
              className="w-full min-w-0 rounded border border-slate-300 px-2 py-1 text-xs text-slate-900"
            />
            <input
              value={p.endpoint || ''}
              onChange={(e) =>
                setLlmProviders((prev) =>
                  prev.map((x) => (x.provider === p.provider ? { ...x, endpoint: e.target.value } : x))
                )
              }
              onBlur={(e) => patchProvider(p.provider, { endpoint: e.target.value })}
              placeholder="Endpoint"
              className="w-full min-w-0 rounded border border-slate-300 px-2 py-1 text-xs text-slate-900"
            />
            <input
              type="number"
              value={p.priority ?? 100}
              onChange={(e) =>
                setLlmProviders((prev) =>
                  prev.map((x) => (x.provider === p.provider ? { ...x, priority: Number(e.target.value || 100) } : x))
                )
              }
              onBlur={(e) => patchProvider(p.provider, { priority: Number(e.target.value || 100) })}
              placeholder="Priority"
              className="w-full min-w-0 rounded border border-slate-300 px-2 py-1 text-xs text-slate-900"
            />
            <div className="text-xs text-slate-700 flex items-center break-all min-w-0">Keys: {p.key_count}</div>
          </div>

          {p.key_count > 0 && (
            <div className="border border-slate-200 rounded overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="text-left px-3 py-2 font-semibold text-slate-700">Masked Key</th>
                    <th className="text-right px-3 py-2 font-semibold text-slate-700">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(p.masked_keys || []).map((maskedKey, idx) => (
                    <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2 text-slate-600 font-mono break-all">{maskedKey}</td>
                      <td className="px-3 py-2 text-right">
                        <button
                          onClick={() => setConfirmDelete({ provider: p.provider, keyIndex: idx, maskedKey })}
                          className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <ProviderKeyControls
            newKeys={newKeys}
            p={p}
            setNewKeys={setNewKeys}
            rotateKey={rotateKey}
            runSingleProviderHealthCheck={runSingleProviderHealthCheck}
            providerChecks={providerChecks}
            runSingleProviderTest={runSingleProviderTest}
            saveState={saveState}
          />

          {providerChecks[p.provider]?.result && (
            <div className="text-xs text-slate-700 bg-slate-50 border border-slate-200 rounded p-2 overflow-x-auto">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold">Result:</span>
                <button
                  onClick={() =>
                    setProviderChecks((prev) => ({
                      ...prev,
                      [p.provider]: { ...prev[p.provider], result: null },
                    }))
                  }
                  className="rounded bg-slate-400 hover:bg-slate-500 px-2 py-1 text-xs font-medium text-white"
                >
                  Clear
                </button>
              </div>
              <pre className="whitespace-pre-wrap break-words text-[12px]">
                {JSON.stringify(providerChecks[p.provider].result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
