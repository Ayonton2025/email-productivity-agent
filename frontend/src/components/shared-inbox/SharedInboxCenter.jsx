import SharedInboxList from './SharedInboxList'
import SharedInboxDetails from './SharedInboxDetails'
import React from 'react'
import { CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react'

import { useSharedInbox } from './useSharedInbox'
const SharedInboxCenter = () => {
  const {
    isSuperAdmin,
    loading,
    inboxes,
    selectedInbox,
    setSelectedInbox,
    members,
    error,
    success,
    createForm,
    setCreateForm,
    memberEmail,
    setMemberEmail,
    emailIdToAdd,
    setEmailIdToAdd,
    subscriptionLoadFailed,
    assignedToMeOnly,
    setAssignedToMeOnly,
    loadInboxes,
    hasSharedInboxFeature,
    sharedInboxLimit,
    ownedInboxCount,
    canManageMembers,
    teamMemberLimit,
    memberCount,
    createInbox,
    addMember,
    addEmail,
    setStatus,
    setAssignment,
    memberEmailById,
    memberDisplayByEmail,
    filteredItems,
  } = useSharedInbox()
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

      <SharedInboxList
        createForm={createForm}
        setCreateForm={setCreateForm}
        createInbox={createInbox}
        isSuperAdmin={isSuperAdmin}
        subscriptionLoadFailed={subscriptionLoadFailed}
        hasSharedInboxFeature={hasSharedInboxFeature}
        ownedInboxCount={ownedInboxCount}
        sharedInboxLimit={sharedInboxLimit}
        loading={loading}
        inboxes={inboxes}
        setSelectedInbox={setSelectedInbox}
        selectedInbox={selectedInbox}
      />

      <SharedInboxDetails
        selectedInbox={selectedInbox}
        memberEmail={memberEmail}
        setMemberEmail={setMemberEmail}
        addMember={addMember}
        canManageMembers={canManageMembers}
        isSuperAdmin={isSuperAdmin}
        subscriptionLoadFailed={subscriptionLoadFailed}
        teamMemberLimit={teamMemberLimit}
        memberCount={memberCount}
        members={members}
        setAssignedToMeOnly={setAssignedToMeOnly}
        assignedToMeOnly={assignedToMeOnly}
        emailIdToAdd={emailIdToAdd}
        setEmailIdToAdd={setEmailIdToAdd}
        addEmail={addEmail}
        filteredItems={filteredItems}
        setStatus={setStatus}
        memberEmailById={memberEmailById}
        setAssignment={setAssignment}
        memberDisplayByEmail={memberDisplayByEmail}
      />
    </div>
  )
}
export default SharedInboxCenter
