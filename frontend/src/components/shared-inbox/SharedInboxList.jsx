import React from 'react'
import { Inbox, Plus } from 'lucide-react'

export default function SharedInboxList({
  createForm,
  setCreateForm,
  createInbox,
  isSuperAdmin,
  subscriptionLoadFailed,
  hasSharedInboxFeature,
  ownedInboxCount,
  sharedInboxLimit,
  loading,
  inboxes,
  setSelectedInbox,
  selectedInbox,
}) {
  return (
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
          disabled={
            (!isSuperAdmin && !subscriptionLoadFailed && !hasSharedInboxFeature) ||
            (!isSuperAdmin && !subscriptionLoadFailed && ownedInboxCount >= sharedInboxLimit)
          }
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
  )
}
