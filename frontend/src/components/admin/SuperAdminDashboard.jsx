import React, { useEffect, useMemo, useState } from 'react';
import {
  getAdminOverview,
  getAdminTransactions,
  getRevenueByCurrency,
  getLLMProviders,
  updateLLMProvider,
  rotateLLMProviderKey,
  deleteLLMProviderKey,
  runLLMHealthCheck,
  runLLMProviderHealthCheck,
  runLLMSingleProviderTest,
  resetPremiumDismissals
} from '../../services/adminService';

const Stat = ({ label, value }) => (
  <div className="rounded-lg border border-slate-200 bg-white p-4">
    <div className="text-xs text-slate-500">{label}</div>
    <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
  </div>
);

const SuperAdminDashboard = ({ view = 'dashboard' }) => {
  const [overview, setOverview] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [currencyReport, setCurrencyReport] = useState([]);
  const [llmProviders, setLlmProviders] = useState([]);
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmCheckResult, setLlmCheckResult] = useState(null);
  const [providerChecks, setProviderChecks] = useState({});
  const [saveState, setSaveState] = useState({});
  const [newKeys, setNewKeys] = useState({});
  const [confirmDelete, setConfirmDelete] = useState({ provider: null, keyIndex: null, maskedKey: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [lastRefreshTime, setLastRefreshTime] = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [o, t, r] = await Promise.all([
          getAdminOverview(),
          getAdminTransactions(200),
          getRevenueByCurrency(),
        ]);
        setOverview(o?.metrics || null);
        setTransactions(t?.transactions || []);
        setCurrencyReport(r?.report || []);
      } catch (e) {
        setError(e?.response?.data?.detail || e.message || 'Failed to load admin dashboard');
      } finally {
        setLoading(false);
      }
    };
    load();
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLlmLoading(true);
      const res = await getLLMProviders();
      setLlmProviders(res?.providers || []);
      setLastRefreshTime(new Date());
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to load LLM providers');
    } finally {
      setLlmLoading(false);
    }
  };

  // Auto-refresh providers every 30 seconds to show updated health status
  useEffect(() => {
    if (!autoRefreshEnabled || view !== 'llm') return;
    
    const refreshInterval = setInterval(() => {
      loadProviders();
    }, 30000); // Refresh every 30 seconds
    
    return () => clearInterval(refreshInterval);
  }, [autoRefreshEnabled, view]);

  const patchProvider = async (provider, patch) => {
    setSaveState(prev => ({ ...prev, [provider]: 'saving' }));
    try {
      await updateLLMProvider(provider, patch);
      await loadProviders();
      setSaveState(prev => ({ ...prev, [provider]: 'saved' }));
    } catch (e) {
      setSaveState(prev => ({ ...prev, [provider]: e?.response?.data?.detail || e.message || 'Failed' }));
    }
  };

  const rotateKey = async (provider) => {
    const key = (newKeys[provider] || '').trim();
    if (!key) return;
    setSaveState(prev => ({ ...prev, [provider]: 'saving' }));
    try {
      await rotateLLMProviderKey(provider, key);
      setNewKeys(prev => ({ ...prev, [provider]: '' }));
      await loadProviders();
      setSaveState(prev => ({ ...prev, [provider]: 'saved' }));
    } catch (e) {
      setSaveState(prev => ({ ...prev, [provider]: e?.response?.data?.detail || e.message || 'Failed' }));
    }
  };

  const confirmDeleteKey = async (provider, keyIndex) => {
    setSaveState(prev => ({ ...prev, [provider]: 'deleting' }));
    try {
      await deleteLLMProviderKey(provider, keyIndex);
      setConfirmDelete({ provider: null, keyIndex: null, maskedKey: null });
      await loadProviders();
      setSaveState(prev => ({ ...prev, [provider]: 'deleted' }));
      setTimeout(() => setSaveState(prev => ({ ...prev, [provider]: '' })), 2000);
    } catch (e) {
      setSaveState(prev => ({ ...prev, [provider]: e?.response?.data?.detail || e.message || 'Failed to delete' }));
    }
  };

  const runHealthCheck = async () => {
    setLlmLoading(true);
    try {
      const res = await runLLMHealthCheck();
      // res may include health and providers
      setLlmCheckResult(res?.health || res || { message: 'No details returned' });
      await loadProviders();
    } catch (e) {
      const msg = e?.response?.data || e.message || 'Failed to run provider health check';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      setLlmCheckResult({ error: msg });
    } finally {
      setLlmLoading(false);
    }
  };

  const runSingleProviderHealthCheck = async (provider) => {
    setProviderChecks(prev => ({ ...prev, [provider]: { status: 'checking', type: 'health' } }));
    try {
      const res = await runLLMProviderHealthCheck(provider);
      const providerResult = res?.provider_health || null;
      setProviderChecks(prev => ({
        ...prev,
        [provider]: {
          status: 'done',
          type: 'health',
          result: providerResult || { message: res?.health?.message || 'No provider result returned' },
        },
      }));
      await loadProviders();
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || 'Failed to run provider health check';
      setProviderChecks(prev => ({
        ...prev,
        [provider]: { status: 'error', type: 'health', result: { error: msg } },
      }));
    }
  };

  const runSingleProviderTest = async (provider) => {
    setProviderChecks(prev => ({ ...prev, [provider]: { status: 'checking', type: 'test' } }));
    try {
      const res = await runLLMSingleProviderTest(provider);
      const providerResult = res?.provider_result || null;
      setProviderChecks(prev => ({
        ...prev,
        [provider]: {
          status: 'done',
          type: 'test',
          result: providerResult || { message: res?.test_results?.message || 'No provider test result returned' },
        },
      }));
      await loadProviders();
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || 'Failed to run provider test';
      setProviderChecks(prev => ({
        ...prev,
        [provider]: { status: 'error', type: 'test', result: { error: msg } },
      }));
    }
  };

  const txSummary = useMemo(() => {
    const byMethod = {};
    for (const tx of transactions) {
      const key = tx.payment_method || 'unknown';
      byMethod[key] = (byMethod[key] || 0) + 1;
    }
    return Object.entries(byMethod).sort((a, b) => b[1] - a[1]);
  }, [transactions]);

  if (loading && view === 'dashboard') return <div className="p-6 text-slate-600">Loading dashboard...</div>;
  if (loading && view === 'llm') return <div className="p-6 text-slate-600">Loading LLM settings...</div>;
  if (error) return <div className="p-6 text-red-600">{error}</div>;

  // Dashboard View
  if (view === 'dashboard' || view === 'super-admin') {
    return (
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin Dashboard</h1>
          <p className="text-slate-600 text-sm">System-wide operations, billing analytics, and payment monitoring.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <Stat label="Total Users" value={overview?.total_users ?? 0} />
          <Stat label="Total Payments" value={overview?.total_payments ?? 0} />
          <Stat label="Completed" value={overview?.completed_payments ?? 0} />
          <Stat label="Pending" value={overview?.pending_payments ?? 0} />
          <Stat label="Failed" value={overview?.failed_payments ?? 0} />
          <Stat label="Revenue (USD)" value={`$${(overview?.revenue_usd ?? 0).toFixed(2)}`} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Revenue by Currency</h2>
            <div className="space-y-2">
              {currencyReport.map((row) => (
                <div key={row.currency} className="flex justify-between text-sm border-b border-slate-100 pb-2">
                  <span>{row.currency}</span>
                  <span>{row.payments} payments</span>
                  <span>${row.revenue_usd.toFixed(2)} USD</span>
                </div>
              ))}
              {currencyReport.length === 0 && <p className="text-sm text-slate-500">No completed payments yet.</p>}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-lg font-semibold text-slate-900 mb-3">Gateway / Method Mix</h2>
            <div className="space-y-2">
              {txSummary.map(([method, count]) => (
                <div key={method} className="flex justify-between text-sm border-b border-slate-100 pb-2">
                  <span>{method}</span>
                  <span>{count} tx</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-lg font-semibold text-slate-900 mb-3">Latest Transactions</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-slate-600 border-b border-slate-200">
                  <th className="py-2 pr-4">Time</th>
                  <th className="py-2 pr-4">User</th>
                  <th className="py-2 pr-4">Method</th>
                  <th className="py-2 pr-4">Currency</th>
                  <th className="py-2 pr-4">Amount USD</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Reference</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{tx.attempted_at || '-'}</td>
                    <td className="py-2 pr-4">{tx.user_id}</td>
                    <td className="py-2 pr-4">{tx.payment_method}</td>
                    <td className="py-2 pr-4">{tx.currency}</td>
                  <td className="py-2 pr-4">${(tx.amount_usd || 0).toFixed(2)}</td>
                  <td className="py-2 pr-4">{tx.status}</td>
                  <td className="py-2 pr-4">{tx.payment_reference || '-'}</td>
                </tr>
              ))}
              {transactions.length === 0 && (
                <tr>
                  <td className="py-4 text-slate-500" colSpan={7}>No transactions available.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Admin Controls</h2>
            <p className="text-xs text-slate-500">System-level administrative actions.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={runHealthCheck}
              disabled={llmLoading}
              className="rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {llmLoading ? 'Checking...' : 'LLM Health'}
            </button>
          </div>
        </div>

        <div className="mt-2">
          <button
            onClick={async () => {
              try {
                await resetPremiumDismissals();
                alert('Global premium prompt dismissals reset. Local dismissals will clear shortly.');
              } catch (e) {
                console.error(e);
                alert('Failed to reset dismissals');
              }
            }}
            className="rounded-md bg-rose-600 px-3 py-2 text-xs font-medium text-white hover:bg-rose-700"
          >
            Reset Premium Prompt Dismissals (Global)
          </button>
        </div>
      </div>
    </div>
  );
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
                Keys are encrypted in database and shown masked only. Green circle = Healthy, Red = Issue. Auto-refreshes every 30 seconds.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label className="text-xs flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoRefreshEnabled}
                  onChange={(e) => {
                    setAutoRefreshEnabled(e.target.checked);
                    if (e.target.checked) loadProviders();
                  }}
                  className="w-4 h-4"
                />
                <span>{autoRefreshEnabled ? '🔄 Auto-refresh enabled' : 'Auto-refresh disabled'}</span>
              </label>
              {lastRefreshTime && (
                <div className="text-xs text-slate-500">
                  Last: {lastRefreshTime.toLocaleTimeString()}
                </div>
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
                <pre className="whitespace-pre-wrap break-words text-[12px] bg-slate-50 border border-slate-100 p-2 rounded">{JSON.stringify(llmCheckResult, null, 2)}</pre>
              </div>
            </div>
          )}

          {llmProviders.length === 0 && (
            <p className="text-sm text-slate-500">No provider configuration rows yet.</p>
          )}

          <div className="space-y-3">
            {llmProviders.map((p) => (
              <div key={p.provider} className="rounded-lg border border-slate-200 p-3 space-y-3 min-w-0">
                {p.decryption_failures > 0 && (
                  <div className="text-sm text-red-700 bg-amber-50 border border-amber-100 p-2 rounded">
                    <strong>Decryption issues:</strong> {p.decryption_failures} key(s) failed to decrypt. Update the server `ENCRYPTION_KEY` or re-add keys.
                  </div>
                )}
                <div className="flex flex-wrap items-center gap-3">
                  {/* Live Status Circle */}
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${
                      p.is_healthy 
                        ? 'bg-emerald-500 animate-pulse' 
                        : (p.last_error ? 'bg-red-500 animate-pulse' : 'bg-slate-300')
                    }`} title={p.last_error || 'Status indicator'} />
                    <span className="font-semibold text-slate-900">{p.display_name}</span>
                  </div>
                  <span className="text-xs rounded px-2 py-1 bg-indigo-100 text-indigo-800 font-medium">{p.provider}</span>
                  <span className={`text-xs rounded px-3 py-1 font-semibold ${
                    p.is_healthy 
                      ? 'bg-emerald-100 text-emerald-900' 
                      : (p.last_error ? 'bg-orange-100 text-orange-900' : 'bg-slate-200 text-slate-900')
                  }`}>
                    {p.is_healthy ? '✓ Healthy' : (p.last_error ? '⚠ Issue detected' : '○ Not checked')}
                  </span>
                  {p.last_error && <span className="text-xs font-medium text-red-700 bg-red-50 px-2 py-1 rounded break-all">Reason: {p.last_error}</span>}
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
                    onChange={(e) => setLlmProviders(prev => prev.map(x => x.provider === p.provider ? { ...x, model: e.target.value } : x))}
                    onBlur={(e) => patchProvider(p.provider, { model: e.target.value })}
                    placeholder="Model"
                    className="w-full min-w-0 rounded border border-slate-300 px-2 py-1 text-xs text-slate-900"
                  />
                  <input
                    value={p.endpoint || ''}
                    onChange={(e) => setLlmProviders(prev => prev.map(x => x.provider === p.provider ? { ...x, endpoint: e.target.value } : x))}
                    onBlur={(e) => patchProvider(p.provider, { endpoint: e.target.value })}
                    placeholder="Endpoint"
                    className="w-full min-w-0 rounded border border-slate-300 px-2 py-1 text-xs text-slate-900"
                  />
                  <input
                    type="number"
                    value={p.priority ?? 100}
                    onChange={(e) => setLlmProviders(prev => prev.map(x => x.provider === p.provider ? { ...x, priority: Number(e.target.value || 100) } : x))}
                    onBlur={(e) => patchProvider(p.provider, { priority: Number(e.target.value || 100) })}
                    placeholder="Priority"
                    className="w-full min-w-0 rounded border border-slate-300 px-2 py-1 text-xs text-slate-900"
                  />
                  <div className="text-xs text-slate-700 flex items-center break-all min-w-0">
                    Keys: {p.key_count}
                  </div>
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

                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type="password"
                    value={newKeys[p.provider] || ''}
                    onChange={(e) => setNewKeys(prev => ({ ...prev, [p.provider]: e.target.value }))}
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
                    {providerChecks[p.provider]?.status === 'checking' && providerChecks[p.provider]?.type === 'health' ? 'Checking...' : 'Check'}
                  </button>
                  <button
                    onClick={() => runSingleProviderTest(p.provider)}
                    disabled={providerChecks[p.provider]?.status === 'checking'}
                    className="rounded bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {providerChecks[p.provider]?.status === 'checking' && providerChecks[p.provider]?.type === 'test' ? 'Testing...' : 'Test'}
                  </button>
                  <span className="text-xs text-slate-500">
                    {saveState[p.provider] === 'saving' ? 'Saving...' : saveState[p.provider] === 'saved' ? 'Saved' : saveState[p.provider] === 'deleting' ? 'Deleting...' : saveState[p.provider] === 'deleted' ? 'Deleted' : saveState[p.provider] || ''}
                  </span>
                </div>

                {providerChecks[p.provider]?.result && (
                  <div className="text-xs text-slate-700 bg-slate-50 border border-slate-200 rounded p-2 overflow-x-auto">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">Result:</span>
                      <button
                        onClick={() => setProviderChecks(prev => ({
                          ...prev,
                          [p.provider]: { ...prev[p.provider], result: null }
                        }))}
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
    );
  }
};

export default SuperAdminDashboard;
