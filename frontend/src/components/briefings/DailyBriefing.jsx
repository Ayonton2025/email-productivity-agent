import React, { useEffect, useMemo, useState } from 'react';
import { CalendarClock, RefreshCw, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import { briefingsApi } from '../../services/api';

const DailyBriefing = () => {
  const [loading, setLoading] = useState(true);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [briefing, setBriefing] = useState(null);
  const [prefs, setPrefs] = useState({
    timezone: 'UTC',
    send_hour: 6,
    enabled: true,
  });

  const metrics = useMemo(() => briefing?.content?.metrics || {}, [briefing]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [briefingRes, prefsRes] = await Promise.all([
          briefingsApi.getToday(),
          briefingsApi.getPreferences(),
        ]);
        setBriefing(briefingRes.data?.briefing || null);
        setPrefs(prefsRes.data?.preferences || prefs);
      } catch (e) {
        setError(e?.response?.data?.detail || 'Failed to load daily briefing');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleSavePreferences = async () => {
    setSavingPrefs(true);
    setError('');
    setSuccess('');
    try {
      const res = await briefingsApi.updatePreferences({
        timezone: prefs.timezone,
        send_hour: Number(prefs.send_hour),
        enabled: Boolean(prefs.enabled),
      });
      setPrefs(res.data?.preferences || prefs);
      setSuccess('Briefing preferences updated.');
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to update preferences');
    } finally {
      setSavingPrefs(false);
    }
  };

  const handleRegenerate = async () => {
    setRegenerating(true);
    setError('');
    setSuccess('');
    try {
      const res = await briefingsApi.regenerateToday();
      setBriefing(res.data?.briefing || null);
      setSuccess('Daily briefing regenerated.');
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to regenerate briefing');
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 flex items-center gap-3">
        <RefreshCw className="h-5 w-5 animate-spin text-indigo-600" />
        <span className="text-gray-700">Loading daily briefing...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daily AI Briefing</h1>
          <p className="text-sm text-gray-600">Your cached morning digest of priorities, risks, and follow-ups.</p>
        </div>
        <button
          type="button"
          onClick={handleRegenerate}
          disabled={regenerating}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${regenerating ? 'animate-spin' : ''}`} />
          {regenerating ? 'Regenerating...' : 'Regenerate Today'}
        </button>
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="text-sm text-gray-500">Unresolved Commitments</div>
          <div className="text-2xl font-semibold text-gray-900">{metrics.unresolved_commitments || 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="text-sm text-gray-500">Negative Sentiment Emails</div>
          <div className="text-2xl font-semibold text-gray-900">{metrics.high_sentiment_negative_emails || 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="text-sm text-gray-500">Idle Threads</div>
          <div className="text-2xl font-semibold text-gray-900">{metrics.idle_threads || 0}</div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <CalendarClock className="h-5 w-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">Today&apos;s Briefing</h2>
        </div>
        <p className="text-gray-800 whitespace-pre-wrap mb-4">
          {briefing?.content?.overview || 'No briefing overview available yet.'}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <BriefingList title="Priorities" items={briefing?.content?.priorities} itemRender={(item) => item?.title || item} />
          <BriefingList title="Risks" items={briefing?.content?.risks} />
          <BriefingList
            title="Follow-ups"
            items={briefing?.content?.follow_ups}
            itemRender={(item) => item?.action || item?.thread_or_email || item}
          />
          <BriefingList
            title="Schedule"
            items={briefing?.content?.schedule}
            itemRender={(item) => `${item?.item || 'Task'}${item?.date ? ` (${item.date})` : ''}`}
          />
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Digest Preferences</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Timezone</label>
            <input
              type="text"
              value={prefs.timezone || ''}
              onChange={(e) => setPrefs({ ...prefs, timezone: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              placeholder="UTC"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Send Hour (0-23)</label>
            <input
              type="number"
              min={0}
              max={23}
              value={prefs.send_hour ?? 6}
              onChange={(e) => setPrefs({ ...prefs, send_hour: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
          <div className="flex items-center gap-2 pt-7">
            <input
              id="digest-enabled"
              type="checkbox"
              checked={Boolean(prefs.enabled)}
              onChange={(e) => setPrefs({ ...prefs, enabled: e.target.checked })}
            />
            <label htmlFor="digest-enabled" className="text-sm text-gray-700">Enable daily digest</label>
          </div>
        </div>
        <div className="mt-4">
          <button
            type="button"
            onClick={handleSavePreferences}
            disabled={savingPrefs}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-60"
          >
            <Save className="h-4 w-4 mr-2" />
            {savingPrefs ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </div>
  );
};

const BriefingList = ({ title, items, itemRender }) => {
  const list = Array.isArray(items) ? items : [];
  return (
    <div className="border border-gray-100 rounded-lg p-3 bg-gray-50">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{title}</h3>
      {list.length === 0 ? (
        <p className="text-sm text-gray-500">No items.</p>
      ) : (
        <ul className="space-y-2 text-sm text-gray-700">
          {list.map((item, idx) => (
            <li key={`${title}-${idx}`} className="bg-white border border-gray-100 rounded p-2">
              {itemRender ? itemRender(item) : (typeof item === 'string' ? item : JSON.stringify(item))}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default DailyBriefing;
