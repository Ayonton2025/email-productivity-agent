import React, { useEffect, useState } from 'react';
import { Crown, Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import { executiveApi } from '../../services/api';

const ExecutiveCenter = () => {
  const [loading, setLoading] = useState(true);
  const [commandLoading, setCommandLoading] = useState(false);
  const [error, setError] = useState('');
  const [summary, setSummary] = useState(null);
  const [objective, setObjective] = useState('');
  const [commandResult, setCommandResult] = useState(null);

  const loadSummary = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await executiveApi.getSummary();
      setSummary(res.data || null);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load executive summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const runCommand = async () => {
    if (!objective.trim()) return;
    setCommandLoading(true);
    setError('');
    try {
      const res = await executiveApi.command({ objective: objective.trim() });
      setCommandResult(res.data || null);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to run executive AI command');
    } finally {
      setCommandLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Executive AI</h1>
          <p className="text-sm text-slate-500">AI-powered communication operating layer across briefing, inbox, and deliverability.</p>
        </div>
        <button
          onClick={loadSummary}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-500">Loading executive context...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card
            title="Deliverability"
            value={`${summary?.deliverability?.score ?? '-'} (${summary?.deliverability?.grade ?? '-'})`}
            subtitle="Sending health score"
          />
          <Card
            title="Shared Inboxes"
            value={summary?.shared_inbox?.inboxes ?? 0}
            subtitle={`Open items: ${summary?.shared_inbox?.open_items ?? 0}`}
          />
          <Card
            title="Briefing Priorities"
            value={(summary?.briefing?.content?.priorities || []).length}
            subtitle="Today"
          />
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Crown className="h-4 w-4 text-indigo-600" />
          <h2 className="font-semibold text-slate-900">Executive Command</h2>
        </div>
        <textarea
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          placeholder="Example: Give me a 7-day communication operating plan to improve reply rate and reduce spam risk."
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          rows={3}
        />
        <button
          onClick={runCommand}
          disabled={commandLoading || !objective.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Sparkles className="h-4 w-4" />
          {commandLoading ? 'Running...' : 'Run Executive AI'}
        </button>

        {commandResult && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-sm font-semibold text-slate-900">{commandResult.assistant_message || 'Executive response'}</p>
            {Array.isArray(commandResult.suggested_actions) && commandResult.suggested_actions.length > 0 && (
              <ul className="list-disc pl-5 text-sm text-slate-700 mt-2">
                {commandResult.suggested_actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const Card = ({ title, value, subtitle }) => (
  <div className="rounded-xl border border-slate-200 bg-white p-5">
    <p className="text-sm text-slate-500">{title}</p>
    <p className="text-2xl font-semibold text-slate-900 mt-1">{value}</p>
    <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
  </div>
);

export default ExecutiveCenter;
