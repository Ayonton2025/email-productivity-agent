import { notify } from '../../utils/notifications'
import { logger } from '../../utils/logger.js'
import React from 'react'
import { resetPremiumDismissals } from '../../services/adminService'
const Stat = ({ label, value }) => (
  <div className="rounded-lg border border-slate-200 bg-white p-4">
    <div className="text-xs text-slate-500">{label}</div>
    <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
  </div>
)

export default function AdminOverviewPanel({
  overview,
  currencyReport,
  txSummary,
  transactions,
  runHealthCheck,
  llmLoading,
}) {
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
                  <td className="py-4 text-slate-500" colSpan={7}>
                    No transactions available.
                  </td>
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
                await resetPremiumDismissals()
                notify('Global premium prompt dismissals reset. Local dismissals will clear shortly.')
              } catch (e) {
                logger.error(e)
                notify('Failed to reset dismissals', 'error')
              }
            }}
            className="rounded-md bg-rose-600 px-3 py-2 text-xs font-medium text-white hover:bg-rose-700"
          >
            Reset Premium Prompt Dismissals (Global)
          </button>
        </div>
      </div>
    </div>
  )
}
