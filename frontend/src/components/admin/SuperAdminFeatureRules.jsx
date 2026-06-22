import React, { useMemo, useState, useEffect } from 'react';
import { getUserAccessProfile, updateUserAccessProfile, getFeatureTemplates } from '../../services/adminService';

const SuperAdminFeatureRules = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);
  const [featureOverrides, setFeatureOverrides] = useState({});
  const [query, setQuery] = useState('');
  const [templates, setTemplates] = useState({}); // NEW: Store fetched templates

  // NEW: Fetch templates on mount
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const response = await getFeatureTemplates();
        if (response.success && response.templates) {
          setTemplates(response.templates);
        }
      } catch (e) {
        console.warn('Failed to fetch feature templates:', e);
        // Fallback: set empty templates (users can still manually toggle)
        setTemplates({});
      }
    };
    fetchTemplates();
  }, []);

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
      setFeatureOverrides({ ...(res?.override?.feature_overrides || {}) });
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to load user profile');
    } finally {
      setLoading(false);
    }
  };

  const featureList = useMemo(() => {
    const fromAccess = Object.keys(data?.feature_access || {});
    const fromPlan = Object.keys(data?.subscription?.features || {});
    const merged = Array.from(new Set([...fromAccess, ...fromPlan])).sort();
    if (!query.trim()) return merged;
    const q = query.toLowerCase();
    return merged.filter((x) => x.toLowerCase().includes(q));
  }, [data, query]);

  const applyTemplate = (templateName) => {
    const template = templates[templateName];
    if (!template || !template.features) {
      console.error(`Template ${templateName} not found`);
      return;
    }

    const selected = template.features;
    const merged = {};
    const knownFeatures = Array.from(
      new Set([
        ...Object.keys(data?.feature_access || {}),
        ...Object.keys(data?.subscription?.features || {}),
        ...Object.keys(featureOverrides || {}),
        ...Object.keys(selected),
      ])
    );

    for (const f of knownFeatures) {
      merged[f] = !!selected[f];
    }
    setFeatureOverrides(merged);
  };

  const saveFeatureRules = async () => {
    if (!data?.user?.email) return;
    try {
      setSaving(true);
      setError('');
      await updateUserAccessProfile(data.user.email, {
        allow_all: !!data?.override?.allow_all,
        block_all: !!data?.override?.block_all,
        payment_bypass: !!data?.override?.payment_bypass,
        is_active: !!data?.user?.is_active,
        status_note: data?.override?.status_note || '',
        feature_overrides: featureOverrides,
      });
      await loadProfile();
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed to save feature rules');
    } finally {
      setSaving(false);
    }
  };

  const setRule = (feature, allowed) => {
    setFeatureOverrides((prev) => ({ ...prev, [feature]: !!allowed }));
  };

  const clearRule = (feature) => {
    setFeatureOverrides((prev) => {
      const next = { ...prev };
      delete next[feature];
      return next;
    });
  };

  return (
    <div className="p-6 space-y-6 text-slate-900">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Feature Rules</h1>
        <p className="text-slate-600 text-sm">Per-user, per-feature allow/deny overrides.</p>
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
        <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{data.user.email}</h2>
              <p className="text-xs text-slate-500">Plan: {data.subscription?.plan_name} ({data.subscription?.plan_id})</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => applyTemplate('plus')}
                className="rounded bg-amber-100 px-3 py-2 text-xs font-medium text-amber-900 hover:bg-amber-200"
              >
                Set Plus-like
              </button>
              <button
                type="button"
                onClick={() => applyTemplate('pro')}
                className="rounded bg-indigo-100 px-3 py-2 text-xs font-medium text-indigo-900 hover:bg-indigo-200"
              >
                Set Pro-like
              </button>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter features..."
                className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 md:w-64"
              />
            </div>
          </div>

          <div className="space-y-2">
            {featureList.map((feature) => {
              const rule = Object.prototype.hasOwnProperty.call(featureOverrides, feature) ? featureOverrides[feature] : null;
              const effective = data?.feature_access?.[feature];
              return (
                <div key={feature} className="border border-slate-200 rounded p-3">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-900 text-sm">{feature}</div>
                      <div className="text-xs text-slate-500">
                        Current: {effective ? 'Allowed' : 'Limited'} | Override: {rule === null ? 'Inherit' : (rule ? 'Allow' : 'Deny')}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setRule(feature, true)}
                        className={`rounded px-3 py-1 text-xs font-medium ${rule === true ? 'bg-emerald-600 text-white' : 'bg-emerald-100 text-emerald-800'}`}
                      >
                        Allow
                      </button>
                      <button
                        type="button"
                        onClick={() => setRule(feature, false)}
                        className={`rounded px-3 py-1 text-xs font-medium ${rule === false ? 'bg-rose-600 text-white' : 'bg-rose-100 text-rose-800'}`}
                      >
                        Deny
                      </button>
                      <button
                        type="button"
                        onClick={() => clearRule(feature)}
                        className={`rounded px-3 py-1 text-xs font-medium ${rule === null ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-700'}`}
                      >
                        Inherit
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
            {featureList.length === 0 && (
              <p className="text-sm text-slate-500">No features available for this user.</p>
            )}
          </div>

          <div className="pt-2">
            <button
              onClick={saveFeatureRules}
              disabled={saving}
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Feature Rules'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuperAdminFeatureRules;
