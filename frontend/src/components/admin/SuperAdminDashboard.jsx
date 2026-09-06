import AdminOverviewPanel from './AdminOverviewPanel'
import ProviderList from './ProviderList'

import React from 'react'

import { useSuperAdminDashboard } from './useSuperAdminDashboard'
const SuperAdminDashboard = ({ view = 'dashboard' }) => {
  const {
    overview,
    transactions,
    currencyReport,
    llmProviders,
    setLlmProviders,
    llmLoading,
    llmCheckResult,
    setLlmCheckResult,
    providerChecks,
    setProviderChecks,
    saveState,
    newKeys,
    setNewKeys,
    confirmDelete,
    setConfirmDelete,
    loading,
    error,
    autoRefreshEnabled,
    setAutoRefreshEnabled,
    lastRefreshTime,
    loadProviders,
    patchProvider,
    rotateKey,
    confirmDeleteKey,
    runHealthCheck,
    runSingleProviderHealthCheck,
    runSingleProviderTest,
    txSummary,
  } = useSuperAdminDashboard({ view })
  if (loading && view === 'dashboard') return <div className="p-6 text-slate-600">Loading dashboard...</div>
  if (loading && view === 'llm') return <div className="p-6 text-slate-600">Loading LLM settings...</div>
  if (error) return <div className="p-6 text-red-600">{error}</div>

  // Dashboard View
  if (view === 'dashboard' || view === 'super-admin') {
    return (
      <AdminOverviewPanel
        overview={overview}
        currencyReport={currencyReport}
        txSummary={txSummary}
        transactions={transactions}
        runHealthCheck={runHealthCheck}
        llmLoading={llmLoading}
      />
    )
  }

  // LLM Settings View
  if (view === 'llm') {
    return (
      <div className="p-6 space-y-6 overflow-x-hidden">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">LLM Provider Settings</h1>
          <p className="text-slate-600 text-sm">Manage AI provider configurations, keys, and health checks.</p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-4 overflow-hidden">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">LLM Providers</h2>
              <p className="text-xs text-slate-500">
                Keys are encrypted in database and shown masked only. Green circle = Healthy, Red = Issue.
                Auto-refreshes every 30 seconds.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-xs flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoRefreshEnabled}
                  onChange={(e) => {
                    setAutoRefreshEnabled(e.target.checked)
                    if (e.target.checked) loadProviders()
                  }}
                  className="w-4 h-4"
                />
                <span>{autoRefreshEnabled ? '🔄 Auto-refresh enabled' : 'Auto-refresh disabled'}</span>
              </label>
              {lastRefreshTime && (
                <div className="text-xs text-slate-500">Last: {lastRefreshTime.toLocaleTimeString()}</div>
              )}
            </div>
          </div>
          {llmCheckResult && (
            <div className="mt-3 text-xs text-slate-700">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold">Last Health Check Result</h3>
                <button
                  onClick={() => setLlmCheckResult(null)}
                  className="rounded bg-slate-400 hover:bg-slate-500 px-2 py-1 text-xs font-medium text-white"
                >
                  Clear
                </button>
              </div>
              <div className="overflow-x-auto">
                <pre className="whitespace-pre-wrap break-words text-[12px] bg-slate-50 border border-slate-100 p-2 rounded">
                  {JSON.stringify(llmCheckResult, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {llmProviders.length === 0 && <p className="text-sm text-slate-500">No provider configuration rows yet.</p>}

          <ProviderList
            llmProviders={llmProviders}
            patchProvider={patchProvider}
            setLlmProviders={setLlmProviders}
            setConfirmDelete={setConfirmDelete}
            newKeys={newKeys}
            setNewKeys={setNewKeys}
            rotateKey={rotateKey}
            runSingleProviderHealthCheck={runSingleProviderHealthCheck}
            providerChecks={providerChecks}
            runSingleProviderTest={runSingleProviderTest}
            saveState={saveState}
            setProviderChecks={setProviderChecks}
          />
        </div>

        {confirmDelete.provider && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4 space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Delete API Key</h3>
                <p className="text-sm text-slate-600 mt-2">Are you sure you want to delete this key?</p>
                <p className="text-xs font-mono text-slate-500 mt-2 break-all">{confirmDelete.maskedKey}</p>
              </div>

              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setConfirmDelete({ provider: null, keyIndex: null, maskedKey: null })}
                  className="rounded bg-slate-300 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-400"
                >
                  Cancel
                </button>
                <button
                  onClick={() => confirmDeleteKey(confirmDelete.provider, confirmDelete.keyIndex)}
                  disabled={saveState[confirmDelete.provider] === 'deleting'}
                  className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saveState[confirmDelete.provider] === 'deleting' ? 'Deleting...' : 'Delete Key'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }
}
export default SuperAdminDashboard
