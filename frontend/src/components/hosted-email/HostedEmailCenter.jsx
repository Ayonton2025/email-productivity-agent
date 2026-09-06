import HostedSignupForm from './HostedSignupForm'
import React, { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, MailPlus, RefreshCw, Shield } from 'lucide-react'
import { hostedEmailApi } from '../../services/api'

const HostedEmailCenter = () => {
  const [availabilityLocalPart, setAvailabilityLocalPart] = useState('')
  const [availability, setAvailability] = useState(null)
  const [checking, setChecking] = useState(false)
  const [provisioning, setProvisioning] = useState(false)
  const [limitsLoading, setLimitsLoading] = useState(true)
  const [limits, setLimits] = useState(null)
  const [provisionForm, setProvisionForm] = useState({ local_part: '', display_name: '' })
  const [lightSignup, setLightSignup] = useState({ local_part: '', full_name: '', password: '' })
  const [signupResult, setSignupResult] = useState(null)
  const [signupLoading, setSignupLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadLimits = async () => {
    setLimitsLoading(true)
    try {
      const res = await hostedEmailApi.getLimits()
      setLimits(res.data || null)
    } catch (_) {
      setLimits(null)
    } finally {
      setLimitsLoading(false)
    }
  }

  useEffect(() => {
    loadLimits()
  }, [])

  const checkAvailability = async () => {
    setChecking(true)
    setError('')
    setSuccess('')
    setAvailability(null)
    try {
      const res = await hostedEmailApi.checkAvailability(availabilityLocalPart)
      setAvailability(res.data || null)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to check availability')
    } finally {
      setChecking(false)
    }
  }

  const provision = async () => {
    setProvisioning(true)
    setError('')
    setSuccess('')
    try {
      const res = await hostedEmailApi.provision(provisionForm)
      setSuccess(`Hosted mailbox created: ${res.data?.account?.email}`)
      setProvisionForm({ local_part: '', display_name: '' })
      await loadLimits()
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to provision hosted mailbox')
    } finally {
      setProvisioning(false)
    }
  }

  const submitLightSignup = async () => {
    setSignupLoading(true)
    setError('')
    setSuccess('')
    setSignupResult(null)
    try {
      const payload = {
        local_part: lightSignup.local_part,
        full_name: lightSignup.full_name || null,
        password: lightSignup.password || null,
      }
      const res = await hostedEmailApi.signup(payload)
      setSignupResult(res.data || null)
      setSuccess(`Light signup complete for ${res.data?.user?.email}`)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Hosted email signup failed')
    } finally {
      setSignupLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Hosted Email (Bylix Address)</h1>
        <p className="text-sm text-gray-600">
          Provision managed mailboxes (e.g. user@bylix.email), monitor send limits, and use lightweight signup flow.
        </p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-green-700 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" />
          <span>{success}</span>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">Check Availability</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            type="text"
            value={availabilityLocalPart}
            onChange={(e) => setAvailabilityLocalPart(e.target.value)}
            placeholder="local-part"
            className="border border-gray-300 rounded-lg px-3 py-2"
          />
          <button
            type="button"
            onClick={checkAvailability}
            disabled={checking}
            className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${checking ? 'animate-spin' : ''}`} />
            {checking ? 'Checking...' : 'Check'}
          </button>
        </div>
        {availability && (
          <div className="text-sm text-gray-700">
            <div>
              Email: <span className="font-medium">{availability.email || '-'}</span>
            </div>
            <div>
              Available:{' '}
              <span className={availability.available ? 'text-green-700 font-medium' : 'text-red-700 font-medium'}>
                {String(availability.available)}
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">Provision Hosted Mailbox (Authenticated)</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            type="text"
            value={provisionForm.local_part}
            onChange={(e) => setProvisionForm({ ...provisionForm, local_part: e.target.value })}
            placeholder="local-part"
            className="border border-gray-300 rounded-lg px-3 py-2"
          />
          <input
            type="text"
            value={provisionForm.display_name}
            onChange={(e) => setProvisionForm({ ...provisionForm, display_name: e.target.value })}
            placeholder="Display name (optional)"
            className="border border-gray-300 rounded-lg px-3 py-2"
          />
          <button
            type="button"
            onClick={provision}
            disabled={provisioning}
            className="inline-flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-60"
          >
            <MailPlus className="h-4 w-4 mr-2" />
            {provisioning ? 'Provisioning...' : 'Provision'}
          </button>
        </div>
      </div>

      <HostedSignupForm
        lightSignup={lightSignup}
        setLightSignup={setLightSignup}
        submitLightSignup={submitLightSignup}
        signupLoading={signupLoading}
        signupResult={signupResult}
      />

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="h-5 w-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">Abuse & Limits</h2>
        </div>
        {limitsLoading ? (
          <div className="flex items-center gap-2 text-gray-600">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span>Loading limits...</span>
          </div>
        ) : !limits ? (
          <p className="text-sm text-gray-500">No hosted account limits available yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
            <LimitCard label="Daily Limit" value={limits.daily_limit ?? '-'} />
            <LimitCard label="Sent Today" value={limits.sent_today ?? 0} />
            <LimitCard label="Blocked Today" value={limits.blocked_today ?? 0} />
            <LimitCard label="Remaining Today" value={limits.remaining_today ?? '-'} />
            <LimitCard label="Domain Daily Limit" value={limits.domain_daily_limit ?? '-'} />
            <LimitCard label="Spam Threshold" value={limits.spam_threshold ?? '-'} />
          </div>
        )}
      </div>
    </div>
  )
}

const LimitCard = ({ label, value }) => (
  <div className="border border-gray-100 rounded-lg p-3 bg-gray-50">
    <div className="text-gray-500">{label}</div>
    <div className="text-lg font-semibold text-gray-900">{value}</div>
  </div>
)

export default HostedEmailCenter
