import React, { useState, useEffect } from 'react';
import {
  Plus,
  Trash2,
  Edit2,
  Save,
  X,
  Zap,
  Clock,
  CheckCircle,
  XCircle,
  Mail,
  Filter,
  AlertCircle,
} from 'lucide-react';
import { autoReplyApi } from '../../services/api';

const AutoReplyRules = () => {
  const [rules, setRules] = useState([]);
  const [away, setAway] = useState({ is_active: false, valid_from: null, valid_until: null, message: null });
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    name: '',
    match_category: '',
    match_sender: '',
    instructions: '',
    priority: 0,
    confidence_min: 0,
    require_away_mode: true,
    use_approval_queue: true,
    auto_send: false,
  });
  const [showForm, setShowForm] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [rulesRes, awayRes, queueRes] = await Promise.all([
        autoReplyApi.getRules(),
        autoReplyApi.getAwayMode(),
        autoReplyApi.getApprovalQueue(),
      ]);
      setRules(Array.isArray(rulesRes.data) ? rulesRes.data : []);
      setAway(awayRes.data || { is_active: false });
      setQueue(Array.isArray(queueRes.data) ? queueRes.data : []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load');
      setRules([]);
      setQueue([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleAwayToggle = async () => {
    try {
      await autoReplyApi.setAwayMode({
        is_active: !away.is_active,
        valid_from: away.valid_from || null,
        valid_until: away.valid_until || null,
        message: away.message || null,
      });
      setAway((prev) => ({ ...prev, is_active: !prev.is_active }));
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to update away mode');
    }
  };

  const handleCreateRule = async (e) => {
    e.preventDefault();
    try {
      await autoReplyApi.createRule({
        name: form.name,
        match_category: form.match_category || null,
        match_sender: form.match_sender || null,
        instructions: form.instructions || null,
        priority: form.priority,
        confidence_min: form.confidence_min,
        require_away_mode: form.require_away_mode,
        use_approval_queue: form.use_approval_queue,
        auto_send: form.auto_send,
      });
      setForm({ name: '', match_category: '', match_sender: '', instructions: '', priority: 0, confidence_min: 0, require_away_mode: true, use_approval_queue: true, auto_send: false });
      setShowForm(false);
      load();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to create rule');
    }
  };

  const handleUpdateRule = async (ruleId, patch) => {
    try {
      await autoReplyApi.updateRule(ruleId, patch);
      setEditingId(null);
      load();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to update rule');
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!window.confirm('Delete this rule?')) return;
    try {
      await autoReplyApi.deleteRule(ruleId);
      load();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to delete rule');
    }
  };

  const handleApprove = async (draftId) => {
    try {
      await autoReplyApi.approveDraft(draftId);
      load();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to approve');
    }
  };

  const handleReject = async (draftId) => {
    try {
      await autoReplyApi.rejectDraft(draftId);
      load();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to reject');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Auto-Reply Rules</h1>
        <p className="text-slate-600 mt-1 text-sm">
          Define rules to auto-draft replies when you&apos;re away. Match by category or sender.
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <p className="text-sm text-red-800 flex-1">{error}</p>
          <button
            type="button"
            onClick={() => setError(null)}
            className="p-1 text-red-600 hover:text-red-800 rounded hover:bg-red-100 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Away mode */}
      <div className="page-content p-5">
        <h2 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5 text-slate-600" />
          Away mode
        </h2>
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-slate-600">
            When on, auto-reply rules (that require away mode) will run for new emails.
          </p>
          <button
            type="button"
            onClick={handleAwayToggle}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
              away.is_active ? 'bg-indigo-600' : 'bg-slate-300'
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                away.is_active ? 'translate-x-5' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          {away.is_active ? 'Away mode is ON — auto-reply rules can run.' : 'Away mode is OFF.'}
        </p>
      </div>

      {/* Rules list */}
      <div className="page-content p-5">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <Filter className="h-5 w-5 text-slate-600" />
            Rules
          </h2>
          <button
            type="button"
            onClick={() => {
              setShowForm(true);
              setEditingId(null);
              setForm({
                name: '',
                match_category: '',
                match_sender: '',
                instructions: '',
                priority: 0,
                confidence_min: 0,
                require_away_mode: true,
                use_approval_queue: true,
                auto_send: false,
              });
            }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add rule
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleCreateRule} className="mb-6 p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white text-slate-900 px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Match category (optional)</label>
                <input
                  type="text"
                  value={form.match_category}
                  onChange={(e) => setForm((f) => ({ ...f, match_category: e.target.value }))}
                  placeholder="e.g. Support, To-Do"
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white text-slate-900 px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Match sender (optional)</label>
                <input
                  type="text"
                  value={form.match_sender}
                  onChange={(e) => setForm((f) => ({ ...f, match_sender: e.target.value }))}
                  placeholder="e.g. @client.com"
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white text-slate-900 px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Priority (lower = first)</label>
                <input
                  type="number"
                  value={form.priority}
                  onChange={(e) => setForm((f) => ({ ...f, priority: parseInt(e.target.value, 10) || 0 }))}
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white text-slate-900 px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Instructions (optional)</label>
              <textarea
                value={form.instructions}
                onChange={(e) => setForm((f) => ({ ...f, instructions: e.target.value }))}
                placeholder="e.g. Tell them I'm away and will respond in 48 hours."
                rows={2}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white text-slate-900 px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div className="flex flex-wrap gap-4">
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.require_away_mode}
                  onChange={(e) => setForm((f) => ({ ...f, require_away_mode: e.target.checked }))}
                  className="rounded border-slate-300 text-indigo-600"
                />
                <span className="text-sm text-slate-700">Require away mode</span>
              </label>
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.use_approval_queue}
                  onChange={(e) => setForm((f) => ({ ...f, use_approval_queue: e.target.checked }))}
                  className="rounded border-slate-300 text-indigo-600"
                />
                <span className="text-sm text-slate-700">Use approval queue</span>
              </label>
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.auto_send}
                  onChange={(e) => setForm((f) => ({ ...f, auto_send: e.target.checked }))}
                  className="rounded border-slate-300 text-indigo-600"
                />
                <span className="text-sm text-slate-700">Auto-send (Gmail)</span>
              </label>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
                <Save className="h-4 w-4" />
                Create
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg text-slate-700 bg-white hover:bg-slate-50 transition-colors">
                <X className="h-4 w-4" />
                Cancel
              </button>
            </div>
          </form>
        )}

        {rules.length === 0 ? (
          <p className="text-slate-500 text-sm">No rules yet. Add one to auto-draft replies when away.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {rules.map((r) => (
              <li key={r.id} className="py-4 flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-900">{r.name}</p>
                  <p className="text-sm text-slate-600">
                    Category: {r.match_category || 'any'} · Sender: {r.match_sender || 'any'} · Priority {r.priority}
                  </p>
                  {r.instructions && <p className="text-xs text-slate-500 mt-1">{r.instructions}</p>}
                  <div className="flex gap-2 mt-2">
                    {r.require_away_mode && <span className="badge-default px-2 py-0.5 rounded text-xs font-medium">Away only</span>}
                    {r.use_approval_queue && <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-sky-100 text-sky-800 border border-sky-200">Approval</span>}
                    {r.auto_send && <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">Auto-send</span>}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteRule(r.id)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Approval queue */}
      <div className="page-content p-5">
        <h2 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Mail className="h-5 w-5 text-slate-600" />
          Approval queue
        </h2>
        {queue.length === 0 ? (
          <p className="text-slate-500 text-sm">No pending auto-reply drafts.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {queue.map((d) => (
              <li key={d.id} className="py-4">
                <div className="flex justify-between items-start gap-4">
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900">To: {d.recipient}</p>
                    <p className="text-sm text-slate-600">{d.subject}</p>
                    <p className="text-sm text-slate-500 mt-1 line-clamp-2">{d.body}</p>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => handleApprove(d.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors"
                    >
                      <CheckCircle className="h-4 w-4" />
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => handleReject(d.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
                    >
                      <XCircle className="h-4 w-4" />
                      Reject
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default AutoReplyRules;
