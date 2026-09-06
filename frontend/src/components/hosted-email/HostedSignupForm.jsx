import React from 'react'
import { UserPlus } from 'lucide-react'

export default function HostedSignupForm({
  lightSignup,
  setLightSignup,
  submitLightSignup,
  signupLoading,
  signupResult,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
      <div className="flex items-center gap-2">
        <UserPlus className="h-5 w-5 text-indigo-600" />
        <h2 className="text-lg font-semibold text-gray-900">Light Signup Flow (No forced long registration)</h2>
      </div>
      <p className="text-sm text-gray-600">Creates DB user + auth token + hosted mailbox with a single action.</p>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <input
          type="text"
          value={lightSignup.local_part}
          onChange={(e) => setLightSignup({ ...lightSignup, local_part: e.target.value })}
          placeholder="local-part"
          className="border border-gray-300 rounded-lg px-3 py-2"
        />
        <input
          type="text"
          value={lightSignup.full_name}
          onChange={(e) => setLightSignup({ ...lightSignup, full_name: e.target.value })}
          placeholder="Full name (optional)"
          className="border border-gray-300 rounded-lg px-3 py-2"
        />
        <input
          type="password"
          value={lightSignup.password}
          onChange={(e) => setLightSignup({ ...lightSignup, password: e.target.value })}
          placeholder="Password (optional)"
          className="border border-gray-300 rounded-lg px-3 py-2"
        />
        <button
          type="button"
          onClick={submitLightSignup}
          disabled={signupLoading}
          className="inline-flex items-center justify-center px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-60"
        >
          {signupLoading ? 'Creating...' : 'Create Light Signup'}
        </button>
      </div>
      {signupResult && (
        <div className="border border-gray-200 rounded-lg p-3 bg-gray-50 text-sm space-y-1">
          <div>
            <span className="font-medium">User:</span> {signupResult?.user?.email}
          </div>
          <div>
            <span className="font-medium">Mailbox:</span> {signupResult?.account?.email}
          </div>
          <div>
            <span className="font-medium">Token received:</span> {signupResult?.access_token ? 'yes' : 'no'}
          </div>
          {signupResult?.temporary_password && (
            <div className="text-amber-700">
              <span className="font-medium">Temporary app password:</span> {signupResult.temporary_password}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
