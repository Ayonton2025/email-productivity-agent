import React from 'react'
import { UserPlus, Link2 } from 'lucide-react'

export default function SharedInboxDetails({
  selectedInbox,
  memberEmail,
  setMemberEmail,
  addMember,
  canManageMembers,
  isSuperAdmin,
  subscriptionLoadFailed,
  teamMemberLimit,
  memberCount,
  members,
  setAssignedToMeOnly,
  assignedToMeOnly,
  emailIdToAdd,
  setEmailIdToAdd,
  addEmail,
  filteredItems,
  setStatus,
  memberEmailById,
  setAssignment,
  memberDisplayByEmail,
}) {
  return (
    selectedInbox && (
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
              disabled={
                !canManageMembers ||
                (!isSuperAdmin && !subscriptionLoadFailed && teamMemberLimit > 0 && memberCount >= teamMemberLimit)
              }
              className="rounded-lg bg-slate-900 px-3 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              <UserPlus className="h-4 w-4" />
            </button>
          </div>
          {!canManageMembers && <p className="text-xs text-amber-700">Only owner/admin can add members.</p>}
          {canManageMembers &&
            !isSuperAdmin &&
            !subscriptionLoadFailed &&
            teamMemberLimit > 0 &&
            memberCount >= teamMemberLimit && (
              <p className="text-xs text-amber-700">Team seat limit reached ({teamMemberLimit}).</p>
            )}
          <div className="space-y-2 text-sm">
            {members.map((m) => (
              <div key={m.id} className="rounded-lg border border-slate-200 p-2">
                <div className="font-medium text-slate-900">{m.full_name || m.email}</div>
                <div className="text-xs text-slate-500">
                  {m.email} · {m.role}
                </div>
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
            <button
              onClick={addEmail}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-white"
            >
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
                        ? memberDisplayByEmail[memberEmailById[item.shared.assigned_to_user_id]] || 'assigned'
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
    )
  )
}
