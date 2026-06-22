import React, { useState } from 'react';
import { getUserAccessProfile, getUserSendReadiness, updateUserAccessProfile } from '../../services/adminService';

const SuperAdminUserAccess = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [sendReadiness, setSendReadiness] = useState(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [form, setForm] = useState({
    allow_all: false,
    block_all: false,
    payment_bypass: false,
    is_active: true,
    status_note: '',
  });

  const loadProfile = async () => {
    setError('');
    if (!email.trim()) {
      setError('Enter user email');
      return;
    }
    try {
      setLoading(true);
      const res = await getUserAccessProfile(email.trim());
      setData(res);
      setReadinessLoading(true);
      try {
        const readiness = await getUserSendReadiness(email.trim());
        setSendReadiness(readiness);
      } catch {
        setSendReadiness(null);
      } finally {
        setReadinessLoading(false);
      }
      const ov = res?.override || {};
      setForm({
        allow_all: !!ov.allow_all,
        block_all: !!ov.block_all,
        payment_bypass: !!ov.payment_bypass,
        is_active: !!res?.user?.is_active,
        status_note: ov.status_note || '',
      });
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to load user profile');
      setSendReadiness(null);
    } finally {
      setLoading(false);
    }
  };

  const saveOverrides = async () => {
    if (!data?.user?.email) return;
    try {
      setSaving(true);
      setError('');
      await updateUserAccessProfile(data.user.email, {
        allow_all: form.allow_all,
        block_all: form.block_all,
        payment_bypass: form.payment_bypass,
        is_active: form.is_active,
        status_note: form.status_note,
        feature_overrides: data?.override?.feature_overrides || {},
      });
      await loadProfile();
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to save overrides');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6 text-slate-900">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">User Access Control</h1>
        <p className="text-slate-600 text-sm">
          Super admin page to inspect any user by email, bypass payments, or limit/allow access.
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@example.com"
            className="flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400"
          />
          <button
            onClick={loadProfile}
            disabled={loading}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load User'}
          </button>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      {data?.user && (
        <div className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="text-lg font-semibold text-slate-900">User Status</h2>
            <div className="mt-3 grid grid-cols-1 gap-3 text-sm text-slate-800 md:grid-cols-2">
              <div><span className="text-slate-500">Email:</span> <span className="break-all">{data.user.email}</span></div>
              <div><span className="text-slate-500">Name:</span> {data.user.full_name || '-'}</div>
              <div><span className="text-slate-500">Plan:</span> {data.subscription?.plan_name} ({data.subscription?.plan_id})</div>
              <div><span className="text-slate-500">Subscription:</span> {data.subscription?.status}</div>
              <div><span className="text-slate-500">AI Credits Balance:</span> {data.credits?.balance ?? 0}</div>
              <div><span className="text-slate-500">Account Active:</span> {String(data.user.is_active)}</div>
              <div><span className="text-slate-500">Super Admin:</span> {String(data.user.is_super_admin)}</div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-lg font-semibold text-slate-900">Send Readiness</h2>
              {readinessLoading && <span className="text-xs text-slate-500">Checking...</span>}
            </div>
            {sendReadiness ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  <div className="text-slate-800">
                    Campaigns:
                    <span className={`ml-2 rounded px-2 py-1 text-xs font-semibold ${sendReadiness?.overall?.campaign_ready ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                      {sendReadiness?.overall?.campaign_ready ? 'Ready' : 'Not Ready'}
                    </span>
                  </div>
                  <div className="text-slate-800">
                    Direct/Reply Send:
                    <span className={`ml-2 rounded px-2 py-1 text-xs font-semibold ${sendReadiness?.overall?.reply_ready ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                      {sendReadiness?.overall?.reply_ready ? 'Ready' : 'Not Ready'}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-slate-600">
                  Global checks:
                  <span className="ml-2">User active: {String(sendReadiness?.global_checks?.user_active)}</span>
                  <span className="ml-2">Celery: {String(sendReadiness?.global_checks?.celery_enabled)}</span>
                  <span className="ml-2">Redis config: {String(sendReadiness?.global_checks?.redis_configured)}</span>
                </div>
                <div className="space-y-2">
                  {(sendReadiness?.accounts || []).map((acc) => (
                    <div key={acc.id} className="rounded border border-slate-200 p-2">
                      <div className="flex flex-wrap items-center gap-2 text-sm text-slate-900">
                        <span className="font-medium break-all">{acc.email}</span>
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">{acc.provider}</span>
                        {acc.is_primary && <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs text-indigo-700">Primary</span>}
                        <span className={`rounded px-2 py-0.5 text-xs font-semibold ${acc.campaign_send_ready ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                          Campaign {acc.campaign_send_ready ? 'OK' : 'Blocked'}
                        </span>
                        <span className={`rounded px-2 py-0.5 text-xs font-semibold ${acc.reply_send_ready ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                          Reply {acc.reply_send_ready ? 'OK' : 'Blocked'}
                        </span>
                      </div>
                      {!!acc.issues?.length && (
                        <div className="mt-1 text-xs text-rose-700 break-all">
                          Issues: {acc.issues.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                  {!(sendReadiness?.accounts || []).length && (
                    <p className="text-sm text-slate-500">No linked email accounts found.</p>
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500">Load a user to check send readiness.</p>
            )}
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
            <h2 className="text-lg font-semibold text-slate-900">Admin Override Controls</h2>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={form.allow_all}
                onChange={(e) => setForm((p) => ({ ...p, allow_all: e.target.checked }))}
              />
              Allow all features for this user
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={form.block_all}
                onChange={(e) => setForm((p) => ({ ...p, block_all: e.target.checked }))}
              />
              Block all feature access for this user
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={form.payment_bypass}
                onChange={(e) => setForm((p) => ({ ...p, payment_bypass: e.target.checked }))}
              />
              Payment bypass (no credit/payment limits)
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))}
              />
              Account active
            </label>
            <textarea
              value={form.status_note}
              onChange={(e) => setForm((p) => ({ ...p, status_note: e.target.value }))}
              placeholder="Admin note"
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400"
              rows={3}
            />
            <button
              onClick={saveOverrides}
              disabled={saving}
              className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Controls'}
            </button>
            <p className="text-xs text-slate-500">
              Feature-level allow/deny rules are now in the <strong>Feature Rules</strong> admin page.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuperAdminUserAccess;
