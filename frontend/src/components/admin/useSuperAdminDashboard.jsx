import { useEffect, useMemo, useState } from 'react'
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
} from '../../services/adminService'

export function useSuperAdminDashboard({ view = 'dashboard' }) {
  const [overview, setOverview] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [currencyReport, setCurrencyReport] = useState([])
  const [llmProviders, setLlmProviders] = useState([])
  const [llmLoading, setLlmLoading] = useState(false)
  const [llmCheckResult, setLlmCheckResult] = useState(null)
  const [providerChecks, setProviderChecks] = useState({})
  const [saveState, setSaveState] = useState({})
  const [newKeys, setNewKeys] = useState({})
  const [confirmDelete, setConfirmDelete] = useState({ provider: null, keyIndex: null, maskedKey: null })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true)
  const [lastRefreshTime, setLastRefreshTime] = useState(null)
  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const [o, t, r] = await Promise.all([getAdminOverview(), getAdminTransactions(200), getRevenueByCurrency()])
        setOverview(o?.metrics || null)
        setTransactions(t?.transactions || [])
        setCurrencyReport(r?.report || [])
      } catch (e) {
        setError(e?.response?.data?.detail || e.message || 'Failed to load admin dashboard')
      } finally {
        setLoading(false)
      }
    }
    load()
    loadProviders()
  }, [])
  const loadProviders = async () => {
    try {
      setLlmLoading(true)
      const res = await getLLMProviders()
      setLlmProviders(res?.providers || [])
      setLastRefreshTime(new Date())
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to load LLM providers')
    } finally {
      setLlmLoading(false)
    }
  }
  useEffect(() => {
    if (!autoRefreshEnabled || view !== 'llm') return

    const refreshInterval = setInterval(() => {
      loadProviders()
    }, 30000) // Refresh every 30 seconds

    return () => clearInterval(refreshInterval)
  }, [autoRefreshEnabled, view])
  const patchProvider = async (provider, patch) => {
    setSaveState((prev) => ({ ...prev, [provider]: 'saving' }))
    try {
      await updateLLMProvider(provider, patch)
      await loadProviders()
      setSaveState((prev) => ({ ...prev, [provider]: 'saved' }))
    } catch (e) {
      setSaveState((prev) => ({ ...prev, [provider]: e?.response?.data?.detail || e.message || 'Failed' }))
    }
  }
  const rotateKey = async (provider) => {
    const key = (newKeys[provider] || '').trim()
    if (!key) return
    setSaveState((prev) => ({ ...prev, [provider]: 'saving' }))
    try {
      await rotateLLMProviderKey(provider, key)
      setNewKeys((prev) => ({ ...prev, [provider]: '' }))
      await loadProviders()
      setSaveState((prev) => ({ ...prev, [provider]: 'saved' }))
    } catch (e) {
      setSaveState((prev) => ({ ...prev, [provider]: e?.response?.data?.detail || e.message || 'Failed' }))
    }
  }
  const confirmDeleteKey = async (provider, keyIndex) => {
    setSaveState((prev) => ({ ...prev, [provider]: 'deleting' }))
    try {
      await deleteLLMProviderKey(provider, keyIndex)
      setConfirmDelete({ provider: null, keyIndex: null, maskedKey: null })
      await loadProviders()
      setSaveState((prev) => ({ ...prev, [provider]: 'deleted' }))
      setTimeout(() => setSaveState((prev) => ({ ...prev, [provider]: '' })), 2000)
    } catch (e) {
      setSaveState((prev) => ({ ...prev, [provider]: e?.response?.data?.detail || e.message || 'Failed to delete' }))
    }
  }
  const runHealthCheck = async () => {
    setLlmLoading(true)
    try {
      const res = await runLLMHealthCheck()
      // res may include health and providers
      setLlmCheckResult(res?.health || res || { message: 'No details returned' })
      await loadProviders()
    } catch (e) {
      const msg = e?.response?.data || e.message || 'Failed to run provider health check'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
      setLlmCheckResult({ error: msg })
    } finally {
      setLlmLoading(false)
    }
  }
  const runSingleProviderHealthCheck = async (provider) => {
    setProviderChecks((prev) => ({ ...prev, [provider]: { status: 'checking', type: 'health' } }))
    try {
      const res = await runLLMProviderHealthCheck(provider)
      const providerResult = res?.provider_health || null
      setProviderChecks((prev) => ({
        ...prev,
        [provider]: {
          status: 'done',
          type: 'health',
          result: providerResult || { message: res?.health?.message || 'No provider result returned' },
        },
      }))
      await loadProviders()
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || 'Failed to run provider health check'
      setProviderChecks((prev) => ({
        ...prev,
        [provider]: { status: 'error', type: 'health', result: { error: msg } },
      }))
    }
  }
  const runSingleProviderTest = async (provider) => {
    setProviderChecks((prev) => ({ ...prev, [provider]: { status: 'checking', type: 'test' } }))
    try {
      const res = await runLLMSingleProviderTest(provider)
      const providerResult = res?.provider_result || null
      setProviderChecks((prev) => ({
        ...prev,
        [provider]: {
          status: 'done',
          type: 'test',
          result: providerResult || { message: res?.test_results?.message || 'No provider test result returned' },
        },
      }))
      await loadProviders()
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || 'Failed to run provider test'
      setProviderChecks((prev) => ({
        ...prev,
        [provider]: { status: 'error', type: 'test', result: { error: msg } },
      }))
    }
  }
  const txSummary = useMemo(() => {
    const byMethod = {}
    for (const tx of transactions) {
      const key = tx.payment_method || 'unknown'
      byMethod[key] = (byMethod[key] || 0) + 1
    }
    return Object.entries(byMethod).sort((a, b) => b[1] - a[1])
  }, [transactions])
  return {
    overview,
    setOverview,
    transactions,
    setTransactions,
    currencyReport,
    setCurrencyReport,
    llmProviders,
    setLlmProviders,
    llmLoading,
    setLlmLoading,
    llmCheckResult,
    setLlmCheckResult,
    providerChecks,
    setProviderChecks,
    saveState,
    setSaveState,
    newKeys,
    setNewKeys,
    confirmDelete,
    setConfirmDelete,
    loading,
    setLoading,
    error,
    setError,
    autoRefreshEnabled,
    setAutoRefreshEnabled,
    lastRefreshTime,
    setLastRefreshTime,
    loadProviders,
    patchProvider,
    rotateKey,
    confirmDeleteKey,
    runHealthCheck,
    runSingleProviderHealthCheck,
    runSingleProviderTest,
    txSummary,
  }
}
