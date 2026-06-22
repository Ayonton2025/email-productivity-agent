import React, { useEffect, useState } from 'react';
import { CheckCircle2, Clock3, RefreshCw, Save, AlertCircle, PlayCircle } from 'lucide-react';
import { followupsApi } from '../../services/api';

const FollowUpCenter = () => {
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [policySaving, setPolicySaving] = useState(false);
  const [policy, setPolicy] = useState({
    enabled: true,
    min_delay_hours: 48,
    max_stages: 3,
    auto_send: false,
    tone_profile: 'professional',
  });
  const [queue, setQueue] = useState([]);
  const [queueStatus, setQueueStatus] = useState('pending_approval');
  const [manualSchedule, setManualSchedule] = useState({ emailId: '', delayHours: 48 });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const load = async (status = queueStatus) => {
    setLoading(true);
    setError('');
    try {
      const [policyRes, queueRes] = await Promise.all([
        followupsApi.getPolicy(),
        followupsApi.getQueue(status, 100),
      ]);
      setPolicy(policyRes.data?.policy || policy);
      setQueue(queueRes.data?.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load follow-up center');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(queueStatus);
  }, [queueStatus]);

  const savePolicy = async () => {
    setPolicySaving(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        ...policy,
        min_delay_hours: Number(policy.min_delay_hours),
        max_stages: Number(policy.max_stages),
      };
      const res = await followupsApi.updatePolicy(payload);
      setPolicy(res.data?.policy || payload);
      setSuccess('Follow-up policy updated.');
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to update policy');
    } finally {
      setPolicySaving(false);
    }
  };

  const processDue = async () => {
    setProcessing(true);
    setError('');
    setSuccess('');
    try {
      const res = await followupsApi.processDue();
      const stats = res.data?.stats || {};
      setSuccess(`Processed: ${stats.processed || 0}, queued: ${stats.queued_for_approval || 0}, auto-sent: ${stats.auto_sent || 0}.`);
      await load(queueStatus);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to process due follow-ups');
    } finally {
      setProcessing(false);
    }
  };

  const approveItem = async (executionId) => {
    setError('');
    setSuccess('');
    try {
      await followupsApi.approveQueueItem(executionId);
      setSuccess('Follow-up approved and sent.');
      await load(queueStatus);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to approve follow-up');
    }
  };

  const scheduleManual = async () => {
    setError('');
    setSuccess('');
    if (!manualSchedule.emailId) {
      setError('Provide a sent email ID to schedule follow-up.');
      return;
    }
    try {
      await followupsApi.schedule(manualSchedule.emailId, Number(manualSchedule.delayHours));
      setSuccess('Follow-up scheduled on selected email.');
      setManualSchedule({ ...manualSchedule, emailId: '' });
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to schedule follow-up');
    }
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 flex items-center gap-3">
        <RefreshCw className="h-5 w-5 animate-spin text-indigo-600" />
        <span className="text-gray-700">Loading follow-up center...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Auto Follow-up Agent</h1>
          <p className="text-sm text-gray-600">Manage follow-up policy, queue approvals, and due execution.</p>
        </div>
        <button
          type="button"
          onClick={processDue}
          disabled={processing}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-60"
        >
          <PlayCircle className="h-4 w-4 mr-2" />
          {processing ? 'Processing...' : 'Process Due Follow-ups'}
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

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Policy</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="md:col-span-1">
            <label className="block text-sm text-gray-600 mb-1">Enabled</label>
            <input
              type="checkbox"
              checked={Boolean(policy.enabled)}
              onChange={(e) => setPolicy({ ...policy, enabled: e.target.checked })}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Min Delay (hours)</label>
            <input
              type="number"
              min={1}
              max={720}
              value={policy.min_delay_hours ?? 48}
              onChange={(e) => setPolicy({ ...policy, min_delay_hours: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Max Stages</label>
            <input
              type="number"
              min={1}
              max={10}
              value={policy.max_stages ?? 3}
              onChange={(e) => setPolicy({ ...policy, max_stages: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
          <div className="md:col-span-1">
            <label className="block text-sm text-gray-600 mb-1">Auto-send</label>
            <input
              type="checkbox"
              checked={Boolean(policy.auto_send)}
              onChange={(e) => setPolicy({ ...policy, auto_send: e.target.checked })}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Tone Profile</label>
            <input
              type="text"
              value={policy.tone_profile || 'professional'}
              onChange={(e) => setPolicy({ ...policy, tone_profile: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
        </div>
        <div className="mt-4">
          <button
            type="button"
            onClick={savePolicy}
            disabled={policySaving}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-60"
          >
            <Save className="h-4 w-4 mr-2" />
            {policySaving ? 'Saving...' : 'Save Policy'}
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Manual Scheduling</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            type="text"
            value={manualSchedule.emailId}
            onChange={(e) => setManualSchedule({ ...manualSchedule, emailId: e.target.value })}
            className="border border-gray-300 rounded-lg px-3 py-2"
            placeholder="Sent email ID"
          />
          <input
            type="number"
            min={1}
            max={720}
            value={manualSchedule.delayHours}
            onChange={(e) => setManualSchedule({ ...manualSchedule, delayHours: e.target.value })}
            className="border border-gray-300 rounded-lg px-3 py-2"
            placeholder="Delay hours"
          />
          <button
            type="button"
            onClick={scheduleManual}
            className="inline-flex items-center justify-center px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800"
          >
            <Clock3 className="h-4 w-4 mr-2" />
            Schedule Follow-up
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-3">
          <h2 className="text-lg font-semibold text-gray-900">Approval Queue</h2>
          <select
            value={queueStatus}
            onChange={(e) => setQueueStatus(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="pending_approval">Pending Approval</option>
            <option value="approved_sent">Approved Sent</option>
            <option value="auto_sent">Auto Sent</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {queue.length === 0 ? (
          <p className="text-sm text-gray-500">No follow-up items found for this status.</p>
        ) : (
          <div className="space-y-3">
            {queue.map((item) => (
              <div key={item.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm text-gray-500">Email ID: {item.source_email_id}</div>
                    <div className="font-medium text-gray-900">{item.generated_subject || 'Generated follow-up'}</div>
                    <div className="text-sm text-gray-700 whitespace-pre-wrap mt-1">{item.generated_body || '-'}</div>
                    <div className="text-xs text-gray-500 mt-2">
                      Stage {item.stage} | Status: {item.status} | Scheduled: {item.scheduled_for || 'n/a'}
                    </div>
                  </div>
                  {item.status === 'pending_approval' && (
                    <button
                      type="button"
                      onClick={() => approveItem(item.id)}
                      className="inline-flex items-center px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Approve & Send
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default FollowUpCenter;
