import React, { useEffect, useState } from 'react';
import { Inbox, Plus, UserPlus, Link2, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { sharedInboxApi } from '../../services/api';
import { getSubscription } from '../../services/paymentService';
import { useAuth } from '../../context/AuthContext';

const SharedInboxCenter = () => {
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  const [loading, setLoading] = useState(true);
  const [inboxes, setInboxes] = useState([]);
  const [selectedInbox, setSelectedInbox] = useState(null);
  const [members, setMembers] = useState([]);
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [createForm, setCreateForm] = useState({ name: '', description: '' });
  const [memberEmail, setMemberEmail] = useState('');
  const [emailIdToAdd, setEmailIdToAdd] = useState('');
  const [subscription, setSubscription] = useState(null);
  const [subscriptionLoadFailed, setSubscriptionLoadFailed] = useState(false);
  const [assignedToMeOnly, setAssignedToMeOnly] = useState(false);

  const loadInboxes = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await sharedInboxApi.list();
      const items = res.data?.items || [];
      setInboxes(items);
      if (items.length > 0 && !selectedInbox) setSelectedInbox(items[0]);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load shared inboxes');
    } finally {
      setLoading(false);
    }
  };

  const loadInboxDetails = async (inboxId) => {
    try {
      const [mRes, eRes] = await Promise.all([
        sharedInboxApi.listMembers(inboxId),
        sharedInboxApi.listEmails(inboxId),
      ]);
      setMembers(mRes.data?.members || []);
      setItems(eRes.data?.items || []);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load shared inbox details');
    }
  };

  useEffect(() => {
    loadInboxes();
  }, []);

  useEffect(() => {
    const loadSubscription = async () => {
      try {
        const data = await getSubscription();
        setSubscription(data || null);
        setSubscriptionLoadFailed(false);
      } catch (_e) {
        setSubscription(null);
        setSubscriptionLoadFailed(true);
      }
    };
    loadSubscription();
  }, []);

  useEffect(() => {
    if (selectedInbox?.id) loadInboxDetails(selectedInbox.id);
  }, [selectedInbox?.id]);

  const sharedInboxPlanLimits = {
    team: 5,
    enterprise: 100,
  };

  const currentPlanId = subscription?.plan_id || null;
  const hasSharedInboxFeature = isSuperAdmin || currentPlanId === 'team' || currentPlanId === 'enterprise';
  const sharedInboxLimit = currentPlanId ? (sharedInboxPlanLimits[currentPlanId] || 0) : 0;
  const ownedInboxCount = inboxes.filter((i) => i.member_role === 'owner').length;
  const selectedRole = selectedInbox?.member_role || null;
  const canManageMembers = selectedRole === 'owner' || selectedRole === 'admin';
  const teamMemberLimit = Number(subscription?.team_members_limit || 0);
  const memberCount = members.length;

  const createInbox = async () => {
    if (!createForm.name.trim()) return;
    setError('');
    setSuccess('');

    if (!isSuperAdmin && !subscriptionLoadFailed && !hasSharedInboxFeature) {
      setError('Your current plan does not include shared inbox. Upgrade to Team or Enterprise.');
      return;
    }
    if (!isSuperAdmin && !subscriptionLoadFailed && ownedInboxCount >= sharedInboxLimit) {
      setError(`Plan limit reached: ${sharedInboxLimit} shared inbox(es) allowed.`);
      return;
    }

    try {
      await sharedInboxApi.create(createForm);
      setCreateForm({ name: '', description: '' });
      setSuccess('Shared inbox created.');
      await loadInboxes();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to create shared inbox');
    }
  };

  const addMember = async () => {
    if (!selectedInbox?.id || !memberEmail.trim()) return;
    setError('');
    setSuccess('');

    if (!canManageMembers) {
      setError('Only owner or admin can add members to this shared inbox.');
      return;
    }
    if (!isSuperAdmin && !subscriptionLoadFailed && !hasSharedInboxFeature) {
      setError('Your current plan does not include shared inbox. Upgrade to Team or Enterprise.');
      return;
    }
    if (!isSuperAdmin && !subscriptionLoadFailed && teamMemberLimit > 0 && memberCount >= teamMemberLimit) {
      setError(`Team seat limit reached: ${teamMemberLimit} member(s) allowed for your plan.`);
      return;
    }

    try {
      await sharedInboxApi.addMember(selectedInbox.id, { user_email: memberEmail.trim() });
      setMemberEmail('');
      setSuccess('Member added to shared inbox.');
      await loadInboxDetails(selectedInbox.id);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to add member');
    }
  };

  const addEmail = async () => {
    if (!selectedInbox?.id || !emailIdToAdd.trim()) return;
    setError('');
    setSuccess('');
    try {
      await sharedInboxApi.addEmail(selectedInbox.id, emailIdToAdd.trim());
      setEmailIdToAdd('');
      setSuccess('Email added to shared inbox.');
      await loadInboxDetails(selectedInbox.id);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to add email');
    }
  };

  const setStatus = async (emailId, status) => {
    if (!selectedInbox?.id) return;
    try {
      await sharedInboxApi.updateEmail(selectedInbox.id, emailId, { status });
      await loadInboxDetails(selectedInbox.id);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to update status');
    }
  };

  const setAssignment = async (emailId, assignedToUserEmail) => {
    if (!selectedInbox?.id) return;
    setError('');
    if (!canManageMembers) {
      setError('Only owner or admin can assign inbox items.');
      return;
    }
    try {
      await sharedInboxApi.updateEmail(selectedInbox.id, emailId, { assigned_to_user_email: assignedToUserEmail });
      await loadInboxDetails(selectedInbox.id);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to update assignee');
    }
  };

  const memberEmailById = members.reduce((acc, m) => {
    acc[m.user_id] = m.email;
    return acc;
  }, {});

  const memberDisplayByEmail = members.reduce((acc, m) => {
    acc[m.email] = m.full_name || m.email;
    return acc;
  }, {});

  const currentUserId = user?.id || null;
  const currentUserEmail = user?.email || null;
  const currentMember = members.find((m) => m.email === currentUserEmail);
  const currentMemberId = currentMember?.user_id || null;
  const filteredItems = assignedToMeOnly
    ? items.filter((item) => {
        const assignee = item?.shared?.assigned_to_user_id;
        if (!assignee) return false;
        return assignee === currentUserId || assignee === currentMemberId;
      })
    : items;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Shared Inbox</h1>
          <p className="text-sm text-slate-500">Collaborative inbox for team triage and assignment.</p>
        </div>
        <button
          onClick={loadInboxes}
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
      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4" /> {success}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
          <h2 className="font-semibold text-slate-900">Create Inbox</h2>
          <input
            value={createForm.name}
            onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
            placeholder="Sales Team Inbox"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <textarea
            value={createForm.description}
            onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
            placeholder="Description"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            rows={2}
          />
          <button
            onClick={createInbox}
            disabled={(!isSuperAdmin && !subscriptionLoadFailed && !hasSharedInboxFeature) || (!isSuperAdmin && !subscriptionLoadFailed && ownedInboxCount >= sharedInboxLimit)}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            Create
          </button>
          {!isSuperAdmin && !subscriptionLoadFailed && !hasSharedInboxFeature && (
            <p className="text-xs text-amber-700">Team or Enterprise plan required for shared inbox.</p>
          )}
          {!isSuperAdmin && !subscriptionLoadFailed && hasSharedInboxFeature && ownedInboxCount >= sharedInboxLimit && (
            <p className="text-xs text-amber-700">You reached your shared inbox plan limit ({sharedInboxLimit}).</p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 lg:col-span-2">
          <h2 className="font-semibold text-slate-900 mb-3">Your Shared Inboxes</h2>
          {loading ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : inboxes.length === 0 ? (
            <p className="text-sm text-slate-500">No shared inboxes yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {inboxes.map((inbox) => (
                <button
                  key={inbox.id}
                  onClick={() => setSelectedInbox(inbox)}
                  className={`rounded-lg border p-3 text-left ${
                    selectedInbox?.id === inbox.id ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Inbox className="h-4 w-4 text-indigo-600" />
                    <p className="font-medium text-slate-900">{inbox.name}</p>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{inbox.description || 'No description'}</p>
                  <p className="text-xs text-slate-600 mt-1">Items: {inbox.email_count || 0}</p>
                  <p className="text-xs text-slate-600 mt-1">Role: {inbox.member_role || 'member'}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedInbox && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
            <h3 className="font-semibold text-slate-900">Members</h3>
            <div className="flex gap-2">
              <input
                value={memberEmail}
                onChange={(e) => setMemberEmail(e.target.value)}
                placeholder="member@company.com"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                onClick={addMember}
                disabled={!canManageMembers || (!isSuperAdmin && !subscriptionLoadFailed && teamMemberLimit > 0 && memberCount >= teamMemberLimit)}
                className="rounded-lg bg-slate-900 px-3 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                <UserPlus className="h-4 w-4" />
              </button>
            </div>
            {!canManageMembers && (
              <p className="text-xs text-amber-700">Only owner/admin can add members.</p>
            )}
            {canManageMembers && !isSuperAdmin && !subscriptionLoadFailed && teamMemberLimit > 0 && memberCount >= teamMemberLimit && (
              <p className="text-xs text-amber-700">Team seat limit reached ({teamMemberLimit}).</p>
            )}
            <div className="space-y-2 text-sm">
              {members.map((m) => (
                <div key={m.id} className="rounded-lg border border-slate-200 p-2">
                  <div className="font-medium text-slate-900">{m.full_name || m.email}</div>
                  <div className="text-xs text-slate-500">{m.email} · {m.role}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3 lg:col-span-2">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold text-slate-900">Inbox Items</h3>
              <button
                onClick={() => setAssignedToMeOnly((v) => !v)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  assignedToMeOnly
                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                    : 'border-slate-300 bg-white text-slate-600'
                }`}
              >
                Assigned to me
              </button>
            </div>
            {!canManageMembers && (
              <p className="text-xs text-amber-700">Assignment changes are limited to owner/admin.</p>
            )}
            <div className="flex gap-2">
              <input
                value={emailIdToAdd}
                onChange={(e) => setEmailIdToAdd(e.target.value)}
                placeholder="Email ID from your inbox"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <button onClick={addEmail} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-white">
                <Link2 className="h-4 w-4" /> Add
              </button>
            </div>
            <div className="space-y-2">
              {filteredItems.map((item) => (
                <div key={item.shared.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{item.email.subject || '(No subject)'}</p>
                      <p className="text-xs text-slate-500">{item.email.sender}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={item.shared.status}
                        onChange={(e) => setStatus(item.email.id, e.target.value)}
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                      >
                        <option value="open">open</option>
                        <option value="in_progress">in_progress</option>
                        <option value="resolved">resolved</option>
                      </select>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-slate-500">Assigned:</span>
                    {canManageMembers ? (
                      <select
                        value={memberEmailById[item.shared.assigned_to_user_id] || ''}
                        onChange={(e) => setAssignment(item.email.id, e.target.value)}
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                      >
                        <option value="">unassigned</option>
                        {members.map((m) => (
                          <option key={m.id} value={m.email}>
                            {m.full_name || m.email}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-xs text-slate-700">
                        {item.shared.assigned_to_user_id
                          ? (memberDisplayByEmail[memberEmailById[item.shared.assigned_to_user_id]] || 'assigned')
                          : 'unassigned'}
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-xs text-slate-600">{item.email.body_preview}</p>
                </div>
              ))}
              {filteredItems.length === 0 && (
                <p className="text-sm text-slate-500">
                  {assignedToMeOnly ? 'No items currently assigned to you.' : 'No shared items yet.'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SharedInboxCenter;
