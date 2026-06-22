import React, { useEffect, useState } from 'react';
import { Gauge, RefreshCw, AlertCircle } from 'lucide-react';
import { deliverabilityApi } from '../../services/api';

const DeliverabilityCenter = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);

  const load = async (windowDays = days) => {
    setLoading(true);
    setError('');
    try {
      const res = await deliverabilityApi.getScore(windowDays);
      setData(res.data || null);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load deliverability score');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(30);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Deliverability Score</h1>
          <p className="text-sm text-slate-500">Monitor sending health, spam risk, and remediation actions.</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
          <button
            onClick={() => load(days)}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-500">Loading score...</div>
      ) : !data ? (
        <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-500">No data available.</div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2 text-slate-600 text-sm">
                <Gauge className="h-4 w-4" /> Health Score
              </div>
              <div className="text-4xl font-bold text-slate-900 mt-2">{data.score}</div>
              <div className="text-sm text-slate-500">Grade {data.grade}</div>
            </div>
            <MetricCard label="Bounce Rate" value={`${(data.metrics?.bounce_rate * 100).toFixed(2)}%`} />
            <MetricCard label="Block Rate" value={`${(data.metrics?.hosted_block_rate * 100).toFixed(2)}%`} />
            <MetricCard label="Open Rate" value={`${(data.metrics?.open_rate * 100).toFixed(2)}%`} />
            <MetricCard label="Reply Rate" value={`${(data.metrics?.reply_rate * 100).toFixed(2)}%`} />
            <MetricCard label="Avg Spam Score" value={data.metrics?.avg_spam_score ?? 0} />
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="font-semibold text-slate-900 mb-2">Recommendations</h2>
            <ul className="list-disc pl-5 text-sm text-slate-700 space-y-1">
              {(data.recommendations || []).map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

const MetricCard = ({ label, value }) => (
  <div className="rounded-xl border border-slate-200 bg-white p-5">
    <div className="text-sm text-slate-500">{label}</div>
    <div className="text-2xl font-semibold text-slate-900 mt-1">{value}</div>
  </div>
);

export default DeliverabilityCenter;
